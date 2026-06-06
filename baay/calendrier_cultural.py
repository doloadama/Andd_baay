"""
Calendrier cultural du Sénégal — données agronomiques curées (contenu SEO).
============================================================================
Dataset **autoritaire et statique** (pas de dépendance DB) servant les pages
publiques indexables `/calendrier-cultural/` et `/calendrier-cultural/<slug>/`.

Pourquoi statique : la table `ProduitAgricole` a des champs agronomiques NULL
pour les cultures principales (mil, arachide…). Pour un contenu SEO complet et
fiable, on cure les faits ici. Amorcé depuis les constantes de
`baay/management/commands/seed_projets_fictifs.py` (`_REND_MOYEN`) + fenêtres de
semis et conseils agronomiques (sources FAO/ISRA, pratiques Sénégal).

`semis_mois` : numéros de mois (1=janvier … 12=décembre) de la fenêtre de semis.
`besoin_eau_mm` : besoin en eau total sur le cycle.
`rendement_min/max` : kg/ha observés au Sénégal.
"""
from __future__ import annotations

MOIS_COURTS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
MOIS_NOMS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

CULTURES: list[dict] = [
    {
        "slug": "mil",
        "nom": "Mil",
        "famille": "Céréale",
        "saison": "Hivernage",
        "semis_mois": [6, 7],
        "cycle_jours": 90,
        "besoin_eau_mm": 350,
        "periode_recolte": "Septembre à octobre",
        "rendement_min": 700,
        "rendement_max": 1400,
        "sols_adaptes": ["Dior", "Deck-Dior"],
        "conseils": [
            "Semer dès les premières pluies utiles (15–20 mm) pour profiter de toute la saison.",
            "Démarier à 2 plants par poquet 10–15 jours après la levée.",
            "Un apport d'engrais organique (fumier) sur sol Dior améliore nettement le rendement.",
            "Surveiller les attaques de mineuse de l'épi et les oiseaux granivores en fin de cycle.",
        ],
        "meta_description": "Calendrier cultural du mil au Sénégal : quand semer, cycle (90 j), besoin en eau, période de récolte, rendement et conseils agronomiques.",
        "intro": "Le mil est la céréale pluviale de base du Sahel sénégalais, cultivée en hivernage sur sols Dior. Voici le calendrier et les bonnes pratiques pour réussir votre campagne.",
    },
    {
        "slug": "arachide",
        "nom": "Arachide",
        "famille": "Légumineuse",
        "saison": "Hivernage",
        "semis_mois": [6, 7],
        "cycle_jours": 110,
        "besoin_eau_mm": 400,
        "periode_recolte": "Octobre à novembre",
        "rendement_min": 800,
        "rendement_max": 1600,
        "sols_adaptes": ["Dior", "Deck-Dior"],
        "conseils": [
            "Utiliser des semences certifiées et traitées pour limiter les fontes de semis.",
            "Semer sur sol bien ressuyé après une pluie d'installation ; éviter les sols lourds (Deck).",
            "L'inoculation (rhizobium) et un léger apport phosphaté favorisent la nodulation.",
            "Récolter dès que les gousses sont mûres pour limiter les pertes et l'aflatoxine.",
        ],
        "meta_description": "Quand semer l'arachide au Sénégal ? Calendrier cultural : semis, cycle (110 j), besoin en eau, récolte, rendement et conseils.",
        "intro": "L'arachide, culture de rente majeure du bassin arachidier, se sème en début d'hivernage sur sols sableux (Dior). Calendrier et conseils pour une bonne campagne.",
    },
    {
        "slug": "niebe",
        "nom": "Niébé",
        "famille": "Légumineuse",
        "saison": "Hivernage",
        "semis_mois": [7, 8],
        "cycle_jours": 80,
        "besoin_eau_mm": 300,
        "periode_recolte": "Septembre à octobre",
        "rendement_min": 400,
        "rendement_max": 900,
        "sols_adaptes": ["Dior", "Sablonneux"],
        "conseils": [
            "Culture courte et résistante à la sécheresse, idéale en association avec le mil.",
            "Semer après le mil pour étaler le travail et couvrir le sol.",
            "Surveiller pucerons et thrips ; les bruches attaquent les graines au stockage.",
            "Le niébé enrichit le sol en azote : excellent précédent cultural.",
        ],
        "meta_description": "Calendrier cultural du niébé au Sénégal : semis, cycle court (80 j), besoin en eau, récolte, rendement et conseils agronomiques.",
        "intro": "Le niébé (cornille) est une légumineuse rustique, souvent associée au mil. Sa culture courte sécurise la production en zone sahélienne.",
    },
    {
        "slug": "sorgho",
        "nom": "Sorgho",
        "famille": "Céréale",
        "saison": "Hivernage",
        "semis_mois": [6, 7],
        "cycle_jours": 110,
        "besoin_eau_mm": 450,
        "periode_recolte": "Octobre à novembre",
        "rendement_min": 900,
        "rendement_max": 1800,
        "sols_adaptes": ["Deck", "Deck-Dior"],
        "conseils": [
            "Préférer les sols lourds (Deck) qui retiennent l'eau, contrairement au mil.",
            "Semer en début d'hivernage ; démarier pour ajuster la densité.",
            "Lutter contre le foreur de tige et la cécidomyie ; protéger les panicules des oiseaux.",
            "Un apport azoté fractionné soutient la montaison.",
        ],
        "meta_description": "Calendrier cultural du sorgho au Sénégal : semis, cycle (110 j), besoin en eau, récolte, rendement et conseils.",
        "intro": "Le sorgho valorise les sols lourds (Deck) du Sine-Saloum et de la Casamance. Plus tolérant à l'engorgement que le mil.",
    },
    {
        "slug": "riz",
        "nom": "Riz",
        "famille": "Céréale",
        "saison": "Hivernage",
        "semis_mois": [6, 7],
        "cycle_jours": 120,
        "besoin_eau_mm": 900,
        "periode_recolte": "Octobre à décembre",
        "rendement_min": 2500,
        "rendement_max": 5500,
        "sols_adaptes": ["Deck", "Deck-Dior"],
        "conseils": [
            "Riziculture irriguée (vallée du fleuve) ou de bas-fond (Casamance) : maîtriser la lame d'eau.",
            "Repiquer de jeunes plants (15–20 j) en ligne pour faciliter l'entretien.",
            "Fractionner l'azote (tallage, montaison) pour maximiser le rendement.",
            "Désherber tôt : la concurrence des adventices est le premier facteur de perte.",
        ],
        "meta_description": "Calendrier cultural du riz au Sénégal : semis/repiquage, cycle (120 j), besoin en eau, récolte, rendement et conseils.",
        "intro": "Le riz, irrigué dans la vallée du fleuve ou de bas-fond en Casamance, est très exigeant en eau mais offre les meilleurs rendements céréaliers.",
    },
    {
        "slug": "mais",
        "nom": "Maïs",
        "famille": "Céréale",
        "saison": "Hivernage",
        "semis_mois": [6, 7],
        "cycle_jours": 100,
        "besoin_eau_mm": 550,
        "periode_recolte": "Septembre à octobre",
        "rendement_min": 1500,
        "rendement_max": 3500,
        "sols_adaptes": ["Deck", "Deck-Dior"],
        "conseils": [
            "Exigeant en eau et en azote : réserver les bonnes terres et fertiliser.",
            "Semer dès l'installation des pluies ; densité régulière pour un bon peuplement.",
            "Surveiller la chenille légionnaire d'automne, ravageur majeur du maïs.",
            "L'irrigation d'appoint sécurise fortement le rendement en cas de poche de sécheresse.",
        ],
        "meta_description": "Calendrier cultural du maïs au Sénégal : semis, cycle (100 j), besoin en eau, récolte, rendement et conseils agronomiques.",
        "intro": "Le maïs, performant sur bonnes terres bien alimentées en eau, demande une fertilisation azotée soutenue pour exprimer son potentiel.",
    },
    {
        "slug": "tomate",
        "nom": "Tomate",
        "famille": "Maraîchage",
        "saison": "Contre-saison",
        "semis_mois": [10, 11, 12],
        "cycle_jours": 90,
        "besoin_eau_mm": 600,
        "periode_recolte": "Février à avril",
        "rendement_min": 12000,
        "rendement_max": 25000,
        "sols_adaptes": ["Deck", "Deck-Dior"],
        "conseils": [
            "Cultiver en contre-saison fraîche (oct.–avr.) pour limiter la pression parasitaire.",
            "Passer par une pépinière puis repiquer des plants vigoureux.",
            "Irrigation régulière (goutte-à-goutte idéal) : éviter les à-coups qui fendillent les fruits.",
            "Surveiller la mineuse (Tuta absoluta) et les maladies fongiques ; paillage recommandé.",
        ],
        "meta_description": "Calendrier cultural de la tomate au Sénégal : semis en contre-saison, cycle (90 j), besoin en eau, récolte, rendement et conseils.",
        "intro": "La tomate est une culture maraîchère de contre-saison à forte valeur ajoutée, conduite en irrigation. Calendrier et conseils pour limiter les pertes.",
    },
    {
        "slug": "oignon",
        "nom": "Oignon",
        "famille": "Maraîchage",
        "saison": "Contre-saison",
        "semis_mois": [10, 11, 12],
        "cycle_jours": 100,
        "besoin_eau_mm": 500,
        "periode_recolte": "Mars à mai",
        "rendement_min": 15000,
        "rendement_max": 28000,
        "sols_adaptes": ["Sablonneux", "Deck"],
        "conseils": [
            "Filière phare des Niayes : semis en pépinière puis repiquage.",
            "Arrêter l'irrigation à l'approche de la maturité (chute des feuilles) pour la conservation.",
            "Bien sécher et trier les bulbes après récolte pour limiter les pertes au stockage.",
            "Surveiller les thrips et le mildiou ; éviter l'excès d'azote en fin de cycle.",
        ],
        "meta_description": "Calendrier cultural de l'oignon au Sénégal : semis en contre-saison, cycle (100 j), besoin en eau, récolte, rendement et conseils.",
        "intro": "L'oignon, pilier maraîcher des Niayes, se conduit en contre-saison. Une bonne gestion de l'eau et du séchage conditionne la conservation des bulbes.",
    },
]

