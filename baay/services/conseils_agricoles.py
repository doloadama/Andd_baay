"""
Service de génération de conseils agronomiques contextualisés.

Génère des conseils actionnables basés sur :
- Le stade phénologique de la culture (age_plant / cycle)
- Les données de sol disponibles (N-P-K, pH)
- Les conditions hydriques (pluviométrie, irrigation)
- La fertilisation appliquée
- L'état végétatif observé (notation 1-5)
- La saison et le calendrier cultural

Retourne une liste de ConseilAgricole triée par priorité décroissante.
Aucun appel API externe — entièrement basé sur des règles agronomiques sahéliennes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

PRIORITE_CRITIQUE = "critique"
PRIORITE_HAUTE = "haute"
PRIORITE_NORMALE = "normale"
PRIORITE_INFO = "info"

CATEGORIE_SOL = "sol"
CATEGORIE_EAU = "eau"
CATEGORIE_PHYTO = "phytosanitaire"
CATEGORIE_FERTILISATION = "fertilisation"
CATEGORIE_CALENDRIER = "calendrier"
CATEGORIE_RENDEMENT = "rendement"
CATEGORIE_BIEN_ETRE = "bien_etre"


@dataclass
class ConseilAgricole:
    titre: str
    message: str
    priorite: str          # critique | haute | normale | info
    categorie: str         # sol | eau | phytosanitaire | fertilisation | calendrier | rendement
    action: str = ""       # libellé bouton ou action concrète
    icone: str = "fas fa-lightbulb"   # FontAwesome class
    couleur: str = "#1D9E75"          # hex couleur de la carte


# Mapping couleurs / icônes par priorité
_PRIORITE_STYLE = {
    PRIORITE_CRITIQUE: ("fas fa-exclamation-circle", "#DC2626"),
    PRIORITE_HAUTE:    ("fas fa-exclamation-triangle", "#F5A623"),
    PRIORITE_NORMALE:  ("fas fa-lightbulb", "#1D9E75"),
    PRIORITE_INFO:     ("fas fa-info-circle", "#1D4ED8"),
}

_PRIORITE_ORDRE = {
    PRIORITE_CRITIQUE: 0,
    PRIORITE_HAUTE: 1,
    PRIORITE_NORMALE: 2,
    PRIORITE_INFO: 3,
}


def _make_conseil(
    titre: str,
    message: str,
    priorite: str,
    categorie: str,
    action: str = "",
) -> ConseilAgricole:
    icone, couleur = _PRIORITE_STYLE.get(priorite, _PRIORITE_STYLE[PRIORITE_INFO])
    return ConseilAgricole(
        titre=titre,
        message=message,
        priorite=priorite,
        categorie=categorie,
        action=action,
        icone=icone,
        couleur=couleur,
    )


# ---------------------------------------------------------------------------
# Normes agronomiques sahéliennes (minima requis pour la culture)
# ---------------------------------------------------------------------------

_BESOINS_NPK_PPM = {
    # culture_key: (N_min, P_min, K_min)
    "arachide": (20, 15, 30),
    "mil":       (30, 20, 40),
    "sorgho":    (35, 20, 40),
    "mais":      (50, 25, 60),
    "riz":       (40, 20, 50),
    "niebe":     (15, 15, 30),
    "coton":     (60, 30, 60),
    "tomate":    (50, 30, 70),
    "oignon":    (60, 30, 80),
    "piment":    (50, 25, 60),
    "manioc":    (30, 20, 60),
    "igname":    (40, 25, 80),
}

_PH_OPTIMAL = {
    "arachide": (5.5, 7.0),
    "mil":       (5.0, 7.5),
    "sorgho":    (5.5, 8.0),
    "mais":      (5.5, 7.5),
    "riz":       (5.0, 6.5),
    "niebe":     (5.5, 7.0),
    "tomate":    (6.0, 6.8),
    "oignon":    (6.0, 7.0),
}


def _culture_key(nom: str) -> str:
    """Normalise le nom de culture pour la correspondance dans les tables."""
    return (
        nom.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("â", "a")
        .replace("ô", "o")
        .replace("-", " ")
        .strip()
    )


# ---------------------------------------------------------------------------
# Stades phénologiques
# ---------------------------------------------------------------------------

def _stade(progression: float) -> str:
    """
    Retourne le stade phénologique selon la progression du cycle (0→1).
    """
    if progression < 0.10:
        return "levee"
    elif progression < 0.25:
        return "vegetatif_precoce"
    elif progression < 0.50:
        return "vegetatif_actif"
    elif progression < 0.70:
        return "floraison"
    elif progression < 0.90:
        return "fructification"
    else:
        return "maturite"


_STADE_LABEL = {
    "levee":              "Levée / Germination",
    "vegetatif_precoce":  "Végétatif précoce",
    "vegetatif_actif":    "Croissance végétative",
    "floraison":          "Floraison",
    "fructification":     "Fructification / Remplissage",
    "maturite":           "Approche maturité",
}


# ---------------------------------------------------------------------------
# Moteur de conseils
# ---------------------------------------------------------------------------

def generer_conseils_par_stade(
    projet_produit,
    *,
    analyse_sol=None,          # HistoriqueSol optionnel (le plus récent de la ferme)
) -> list[ConseilAgricole]:
    """
    Génère une liste de conseils agronomiques contextualisés pour un ProjetProduit.

    Args:
        projet_produit: instance ProjetProduit (avec .produit, .projet, .projet.localite)
        analyse_sol: instance HistoriqueSol optionnel (pour les conseils N-P-K/pH)

    Returns:
        Liste de ConseilAgricole triée par priorité décroissante.
    """
    conseils: list[ConseilAgricole] = []
    pp = projet_produit
    produit = pp.produit
    projet = pp.projet
    localite = projet.localite

    nom_produit = produit.nom
    cle = _culture_key(nom_produit)

    # ── Progression du cycle ─────────────────────────────────────────────────
    cycle_jours = produit.cycle_culture_jours or produit.duree_avant_recolte or 0
    progression = 0.0
    jours_ecoules = 0
    date_recolte_prevue = None
    if pp.date_semis and cycle_jours > 0:
        jours_ecoules = (date.today() - pp.date_semis).days
        progression = min(1.0, max(0.0, jours_ecoules / cycle_jours))
        from datetime import timedelta
        date_recolte_prevue = pp.date_semis + timedelta(days=cycle_jours)

    stade = _stade(progression)
    stade_label = _STADE_LABEL.get(stade, "Stade inconnu")
    jours_restants = max(0, int(cycle_jours - jours_ecoules)) if cycle_jours else None

    # ── 1. Conseil de stade phénologique ────────────────────────────────────
    if stade == "levee":
        conseils.append(_make_conseil(
            titre="🌱 Surveiller la levée",
            message=(
                f"Votre {nom_produit} est en phase de levée/germination. "
                "Vérifiez régulièrement l'humidité du sol (pas de croûte de battance). "
                "Protégez les jeunes pousses contre les oiseaux granivores."
            ),
            priorite=PRIORITE_HAUTE,
            categorie=CATEGORIE_CALENDRIER,
            action="Consulter le calendrier cultural",
        ))

    elif stade == "vegetatif_precoce":
        conseils.append(_make_conseil(
            titre="🌿 Phase végétative — Attention aux mauvaises herbes",
            message=(
                f"Le {nom_produit} est en croissance précoce (J{jours_ecoules}). "
                "C'est la période critique de compétition avec les adventices. "
                "Effectuez un premier sarclage si nécessaire. "
                "Évitez les engrais azotés foliaires à ce stade."
            ),
            priorite=PRIORITE_HAUTE,
            categorie=CATEGORIE_CALENDRIER,
            action="Planifier le sarclage",
        ))

    elif stade == "vegetatif_actif":
        conseils.append(_make_conseil(
            titre="📈 Croissance active — Maximiser les apports",
            message=(
                f"Stade : {stade_label} (J{jours_ecoules}/{cycle_jours}j). "
                "C'est la phase d'accumulation de biomasse. Veillez à maintenir "
                "une alimentation hydrique et minérale régulière. "
                "Un apport d'azote fractionné (urée) peut significativement augmenter le rendement."
            ),
            priorite=PRIORITE_NORMALE,
            categorie=CATEGORIE_FERTILISATION,
            action="Planifier une fertilisation",
        ))

    elif stade == "floraison":
        conseils.append(_make_conseil(
            titre="🌸 Floraison — Stade le plus sensible",
            message=(
                f"Le {nom_produit} est en floraison (J{jours_ecoules}). "
                "ÉVITEZ tout stress hydrique à ce stade — une sécheresse pendant la floraison "
                "peut réduire le rendement de 30 à 50 %. "
                "Réduisez aussi les applications phytosanitaires pour protéger les pollinisateurs."
            ),
            priorite=PRIORITE_CRITIQUE,
            categorie=CATEGORIE_EAU,
            action="Vérifier l'irrigation",
        ))

    elif stade == "fructification":
        conseils.append(_make_conseil(
            titre="🌾 Remplissage du grain/fruit — Dernière ligne droite",
            message=(
                f"Phase de fructification (J{jours_ecoules}/{cycle_jours}j). "
                "Maintenez une irrigation modérée. Un apport de potassium (K) améliore "
                "la qualité et le calibre des fruits/grains. "
                "Surveillez attentivement les maladies fongiques (taches, rouilles)."
            ),
            priorite=PRIORITE_NORMALE,
            categorie=CATEGORIE_RENDEMENT,
        ))

    elif stade == "maturite":
        days_msg = f" dans {jours_restants} jour(s)" if jours_restants is not None and jours_restants > 0 else ""
        conseils.append(_make_conseil(
            titre=f"🏆 Récolte prévue{days_msg}",
            message=(
                f"Le {nom_produit} approche de sa maturité{days_msg}. "
                "Préparez le matériel de récolte et les moyens de stockage. "
                "Évitez toute application phytosanitaire dans les 2 semaines précédant la récolte. "
                "Récoltez aux heures fraîches pour limiter les pertes post-récolte."
            ),
            priorite=PRIORITE_HAUTE,
            categorie=CATEGORIE_CALENDRIER,
            action="Préparer la récolte",
        ))

    # ── 2. Alertes stade sans date de semis ─────────────────────────────────
    if not pp.date_semis:
        conseils.append(_make_conseil(
            titre="📅 Date de semis non renseignée",
            message=(
                "Renseignez la date de semis pour activer les conseils phénologiques "
                "personnalisés et les alertes calendrier. Sans cette date, les prédictions "
                "de rendement sont moins précises."
            ),
            priorite=PRIORITE_HAUTE,
            categorie=CATEGORIE_CALENDRIER,
            action="Modifier la culture",
        ))

    # ── 3. Conseil irrigation ────────────────────────────────────────────────
    besoin_eau = produit.besoin_eau_mm or 0
    pluie = (localite.pluviometrie_moyenne or 0) if localite else 0
    type_irrig = getattr(projet, "type_irrigation", "Aucune") or "Aucune"

    if besoin_eau > 0 and pluie < besoin_eau:
        if type_irrig == "Aucune":
            conseils.append(_make_conseil(
                titre="💧 Déficit hydrique — Irrigation fortement conseillée",
                message=(
                    f"{nom_produit} nécessite ~{besoin_eau} mm ; la zone reçoit ~{pluie} mm/an. "
                    "Le déficit hydrique actuel peut réduire le rendement de 40 à 60 %. "
                    "Envisagez une irrigation d'appoint, même sommaire (arrosage en rigoles)."
                ),
                priorite=PRIORITE_CRITIQUE,
                categorie=CATEGORIE_EAU,
                action="Planifier une irrigation",
            ))
        elif type_irrig == "Gravitaire":
            conseils.append(_make_conseil(
                titre="💧 Optimiser votre irrigation gravitaire",
                message=(
                    "L'irrigation gravitaire est en place, mais son efficacité est souvent "
                    "de 50-60 %. Vérifiez l'étanchéité des canaux et fractionnez les apports. "
                    "Un passage au goutte-à-goutte économiserait jusqu'à 40 % d'eau."
                ),
                priorite=PRIORITE_NORMALE,
                categorie=CATEGORIE_EAU,
            ))
        else:
            conseils.append(_make_conseil(
                titre="💧 Irrigation en place — Bon suivi",
                message=(
                    f"Votre système d'irrigation ({type_irrig}) compense le déficit hydrique. "
                    "Ajustez les apports selon le stade : plus fréquents à la floraison, "
                    "réduire 2 semaines avant récolte."
                ),
                priorite=PRIORITE_INFO,
                categorie=CATEGORIE_EAU,
            ))
    elif besoin_eau > 0 and pluie >= besoin_eau:
        if stade in ("floraison", "fructification") and type_irrig == "Aucune":
            conseils.append(_make_conseil(
                titre="💧 Pluviométrie suffisante — Surveiller les épisodes secs",
                message=(
                    "La pluviométrie annuelle couvre les besoins de la culture. "
                    f"Cependant, en phase de {stade_label.lower()}, un épisode sec de "
                    "plus de 10 jours peut être critique. Prévoyez une réserve d'eau."
                ),
                priorite=PRIORITE_NORMALE,
                categorie=CATEGORIE_EAU,
            ))

    # ── 4. Conseils fertilisation ────────────────────────────────────────────
    type_engrais = getattr(projet, "type_engrais", "Aucun") or "Aucun"

    if type_engrais == "Aucun":
        conseils.append(_make_conseil(
            titre="🌿 Aucune fertilisation — Rendement limité",
            message=(
                f"Sans apport nutritif, le {nom_produit} dépend entièrement des réserves du sol. "
                "Même un apport modeste de fumier composté (1-2 t/ha) ou de NPK de fond (50 kg/ha) "
                "peut augmenter le rendement de 20 à 40 % dans les sols sahéliens."
            ),
            priorite=PRIORITE_HAUTE,
            categorie=CATEGORIE_FERTILISATION,
            action="Planifier une fertilisation",
        ))
    elif type_engrais == "Organique":
        if stade in ("vegetatif_actif", "floraison"):
            conseils.append(_make_conseil(
                titre="🌱 Complément azoté recommandé à ce stade",
                message=(
                    "L'engrais organique libère ses nutriments lentement. "
                    f"En phase de {stade_label.lower()}, un appoint d'urée (25-50 kg/ha) "
                    "en couverture accélèrera la croissance végétative et améliorera le rendement."
                ),
                priorite=PRIORITE_NORMALE,
                categorie=CATEGORIE_FERTILISATION,
            ))
    elif type_engrais in ("Minéral", "NPK"):
        if stade == "vegetatif_precoce":
            conseils.append(_make_conseil(
                titre="✅ Fertilisation minérale en place",
                message=(
                    "Bon choix. Assurez-vous que le premier apport de fond (NPK) a été "
                    "localisé à 5-10 cm du plant. Prévoyez un apport d'urée en couverture "
                    "au stade de tallage/floraison pour maximiser les grains."
                ),
                priorite=PRIORITE_INFO,
                categorie=CATEGORIE_FERTILISATION,
            ))

    # ── 5. Conseil sol (si données disponibles) ──────────────────────────────
    if analyse_sol:
        n_val = float(analyse_sol.azote_ppm or 0)
        p_val = float(analyse_sol.phosphore_ppm or 0)
        k_val = float(analyse_sol.potassium_ppm or 0)
        ph_val = float(analyse_sol.ph) if analyse_sol.ph else None

        besoins = _BESOINS_NPK_PPM.get(cle, (30, 20, 40))
        n_min, p_min, k_min = besoins

        carences = []
        if n_val < n_min:
            carences.append(f"Azote (N) : {n_val} ppm < seuil {n_min} ppm")
        if p_val < p_min:
            carences.append(f"Phosphore (P) : {p_val} ppm < seuil {p_min} ppm")
        if k_val < k_min:
            carences.append(f"Potassium (K) : {k_val} ppm < seuil {k_min} ppm")

        if carences:
            conseils.append(_make_conseil(
                titre="⚗️ Carences nutritives détectées dans le sol",
                message=(
                    f"Analyse sol du {analyse_sol.date_mesure} — carences pour {nom_produit} :\n"
                    + "\n".join(f"• {c}" for c in carences)
                    + "\nAction : apportez l'engrais adapté dès que possible."
                ),
                priorite=PRIORITE_HAUTE,
                categorie=CATEGORIE_SOL,
                action="Voir les recommandations sol",
            ))
        else:
            conseils.append(_make_conseil(
                titre="✅ Sol bien équilibré pour cette culture",
                message=(
                    f"Les niveaux N-P-K de votre sol correspondent aux besoins du {nom_produit}. "
                    "Continuez les bonnes pratiques et réévaluez en fin de campagne."
                ),
                priorite=PRIORITE_INFO,
                categorie=CATEGORIE_SOL,
            ))

        # pH
        if ph_val is not None:
            ph_range = _PH_OPTIMAL.get(cle, (5.5, 7.5))
            if ph_val < ph_range[0]:
                conseils.append(_make_conseil(
                    titre=f"⚠️ Sol acide (pH {ph_val:.1f}) — risque de toxicité aluminique",
                    message=(
                        f"Le pH optimal pour {nom_produit} est {ph_range[0]}-{ph_range[1]}. "
                        f"À pH {ph_val:.1f}, l'aluminium peut devenir toxique. "
                        "Appliquez 300-500 kg/ha de chaux agricole et réincorporez avant le prochain cycle."
                    ),
                    priorite=PRIORITE_HAUTE,
                    categorie=CATEGORIE_SOL,
                    action="Corriger le pH",
                ))
            elif ph_val > ph_range[1]:
                conseils.append(_make_conseil(
                    titre=f"⚠️ Sol alcalin (pH {ph_val:.1f}) — absorption réduite",
                    message=(
                        f"Un pH de {ph_val:.1f} réduit la disponibilité du fer et du zinc. "
                        "Incorporez de la matière organique (compost, fumier) pour tamponner l'alcalinité."
                    ),
                    priorite=PRIORITE_NORMALE,
                    categorie=CATEGORIE_SOL,
                ))

    # ── 6. Conseil état végétatif ────────────────────────────────────────────
    etat = getattr(pp, "etat_vegetatif", None)
    if etat is not None:
        if etat <= 2:
            conseils.append(_make_conseil(
                titre=f"🚨 État végétatif préoccupant ({etat}/5) — Diagnostic urgent",
                message=(
                    "Vous avez noté un état végétatif défavorable. "
                    "Causas possibles : stress hydrique, carence nutritive, attaque de ravageurs "
                    "ou maladie fongique. Prenez une photo et lancez le diagnostic photo IA "
                    "(BaayVision) pour identifier le problème rapidement."
                ),
                priorite=PRIORITE_CRITIQUE,
                categorie=CATEGORIE_PHYTO,
                action="Lancer le diagnostic photo",
            ))
        elif etat == 3:
            conseils.append(_make_conseil(
                titre="👀 État végétatif moyen — Surveiller de près",
                message=(
                    "L'état actuel est normal mais sans excès. Consultez les niveaux d'eau "
                    "et de fertilisation. Un léger apport nutritif peut améliorer la situation."
                ),
                priorite=PRIORITE_NORMALE,
                categorie=CATEGORIE_PHYTO,
            ))
        elif etat >= 4:
            conseils.append(_make_conseil(
                titre="🌟 Excellente vigueur végétative — Maintenir le cap",
                message=(
                    "Votre culture affiche une belle santé. Maintenez les pratiques actuelles "
                    "et restez vigilant à l'approche de la floraison. "
                    "Pensez à mettre à jour la prévision de rendement."
                ),
                priorite=PRIORITE_INFO,
                categorie=CATEGORIE_BIEN_ETRE,
            ))

    # ── 7. Conseil saison ────────────────────────────────────────────────────
    if pp.date_semis and produit.saison == "Hivernage":
        mois_semis = pp.date_semis.month
        if mois_semis >= 8:
            conseils.append(_make_conseil(
                titre="⏰ Semis tardif détecté — Risque de récolte sous pluie",
                message=(
                    f"Pour une culture d'hivernage, un semis en août ou plus tard "
                    "peut conduire à une récolte sous les premières pluies de fin de saison, "
                    "augmentant les risques de moisissures post-récolte. "
                    "Planifiez une récolte précoce si possible."
                ),
                priorite=PRIORITE_HAUTE,
                categorie=CATEGORIE_CALENDRIER,
            ))

    # ── 8. Conseil maladies génériques par stade ─────────────────────────────
    if stade in ("floraison", "fructification"):
        conseils.append(_make_conseil(
            titre="🔬 Surveillance phytosanitaire renforcée recommandée",
            message=(
                f"La {stade_label.lower()} est la phase la plus exposée aux maladies fongiques "
                "(rouille, mildiou, oïdium) et aux ravageurs (chenilles légionnaires, pucerons). "
                "Inspectez les feuilles supérieures 2 fois par semaine. "
                "En cas de symptômes, utilisez le diagnostic photo IA pour une identification rapide."
            ),
            priorite=PRIORITE_NORMALE,
            categorie=CATEGORIE_PHYTO,
            action="Lancer le diagnostic photo",
        ))

    # ── Conseil si pas de photo ───────────────────────────────────────────────
    if not getattr(pp, "image", None) and stade not in ("levee",):
        conseils.append(_make_conseil(
            titre="📸 Ajoutez une photo pour le diagnostic IA",
            message=(
                "Le diagnostic photo BaayVision nécessite une image de la culture. "
                "Prenez une photo rapprochée d'une feuille ou d'un symptôme suspect "
                "et ajoutez-la à cette culture pour activer l'analyse IA."
            ),
            priorite=PRIORITE_INFO,
            categorie=CATEGORIE_PHYTO,
            action="Modifier la culture",
        ))

    # ── Tri final par priorité ────────────────────────────────────────────────
    conseils.sort(key=lambda c: _PRIORITE_ORDRE.get(c.priorite, 99))
    return conseils
