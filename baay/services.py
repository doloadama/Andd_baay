import logging
import os
import base64
import hashlib
from datetime import timedelta
from types import SimpleNamespace

import requests
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db import transaction
from django.db.models.functions import Coalesce
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import (
    DemandeAccesFerme,
    Depense,
    Ferme,
    HistoriqueSol,
    Investissement,
    MembreFerme,
    PrevisionRecolte,
    ProduitAgricole,
    Profile,
    Projet,
    ProjetProduit,
    Recette,
)
from .messaging_contract import build_recruitment_status_event_v1

logger = logging.getLogger(__name__)


def _format_fcfa_montant(amount: Decimal) -> str:
    if amount is None:
        return "0"
    try:
        n = int(amount.quantize(Decimal("1")))
    except Exception:
        n = int(amount)
    return f"{n:,}".replace(",", "\u202f")


def investissement_montant_expr():
    """Expression ORM : coût/ha × ha (culture ou projet) + autres frais."""
    return ExpressionWrapper(
        F("cout_par_hectare")
        * Coalesce(
            F("projet_produit__superficie_allouee"),
            F("projet__superficie"),
        )
        + Coalesce(F("autres_frais"), Value(Decimal("0"))),
        output_field=DecimalField(max_digits=24, decimal_places=2),
    )


