# baay/tasks/__init__.py
"""
Tâches Celery — point d'entrée unique.

Toutes les tâches sont importées ici pour que le beat scheduler
puisse les résoudre via 'baay.tasks.<nom_tache>'.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# ─── P1.1 — Rafraîchissement du cache des correcteurs de biais ───────────────

@shared_task(
    name="baay.tasks.refresher_correcteurs_biais_task",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    ignore_result=True,
)
def refresher_correcteurs_biais_task(self):
    """
    Invalide le cache Redis des correcteurs de biais et les recalcule
    immédiatement à partir des projets clôturés.

    Planifié toutes les 6 heures via CELERY_BEAT_SCHEDULE.
    Neutre si < 5 observations par culture (facteur reste 1.0).
    """
    try:
        from baay.services.prediction_accuracy import (
            get_correcteurs_biais_par_culture,
            invalider_cache_correcteurs_biais,
        )

        invalider_cache_correcteurs_biais()
        correcteurs = get_correcteurs_biais_par_culture()
        logger.info(
            "refresher_correcteurs_biais : %d cultures calibrées → %s",
            len(correcteurs),
            list(correcteurs.keys()),
        )
        return {"cultures_calibrees": len(correcteurs)}
    except Exception as exc:
        logger.error("refresher_correcteurs_biais : erreur inattendue : %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ─── P2.1 — Recompute prédictions actives (phénologie) ───────────────────────

@shared_task(
    name="baay.tasks.recompute_active_predictions_task",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    ignore_result=True,
)
def recompute_active_predictions_task(self):
    """
    Recalcule toutes les PrevisionRecolte dont le projet est 'en_cours'
    et dont le ProjetProduit a une date_semis renseignée.

    Planifié chaque nuit à 02h00 via CELERY_BEAT_SCHEDULE.
    La progression phénologique (jours / cycle) réduit la variance
    et augmente la confiance au fil du temps — ce recalcul nocturne
    maintient les prévisions à jour automatiquement.
    """
    try:
        from baay.models import ProjetProduit
        from baay.core_services import update_prediction_for_projet_produit

        qs = (
            ProjetProduit.objects.filter(
                projet__statut="en_cours",
                date_semis__isnull=False,
            )
            .select_related(
                "produit",
                "projet",
                "projet__localite",
                "projet__localite__region",
            )
        )

        updated = 0
        errors = 0
        for pp in qs.iterator(chunk_size=100):
            try:
                update_prediction_for_projet_produit(pp)
                updated += 1
            except Exception as exc:
                errors += 1
                logger.warning(
                    "recompute_active_predictions : erreur pp=%s : %s", pp.pk, exc
                )

        logger.info(
            "recompute_active_predictions : %d prévisions mises à jour, %d erreurs.",
            updated, errors,
        )
        return {"updated": updated, "errors": errors}
    except Exception as exc:
        logger.error(
            "recompute_active_predictions : erreur globale : %s", exc, exc_info=True
        )
        raise self.retry(exc=exc)


# ─── P5.4 — Auto-réentraînement des modèles ML ────────────────────────────────

@shared_task(
    name="baay.tasks.auto_retrain_models_task",
    bind=True,
    max_retries=1,
    default_retry_delay=900,
    ignore_result=True,
)
def auto_retrain_models_task(
    self,
    *,
    declencheur: str = "auto",
    min_new_obs: int = 5,
    min_n: int = 5,
    warm_start: bool = True,
):
    """
    Détecte les cultures ayant accumulé ≥ min_new_obs nouvelles observations
    labellisées (rendement_reel renseigné) depuis leur dernier entraînement,
    et ré-entraîne un modèle XGBoost pour chacune.

    Planifié hebdomadairement (dimanche 03h00) via CELERY_BEAT_SCHEDULE.
    Peut aussi être déclenché immédiatement depuis le signal valider_label_ml_a_cloture
    quand une culture atteint le seuil MIN_NEW_OBS_AUTO.

    Le warm-start préserve la mémoire des données historiques : on ajoute des
    arbres sur le booster existant plutôt que de tout réapprendre.
    Un nouveau modèle ne remplace l'ancien que si son R² CV est au moins
    aussi bon (tolérance −0.05).
    """
    try:
        from baay.services.ml_training import cultures_a_reentrainer, entrainer_culture

        cultures = cultures_a_reentrainer(min_new_obs=min_new_obs)
        if not cultures:
            logger.info("auto_retrain_models : aucune culture à réentraîner.")
            return {"cultures": [], "results": []}

        logger.info(
            "auto_retrain_models [%s] : %d culture(s) à réentraîner → %s",
            declencheur, len(cultures), cultures,
        )

        results = []
        for culture_nom in cultures:
            try:
                result = entrainer_culture(
                    culture_nom,
                    min_n=min_n,
                    warm_start=warm_start,
                    declencheur=declencheur,
                )
                if result:
                    results.append({
                        "culture": culture_nom,
                        "n": result["n"],
                        "r2": round(result["r2"], 4),
                        "rmse": round(result["rmse"], 1),
                        "improved": result["improved"],
                        "warm_start_used": result["warm_start_used"],
                    })
                    logger.info(
                        "auto_retrain_models [%s] : R²=%.3f RMSE=%.0f improved=%s",
                        culture_nom, result["r2"], result["rmse"], result["improved"],
                    )
                else:
                    logger.info(
                        "auto_retrain_models [%s] : données insuffisantes (min_n=%d).",
                        culture_nom, min_n,
                    )
            except Exception as exc:
                logger.warning(
                    "auto_retrain_models : erreur pour '%s' : %s", culture_nom, exc
                )

        return {"cultures": cultures, "results": results}
    except Exception as exc:
        logger.error("auto_retrain_models : erreur globale : %s", exc, exc_info=True)
        raise self.retry(exc=exc)


# ─── Réexportation des tâches des sous-modules ───────────────────────────────
# Les tâches ci-dessous vivent dans leurs propres fichiers mais sont accessibles
# via baay.tasks.* pour le beat scheduler.

from baay.tasks.plant_vision import *   # noqa: F401, F403, E402
from baay.tasks.diagnostic import *     # noqa: F401, F403, E402
from baay.tasks.actualites import fetch_actualites_task  # noqa: F401, E402
from baay.tasks.prix import (           # noqa: F401, E402
    fetch_prix_marche_task,
    detecter_alertes_prix_task,
)
