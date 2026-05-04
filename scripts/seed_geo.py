#!/usr/bin/env python
"""
Seed géographique Andd Baay : pays membres de l'Union africaine (noms français)
et régions administratives pour le Sénégal, le Mali, le Maroc et la Mauritanie.

Usage (depuis la racine du projet) :
    python scripts/seed_geo.py

À lancer après : python manage.py migrate
"""

import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Andd_Baayi.settings")
django.setup()

from django.db import transaction  # noqa: E402

from baay.models import Pays, Region  # noqa: E402

# États membres de l’UA (liste usuelle ; noms en français + code ISO alpha-2)
AFRICAN_MEMBER_STATES = [
    ("Algérie", "DZ"),
    ("Angola", "AO"),
    ("Bénin", "BJ"),
    ("Botswana", "BW"),
    ("Burkina Faso", "BF"),
    ("Burundi", "BI"),
    ("Cabo Verde", "CV"),
    ("Cameroun", "CM"),
    ("République centrafricaine", "CF"),
    ("Tchad", "TD"),
    ("Comores", "KM"),
    ("Congo-Brazzaville", "CG"),
    ("RDC", "CD"),
    ("Côte d'Ivoire", "CI"),
    ("Djibouti", "DJ"),
    ("Égypte", "EG"),
    ("Guinée équatoriale", "GQ"),
    ("Érythrée", "ER"),
    ("Eswatini", "SZ"),
    ("Éthiopie", "ET"),
    ("Gabon", "GA"),
    ("Gambie", "GM"),
    ("Ghana", "GH"),
    ("Guinée", "GN"),
    ("Guinée-Bissau", "GW"),
    ("Kenya", "KE"),
    ("Lesotho", "LS"),
    ("Libéria", "LR"),
    ("Libye", "LY"),
    ("Madagascar", "MG"),
    ("Malawi", "MW"),
    ("Mali", "ML"),
    ("Mauritanie", "MR"),
    ("Maurice", "MU"),
    ("Maroc", "MA"),
    ("Mozambique", "MZ"),
    ("Namibie", "NA"),
    ("Niger", "NE"),
    ("Nigéria", "NG"),
    ("Rwanda", "RW"),
    ("Saharawi (RASD)", ""),  # pas d’ISO unique universellement reconnu
    ("Sao Tomé-et-Príncipe", "ST"),
    ("Sénégal", "SN"),
    ("Seychelles", "SC"),
    ("Sierra Leone", "SL"),
    ("Somalie", "SO"),
    ("Afrique du Sud", "ZA"),
    ("Soudan du Sud", "SS"),
    ("Soudan", "SD"),
    ("Tanzanie", "TZ"),
    ("Togo", "TG"),
    ("Tunisie", "TN"),
    ("Ouganda", "UG"),
    ("Zambie", "ZM"),
    ("Zimbabwe", "ZW"),
]

REGIONS_BY_COUNTRY = {
    "Sénégal": [
        "Dakar",
        "Diourbel",
        "Fatick",
        "Kaffrine",
        "Kaolack",
        "Kédougou",
        "Kolda",
        "Louga",
        "Matam",
        "Saint-Louis",
        "Sédhiou",
        "Tambacounda",
        "Thiès",
        "Ziguinchor",
    ],
    "Mali": [
        "Kayes",
        "Koulikoro",
        "Sikasso",
        "Ségou",
        "Mopti",
        "Tombouctou",
        "Gao",
        "Ménaka",
        "Taoudénit",
        "Kidal",
        "District de Bamako",
    ],
    "Maroc": [
        "Tanger-Tétouan-Al Hoceïma",
        "L'Oriental",
        "Fès-Meknès",
        "Rabat-Salé-Kénitra",
        "Béni Mellal-Khénifra",
        "Casablanca-Settat",
        "Marrakech-Safi",
        "Drâa-Tafilalet",
        "Souss-Massa",
        "Guelmim-Oued Noun",
        "Laâyoune-Sakia El Hamra",
        "Dakhla-Oued Ed-Dahab",
    ],
    "Mauritanie": [
        "Hodh ech Chargui",
        "Hodh El Gharbi",
        "Assaba",
        "Gorgol",
        "Brakna",
        "Trarza",
        "Adrar",
        "Nouakchott Nord",
        "Nouakchott Ouest",
        "Nouakchott Sud",
        "Dakhlet Nouadhibou",
        "Tagant",
        "Guidimagha",
        "Tiris Zemmour",
        "Inchiri",
    ],
}


@transaction.atomic
def seed_countries_and_regions():
    created_p = updated_p = created_r = 0
    for nom, iso in AFRICAN_MEMBER_STATES:
        p, crt = Pays.objects.get_or_create(
            nom=nom,
            defaults={"code_iso": iso or None},
        )
        if crt:
            created_p += 1
        elif iso and p.code_iso != iso:
            p.code_iso = iso
            p.save(update_fields=["code_iso"])
            updated_p += 1

    for country_name, regs in REGIONS_BY_COUNTRY.items():
        pays = Pays.objects.filter(nom=country_name).first()
        if not pays:
            pays, _ = Pays.objects.get_or_create(nom=country_name, defaults={"code_iso": None})
        for rn in regs:
            _, crt = Region.objects.get_or_create(pays=pays, nom=rn)
            if crt:
                created_r += 1
    print(
        f"Pays créés={created_p}, pays MAJ iso={updated_p}, "
        f"régions créées ({', '.join(REGIONS_BY_COUNTRY)})={created_r}"
    )


def main():
    seed_countries_and_regions()


if __name__ == "__main__":
    main()