def total_investissements_projet(projet_id):
    agg = (
        Investissement.objects.filter(projet_id=projet_id)
        .aggregate(t=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0"))))
    )
    return agg["t"] or Decimal("0")


def total_recettes_projet(projet_id):
    agg = Recette.objects.filter(projet_id=projet_id).aggregate(
        t=Coalesce(Sum("montant_total"), Value(Decimal("0")))
    )
    return agg["t"] or Decimal("0")


def _safe_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantite_recoltee_projet(projet_id) -> Decimal:
    agg = ProjetProduit.objects.filter(projet_id=projet_id).aggregate(
        q=Coalesce(Sum("rendement_final"), Value(Decimal("0")))
    )
    return agg["q"] or Decimal("0")


def _prediction_revenue_proxy(projet_id) -> Decimal:
    total = Decimal("0")
    rows = (
        PrevisionRecolte.objects.filter(projet_id=projet_id)
        .select_related("projet_produit__produit")
    )
    for prev in rows:
        predicted_qty = (
            _safe_decimal(prev.rendement_estime_min)
            + _safe_decimal(prev.rendement_estime_max)
        ) / Decimal("2")
        produit = prev.projet_produit.produit if prev.projet_produit_id else None
        prix = produit.prix_par_kg if produit and produit.prix_par_kg is not None else Decimal("0")
        total += predicted_qty * prix
    return total


def calculer_kpis_financiers_projet(projet_id) -> dict:
    """
    KPIs financiers réels d'un projet (dashboard, API mobile, clôture).

    Formules (FCFA) :
    - Somme des lignes ``Investissement`` : total_lignes_investissement (= tout matériel + hors matériel).
    - Total ``Depense`` (fiches projet) ajouté au dénominateur de coût total.
    - Total coûts = total_lignes_investissement + total_depenses_fiche_simple.
    - total_depenses : charges d'exploitation = lignes inv hors « matériel » + fiches ``Depense``.
    - Investissements matériels : catégorie « matériel » sur les lignes inv.
    - Bénéfice net = Total recettes − Total coûts ; ROI % = Bénéfice net / Total coûts × 100.
    """
    inv_expr = investissement_montant_expr()
    inv_aggr = Investissement.objects.filter(projet_id=projet_id).aggregate(
        total_lignes_investissement=Coalesce(Sum(inv_expr), Value(Decimal("0"))),
        total_investissements=Coalesce(
            Sum(inv_expr, filter=Q(categorie="materiel")),
            Value(Decimal("0")),
        ),
        total_depenses_lignes_investissement=Coalesce(
            Sum(inv_expr, filter=~Q(categorie="materiel")),
            Value(Decimal("0")),
        ),
    )
    dep_aggr = Depense.objects.filter(projet_id=projet_id).aggregate(
        sf=Coalesce(Sum("montant"), Value(Decimal("0")))
    )
    total_depenses_fiche = dep_aggr["sf"] or Decimal("0")
    total_recettes = total_recettes_projet(projet_id)
    total_lignes_inv = inv_aggr["total_lignes_investissement"] or Decimal("0")
    total_depenses_inv = inv_aggr["total_depenses_lignes_investissement"] or Decimal("0")
    total_investissements = inv_aggr["total_investissements"] or Decimal("0")
    total_depenses_combinees = total_depenses_inv + total_depenses_fiche
    total_couts = total_lignes_inv + total_depenses_fiche
    benefice_net = total_recettes - total_couts
    roi = (benefice_net / total_couts * Decimal("100")) if total_couts else None
    quantite_recoltee = _quantite_recoltee_projet(projet_id)
    cout_revient_unite = (
        (total_depenses_combinees / quantite_recoltee) if quantite_recoltee else None
    )
    recettes_prevues = _prediction_revenue_proxy(projet_id)
    ecart_previsionnel = total_recettes - recettes_prevues
    ecart_previsionnel_pct = (
        ecart_previsionnel / recettes_prevues * Decimal("100")
        if recettes_prevues
        else None
    )

    return {
        "projet_id": str(projet_id),
        "total_recettes": total_recettes,
        "total_depenses": total_depenses_combinees,
        "total_depenses_lignes_investissement": total_depenses_inv,
        "total_depenses_fiche_simple": total_depenses_fiche,
        "total_lignes_investissement_fcfa": total_lignes_inv,
        "total_investissements": total_investissements,
        "total_couts": total_couts,
        "benefice_net": benefice_net,
        "roi_pct": roi,
        "quantite_recoltee": quantite_recoltee,
        "cout_revient_unite": cout_revient_unite,
        "recettes_prevues": recettes_prevues,
        "ecart_previsionnel": ecart_previsionnel,
        "ecart_previsionnel_pct": ecart_previsionnel_pct,
    }


def cloturer_projet(projet_id) -> dict:
    """
    Clôture comptable : statut « clôturé », verrouillage des lignes ``Investissement`` et
    des fiches ``Depense`` associées au projet.

    Prérequis : projet « fini ». Idempotent : re-verrouille les lignes restées ouvertes
    et renvoie les KPI.
    """
    from django.utils import timezone as _tz

    with transaction.atomic():
        projet = Projet.objects.select_for_update().get(pk=projet_id)
        becoming = projet.statut != Projet.STATUT_CLOTURE
        if becoming:
            if projet.statut != "fini":
                raise ValidationError(
                    "Clôture comptable impossible : le projet doit d'abord être au statut « Fini » "
                    "(travaux et récolte terminés). Les écritures comptables restent ouvertes tant "
                    "qu'il n'est pas « Clôturé »."
                )
            projet.statut = Projet.STATUT_CLOTURE
        date_fin_ajoutee = False
        if not projet.date_fin:
            projet.date_fin = _tz.localdate()
            date_fin_ajoutee = True
        to_update = []
        if becoming:
            to_update.append("statut")
        if date_fin_ajoutee:
            to_update.append("date_fin")
        if to_update:
            projet.save(update_fields=to_update)
        Investissement.objects.filter(projet=projet, verrouille=False).update(
            verrouille=True,
            date_verrouillage=_tz.now(),
        )
        Depense.objects.filter(projet=projet, verrouille=False).update(
            verrouille=True,
            date_verrouillage=_tz.now(),
        )
        kpis = calculer_kpis_financiers_projet(projet.id)
    return {"projet": projet, "kpis": kpis, "etait_deja_cloture": not becoming}


def check_budget_status(projet_id):
    """
    Compare la somme des investissements (montant par ligne : ha culture ou projet)
    au budget_alloue du projet (FCFA).
    """
    projet = (
        Projet.objects.filter(pk=projet_id)
        .only("id", "nom", "budget_alloue", "superficie")
        .first()
    )
    if not projet:
        return {"ok": False, "error": "projet_introuvable"}

    budget = projet.budget_alloue
    if budget is None:
        return {
            "ok": True,
            "applicable": False,
            "over_budget": False,
            "projet_nom": projet.nom,
            "total_investi": None,
            "budget": None,
            "depassement": None,
        }

    total = total_investissements_projet(projet_id)

    budget_val = budget or Decimal("0")
    over = total > budget_val
    depassement = (total - budget_val) if over else Decimal("0")

    return {
        "ok": True,
        "applicable": True,
        "over_budget": over,
        "total_investi": total,
        "budget": budget_val,
        "depassement": depassement,
        "depassement_display": _format_fcfa_montant(depassement),
        "projet_nom": projet.nom,
    }


def check_projet_produit_budget_status(projet_produit_id):
    """Budget optionnel par culture (ProjetProduit.budget_alloue)."""
    pp = (
        ProjetProduit.objects.filter(pk=projet_produit_id)
        .select_related("projet", "produit")
        .only("id", "budget_alloue", "projet__nom", "produit__nom")
        .first()
    )
    if not pp:
        return {"ok": False, "applicable": False}
    if pp.budget_alloue is None:
        return {
            "ok": True,
            "applicable": False,
            "over_budget": False,
            "produit_nom": pp.produit.nom if pp.produit_id else "",
            "projet_nom": pp.projet.nom,
        }

    total = (
        Investissement.objects.filter(projet_produit_id=projet_produit_id).aggregate(
            t=Coalesce(Sum(investissement_montant_expr()), Value(Decimal("0")))
        )["t"]
        or Decimal("0")
    )
    budget_val = pp.budget_alloue or Decimal("0")
    over = total > budget_val
    depassement = (total - budget_val) if over else Decimal("0")
    label = f"{pp.produit.nom} — {pp.projet.nom}"
    return {
        "ok": True,
        "applicable": True,
        "over_budget": over,
        "total_investi": total,
        "budget": budget_val,
        "depassement": depassement,
        "depassement_display": _format_fcfa_montant(depassement),
        "projet_line_label": label,
    }

def estimer_rendement_ia(projet_produit):
    """
    Estime dynamiquement le rendement d'une culture selon des critères agronomiques.
    Prend en compte le type de sol, l'eau, et les dates de semis.
    """
    produit = projet_produit.produit
    projet = projet_produit.projet
    localite = projet.localite

    # Base : Le potentiel max de la culture, ou le rendement moyen, ou un fallback
    rendement_base = produit.rendement_potentiel_max or produit.rendement_moyen or 1000.0
    
    # Superficie
    superficie = float(projet_produit.superficie_allouee or 1.0)
    rendement_total_base = float(rendement_base) * superficie

    penalite = 0.0
    confiance = 80.0 # Confiance de base sans modèle entraîné

    # 1. Vérification du Sol
    sol_inadapte = False
    if localite.type_sol:
        # Exemples de règles simples : L'arachide aime le Dior, le Riz aime le Deck.
        if 'arachide' in produit.nom.lower() and localite.type_sol not in ['Dior', 'Deck-Dior']:
            sol_inadapte = True
        elif 'riz' in produit.nom.lower() and localite.type_sol not in ['Deck', 'Deck-Dior']:
            sol_inadapte = True

    if sol_inadapte:
        penalite += 0.20
        confiance -= 10.0

    # 2. Vérification de l'Eau (Pluviométrie + Irrigation)
    besoin_eau = produit.besoin_eau_mm or 0
    pluie_moyenne = localite.pluviometrie_moyenne or 0
    
    if besoin_eau > 0 and pluie_moyenne < besoin_eau:
        if projet.type_irrigation == 'Aucune':
            penalite += 0.40 # Énorme pénalité de stress hydrique
            confiance -= 20.0
        else:
            # S'il y a de l'irrigation, on compense
            if projet.type_irrigation == 'Goutte-à-goutte':
                confiance += 10.0 # Très efficace
            else:
                confiance += 5.0

    # 3. Évaluation du semis tardif
    if projet_produit.date_semis:
        # En Afrique de l'Ouest, l'hivernage est généralement Juillet-Août.
        # Règle simple: si semis après mi-Août pour une culture d'hivernage
        mois_semis = projet_produit.date_semis.month
        if produit.saison == 'Hivernage' and mois_semis >= 8:
            # Semis tardif
            penalite += 0.15
            confiance -= 10.0

    # 4. Apports (Engrais)
    bonus = 0.0
    if projet.type_engrais != 'Aucun':
        # Bonus variable selon le type d'engrais
        if projet.type_engrais == 'Mixte':
            bonus += 0.15
            confiance += 8.0
        elif 'Minéral' in projet.type_engrais:
            bonus += 0.12
            confiance += 5.0
        elif projet.type_engrais == 'Organique':
            bonus += 0.08
            confiance += 6.0 # L'organique est plus sain sur le long terme

    # Calcul Final
    modificateur = max(0.1, 1.0 - penalite + bonus)
    rendement_cible = rendement_total_base * modificateur
    
    # Fourchette Min/Max (Variance de 10%)
    rendement_min = rendement_cible * 0.90
    rendement_max = rendement_cible * 1.10

    # Calcul Date de récolte prévue
    date_recolte = None
    cycle = produit.cycle_culture_jours or produit.duree_avant_recolte
    if projet_produit.date_semis and cycle:
        date_recolte = projet_produit.date_semis + timedelta(days=cycle)

    return {
        'min': round(rendement_min, 2),
        'max': round(rendement_max, 2),
        'confiance': min(100.0, max(0.0, confiance)),
        'date_recolte_prevue': date_recolte
    }


def get_prevision_affichee_projet(projet):
    """
    Vue agrégée des prévisions d'un projet (une ligne par ProjetProduit possible).
    Retourne un seul PrevisionRecolte si une seule entrée, sinon un SimpleNamespace
    avec les mêmes attributs pour les gabarits.
    """
    if projet is None or not projet.pk:
        return None
    rows = list(projet.previsions.order_by("-date_prediction"))
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    total_min = sum(r.rendement_estime_min for r in rows)
    total_max = sum(r.rendement_estime_max for r in rows)
    confs = [r.indice_confiance for r in rows if r.indice_confiance is not None]
    avg_c = sum(confs) / len(confs) if confs else None
    dates = [r.date_recolte_prevue for r in rows if r.date_recolte_prevue]
    d_prev = max(dates) if dates else None
    return SimpleNamespace(
        rendement_estime_min=total_min,
        rendement_estime_max=total_max,
        indice_confiance=avg_c,
        date_recolte_prevue=d_prev,
    )


def ensure_profile_for_user(user: User) -> Profile:
    """Return a profile for a user, creating it if missing."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def update_prediction_for_projet_produit(projet_produit):
    """
    Met à jour ou crée la PrevisionRecolte liée à ce semis (ProjetProduit).
    Une entrée par ligne produit ; le projet est dénormalisé pour requêtes agrégées.
    """
    resultats = estimer_rendement_ia(projet_produit)
    prediction, _ = PrevisionRecolte.objects.update_or_create(
        projet_produit=projet_produit,
        defaults={
            "projet": projet_produit.projet,
            "rendement_estime_min": resultats["min"],
            "rendement_estime_max": resultats["max"],
            "indice_confiance": resultats["confiance"],
            "date_recolte_prevue": resultats["date_recolte_prevue"],
        },
    )
    return prediction


def compute_previsions_for_projet(projet_id: str) -> dict:
    """Service: compute PrevisionRecolte for each ProjetProduit of a projet and
    update the denormalized Projet.rendement_estime field. Returns summary dict.
    """
    with transaction.atomic():
        projet = Projet.objects.select_related("ferme").get(pk=projet_id)
        pps = list(
            ProjetProduit.objects.filter(projet=projet).select_related(
                "produit", "projet", "projet__localite"
            )
        )
        for pp in pps:
            update_prediction_for_projet_produit(pp)

        prevs = list(PrevisionRecolte.objects.filter(projet=projet))
        total_min = sum(p.rendement_estime_min for p in prevs) if prevs else 0
        total_max = sum(p.rendement_estime_max for p in prevs) if prevs else 0
        projet.rendement_estime = (total_min + total_max) / 2 if prevs else None
        projet.save(update_fields=["rendement_estime"])  

    return {
        "projet": projet,
        "total_min": total_min,
        "total_max": total_max,
        "count_pp": len(pps),
    }


# =====================
# Météo (OpenWeatherMap)
# =====================
def get_weather_data(ferme_id: str) -> dict:
    """Retourne la meteo temps reel d'une ferme via OpenWeatherMap."""
    ferme = (
        Ferme.objects
        .only("id", "latitude", "longitude")
        .filter(pk=ferme_id)
        .first()
    )
    if not ferme:
        return {"ok": False, "error": "ferme_introuvable"}

    lat = ferme.latitude
    lon = ferme.longitude
    if lat is None or lon is None:
        return {"ok": False, "error": "coords_absentes"}

    api_key = getattr(settings, "OPENWEATHER_API_KEY", None) or os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "api_key_absente"}

    cache_key = f"weather:ferme:{ferme_id}:{round(float(lat),3)}:{round(float(lon),3)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"ok": True, "data": cached}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "fr",
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return {"ok": False, "error": f"http_{resp.status_code}"}
        raw = resp.json() or {}
        weather = (raw.get("weather") or [{}])[0]
        w = {
            "temperature": (raw.get("main") or {}).get("temp"),
            "humidite": (raw.get("main") or {}).get("humidity"),
            "description": weather.get("description"),
            "icone": weather.get("icon"),
        }
        try:
            ttl_min = int(getattr(settings, "WEATHER_CACHE_TTL_MINUTES", 30))
        except Exception:
            ttl_min = 30
        cache.set(cache_key, w, timeout=max(60, ttl_min * 60))
        return {"ok": True, "data": w}
    except Exception as e:
        logger.error("Erreur appel OpenWeather", exc_info=True)
        return {"ok": False, "error": "exception"}