# Articles français corrects par culture (évite « du Arachide ») :
#   det    = article défini + nom  (« le mil », « l'arachide », « la tomate »)
#   det_de = « de » contracté + nom (« du mil », « de l'arachide », « de la tomate »)
_ARTICLES = {
    "mil":      ("le mil", "du mil"),
    "arachide": ("l'arachide", "de l'arachide"),
    "niebe":    ("le niébé", "du niébé"),
    "sorgho":   ("le sorgho", "du sorgho"),
    "riz":      ("le riz", "du riz"),
    "mais":     ("le maïs", "du maïs"),
    "tomate":   ("la tomate", "de la tomate"),
    "oignon":   ("l'oignon", "de l'oignon"),
}
for _c in CULTURES:
    _det, _det_de = _ARTICLES.get(_c["slug"], (_c["nom"].lower(), "de " + _c["nom"].lower()))
    _c["det"] = _det
    _c["det_de"] = _det_de

# Index slug -> culture (construit une fois).
_INDEX = {c["slug"]: c for c in CULTURES}


def liste_cultures() -> list[dict]:
    """Toutes les cultures du calendrier (ordre du dataset)."""
    return CULTURES


def get_culture(slug: str) -> dict | None:
    """Retourne la culture pour un slug, ou None si inconnu."""
    return _INDEX.get(slug)


def mois_semis_labels(culture: dict) -> str:
    """Libellé lisible de la fenêtre de semis (ex. 'juin à juillet')."""
    mois = culture.get("semis_mois") or []
    if not mois:
        return ""
    if len(mois) == 1:
        return MOIS_NOMS[mois[0] - 1]
    return f"{MOIS_NOMS[mois[0] - 1]} à {MOIS_NOMS[mois[-1] - 1]}"