# =====================
# Recrutement / Demandes
# =====================
def transition_demande_acces(demande_id: str, nouveau_statut: str, role: str = "ouvrier", peut_gerer_membres: bool = False) -> dict:
    """Transition d'etat pour DemandeAccesFerme.

    Si approuvee, cree MembreFerme et notifie l'utilisateur.
    """
    if nouveau_statut not in {"en_attente", "approuvee", "refusee"}:
        raise ValidationError({"statut": "Statut invalide."})
    if role not in {"manager", "technicien", "ouvrier"}:
        role = "ouvrier"

    with transaction.atomic():
        demande = (
            DemandeAccesFerme.objects.select_for_update()
            .select_related("ferme", "utilisateur__user")
            .filter(pk=demande_id)
            .first()
        )
        if not demande:
            return {"ok": False, "error": "demande_introuvable"}

        created_membership = False
        if demande.statut == nouveau_statut:
            return {"ok": True, "demande": demande, "created_membership": False}

        if nouveau_statut == "approuvee":
            membre, created_membership = MembreFerme.objects.get_or_create(
                ferme=demande.ferme,
                utilisateur=demande.utilisateur,
                defaults={"role": role, "peut_gerer_membres": bool(peut_gerer_membres)},
            )
            if not created_membership:
                membre.role = role
                membre.peut_gerer_membres = bool(peut_gerer_membres)
                membre.save(update_fields=["role", "peut_gerer_membres"])

        demande.statut = nouveau_statut
        from django.utils import timezone as _tz
        demande.date_traitement = _tz.now()
        demande.save(update_fields=["statut", "date_traitement"])

    _notify_demande_acces_user(demande, nouveau_statut)
    return {"ok": True, "demande": demande, "created_membership": bool(created_membership)}


def create_demande_acces_ferme(ferme: Ferme, utilisateur: Profile) -> DemandeAccesFerme:
    """Cree une demande apres validation anti-doublon et anti-membre."""
    demande = DemandeAccesFerme(
        ferme=ferme,
        utilisateur=utilisateur,
        code=ferme.code_acces,
    )
    demande.full_clean()
    demande.save()
    return demande


def _notify_demande_acces_user(demande: DemandeAccesFerme, statut: str) -> None:
    """Notification best-effort : websocket si disponible, email sinon/en plus."""
    try:
        layer = get_channel_layer()
        payload = build_recruitment_status_event_v1(demande, statut)
        async_to_sync(layer.group_send)(f"inbox_{demande.utilisateur.id}", payload)
    except Exception:
        logger.warning("Notification recrutement Channels ignoree", exc_info=True)

    email = demande.utilisateur.user.email
    if not email:
        return
    if statut == "approuvee":
        subject = f"Votre demande d'acces a {demande.ferme.nom} a ete approuvee"
        message = (
            f"Bonjour {demande.utilisateur.user.username},\n\n"
            f"Votre demande d'acces a la ferme {demande.ferme.nom} a ete approuvee.\n"
            "Vous pouvez desormais y acceder depuis Andd Baay."
        )
    elif statut == "refusee":
        subject = f"Votre demande d'acces a {demande.ferme.nom} a ete refusee"
        message = (
            f"Bonjour {demande.utilisateur.user.username},\n\n"
            f"Votre demande d'acces a la ferme {demande.ferme.nom} n'a pas ete acceptee."
        )
    else:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@anddbaay.local"),
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        logger.warning("Email recrutement non envoye a %s", email, exc_info=True)


# =====================
# Médias Cloudinary — livraison optimisée (mobile / faible bande passante)
# =====================


class CloudinaryPreset:
    """Noms usuels pour `cloudinary_sahara_url` / gabarits HTML."""

    THUMB = "thumb"
    LIST = "list"
    DASHBOARD = "dashboard"
    DETAIL = "detail"
    REPORT = "report"


_SAHARA_IMAGE_PRESETS = {
    CloudinaryPreset.THUMB: {
        "width": 280,
        "height": 280,
        "crop": "fill",
        "gravity": "auto",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.LIST: {
        "width": 480,
        "height": 480,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.DASHBOARD: {
        "width": 768,
        "height": 432,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.DETAIL: {
        "width": 1280,
        "height": 1280,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
    CloudinaryPreset.REPORT: {
        "width": 2000,
        "height": 2000,
        "crop": "limit",
        "fetch_format": "auto",
        "quality": "auto",
    },
}


def cloudinary_direct_url(media_value) -> str:
    """URL de livraison par défaut (sans transformation catalogue)."""
    if not media_value:
        return ""
    try:
        u = getattr(media_value, "url", None)
        if u:
            return u
    except Exception:
        pass
    raw = getattr(media_value, "name", None) or str(media_value)
    return raw.strip() if raw else ""


def cloudinary_sahara_url(
    media_value,
    preset: str = CloudinaryPreset.LIST,
    *,
    dpr_auto: bool = True,
) -> str:
    """
    URL avec f_auto et q_auto (via options Cloudinary).
    Pour les fichiers ``resource_type=raw`` (PDF…) : fallback sur l’URL directe sans transformation image.
    """
    if not media_value:
        return ""

    try:
        from baay.cloudinary_helpers import public_id_and_type as _pid_rt
        from django.conf import settings as dj_settings

        from cloudinary import utils as cu
    except Exception:
        return cloudinary_direct_url(media_value)

    if not getattr(dj_settings, "CLOUDINARY_ACTIVE", False):
        return cloudinary_direct_url(media_value)

    pid, rt = _pid_rt(media_value)
    if not pid:
        return cloudinary_direct_url(media_value)

    if rt != "image":
        return cloudinary_direct_url(media_value)

    transforms = dict(_SAHARA_IMAGE_PRESETS.get(preset, _SAHARA_IMAGE_PRESETS[CloudinaryPreset.LIST]))
    if dpr_auto:
        transforms.setdefault("dpr", "auto")
    kw = dict(transforms)
    kw["secure"] = True
    try:
        url, _unused = cu.cloudinary_url(pid, **kw)
        return url or cloudinary_direct_url(media_value)
    except Exception:
        return cloudinary_direct_url(media_value)


def cloudinary_img_lazy_attrs(media_value, preset: str = CloudinaryPreset.LIST, *, alt: str = ""):
    """
    Attributs HTML conseillés pour chargement différé (dashboard mobile).
    Exemple gabarit : ``<img {...|cloudinary_img_lazy_attrs:pp.image,'thumb',alt='Plant'} />``
    (avec un filtre custom ou en Python : ``attr=cloudinary_img_lazy_attrs(...)`` puis spread).
    """
    src = cloudinary_sahara_url(media_value, preset=preset)
    attrs = {"src": src, "loading": "lazy", "decoding": "async", "alt": alt}
    widths = []
    sizes = getattr(settings, "CLOUDINARY_SRCSET_WIDTHS", (320, 480, 640, 960))
    try:
        from baay.cloudinary_helpers import public_id_and_type as _pid_rt
        from django.conf import settings as dj_settings
        from cloudinary import utils as cu

        if getattr(dj_settings, "CLOUDINARY_ACTIVE", False):
            pid, rt = _pid_rt(media_value)
            if pid and rt == "image":
                for w in sizes:
                    u, _x = cu.cloudinary_url(
                        pid,
                        secure=True,
                        width=w,
                        crop="limit",
                        fetch_format="auto",
                        quality="auto",
                    )
                    if u:
                        widths.append((u, w))
    except Exception:
        widths = []
    if widths:
        attrs["srcset"] = ", ".join(f"{u} {w}w" for u, w in widths)
        attrs["sizes"] = "(max-width: 576px) 100vw, (max-width: 992px) 50vw, 33vw"
    return attrs


def product_placeholder_data_uri(product_name: str) -> str:
    """
    Lightweight per-product image (SVG data URI).
    Deterministic colors based on product name, optimized for low bandwidth.
    """
    name = (product_name or "Produit").strip()
    initials = "".join([p[0] for p in name.split()[:2] if p])[:2].upper() or "P"
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()
    c1 = f"#{h[0:6]}"
    c2 = f"#{h[6:12]}"
    text = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" role="img" aria-label="{text}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <filter id="s" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.25"/>
    </filter>
  </defs>
  <rect width="960" height="540" rx="36" fill="url(#g)"/>
  <g filter="url(#s)">
    <rect x="56" y="56" width="848" height="428" rx="28" fill="rgba(255,255,255,0.14)" stroke="rgba(255,255,255,0.22)"/>
  </g>
  <text x="96" y="170" font-family="system-ui, -apple-system, Segoe UI, Roboto, Arial" font-weight="800" font-size="64" fill="rgba(255,255,255,0.95)">{initials}</text>
  <text x="96" y="250" font-family="system-ui, -apple-system, Segoe UI, Roboto, Arial" font-weight="700" font-size="38" fill="rgba(255,255,255,0.9)">{text}</text>
  <text x="96" y="310" font-family="system-ui, -apple-system, Segoe UI, Roboto, Arial" font-weight="600" font-size="22" fill="rgba(255,255,255,0.75)">Suivi des plants</text>
</svg>"""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


# ─── Soil Ledger ─────────────────────────────────────────────────────────────

_PH_TOLERANT_ACIDS = {"Manioc", "Arachide", "Patate douce", "Ananas"}  # pH < 6
_PH_ALKALINE_SENSITIVE = {"Riz", "Blé", "Orge"}  # pH > 7.5 → déconseillé
_LEGUMES = {"Arachide", "Niébé", "Soja", "Haricot"}  # fixateurs azote
_HIGH_K_DEMAND = {"Banane", "Tomate", "Pomme de terre", "Patate douce"}  # K exigeants

_SEUIL_K_BAS = Decimal("80")   # ppm — en dessous : déconseiller cultures K-exigeantes
_SEUIL_N_BAS = Decimal("20")   # ppm — en dessous : favoriser légumineuses


def suggerer_semis_saison_suivante(ferme_id) -> dict:
    """
    Analyse le dernier enregistrement ``HistoriqueSol`` de la ferme et retourne
    une suggestion de culture pour la saison suivante.

    Retourne ::

        {
            "suggestion": ProduitAgricole | None,
            "raison": str,
            "confiance": int,   # 0-100
            "alertes": list[str],
        }
    """
    derniere = (
        HistoriqueSol.objects.filter(ferme_id=ferme_id)
        .select_related("culture_precedente")
        .order_by("-date_mesure")
        .first()
    )

    if derniere is None:
        return {
            "suggestion": None,
            "raison": "Aucune analyse de sol enregistrée pour cette ferme.",
            "confiance": 0,
            "alertes": [],
        }

    alertes: list[str] = []
    exclusions: set[str] = set()
    preferences: list[str] = []
    raisons: list[str] = []
    confiance = 40  # base

    ph = derniere.ph
    azote = derniere.azote_ppm
    potassium = derniere.potassium_ppm
    culture_prec = derniere.culture_precedente

    # ── pH ──────────────────────────────────────────────────────────────────
    if ph is not None:
        confiance += 15
        if ph < Decimal("5.5"):
            alertes.append(f"pH acide ({ph}) — amendement calcique recommandé.")
            preferences.extend(_PH_TOLERANT_ACIDS)
            raisons.append("pH acide : cultures tolérantes choisies")
        elif ph > Decimal("7.5"):
            alertes.append(f"pH alcalin ({ph}) — apport de soufre possible.")
            exclusions.update(_PH_ALKALINE_SENSITIVE)
            raisons.append("pH alcalin : céréales sensibles exclues")
        else:
            raisons.append(f"pH optimal ({ph})")

    # ── Azote ────────────────────────────────────────────────────────────────
    if azote is not None:
        confiance += 10
        if azote < _SEUIL_N_BAS:
            alertes.append(f"Azote bas ({azote} ppm) — légumineuse recommandée.")
            preferences.extend(_LEGUMES)
            raisons.append("Azote faible : légumineuse fixatrice favorisée")

    # ── Potassium ────────────────────────────────────────────────────────────
    if potassium is not None:
        confiance += 10
        if potassium < _SEUIL_K_BAS:
            alertes.append(f"Potassium bas ({potassium} ppm) — éviter cultures K-exigeantes.")
            exclusions.update(_HIGH_K_DEMAND)
            raisons.append("Potassium faible : cultures exigeantes exclues")

    # ── Rotation culturale ───────────────────────────────────────────────────
    if culture_prec is not None:
        confiance += 10
        prec_nom = culture_prec.nom
        if prec_nom in _LEGUMES:
            raisons.append(f"Rotation après légumineuse ({prec_nom}) : céréale conseillée")
            preferences.append("Mil")
            preferences.append("Sorgho")
            preferences.append("Maïs")
        else:
            exclusions.add(prec_nom)
            raisons.append(f"Rotation : {prec_nom} exclu pour éviter l'épuisement")

    # ── Sélection du candidat ────────────────────────────────────────────────
    suggestion: ProduitAgricole | None = None

    if preferences:
        # Recherche stricte par ordre de préférence
        for nom_pref in preferences:
            candidat = (
                ProduitAgricole.objects.filter(nom__iexact=nom_pref)
                .exclude(nom__in=exclusions)
                .first()
            )
            if candidat:
                suggestion = candidat
                break

    if suggestion is None:
        # Fallback : n'importe quelle culture hors exclusions
        suggestion = (
            ProduitAgricole.objects.exclude(nom__in=exclusions).order_by("nom").first()
        )

    confiance = min(confiance, 95)

    return {
        "suggestion": suggestion,
        "raison": " ; ".join(raisons) if raisons else "Analyse standard.",
        "confiance": confiance,
        "alertes": alertes,
    }
