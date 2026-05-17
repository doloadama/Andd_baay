import os
import sys
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')
django_setup = __import__('django')
django_setup.setup()

from baay.models import Pays, Region, Localite

# Create Mali
mali, created = Pays.objects.get_or_create(
    nom='Mali',
    defaults={'code_iso': 'ML'}
)
print(f'Mali: {mali.nom} (created: {created})')

# Create regions
regions_data = {
    'Kayes': 'KAY',
    'Koulikoro': 'KOU',
    'Sikasso': 'SIK',
    'Ségou': 'SEG',
    'Mopti': 'MOP',
    'Tombouctou': 'TOM',
    'Gao': 'GAO',
    'Kidal': 'KID',
    'Bamako': 'BAM',
}

regions = {}
for region_name, code in regions_data.items():
    region, created = Region.objects.get_or_create(
        pays=mali,
        nom=region_name,
        defaults={'code': code}
    )
    regions[region_name] = region
    print(f'Region {region_name}: created={created}')

# Create localities
localities_data = {
    'Kayes': ['Kayes', 'Kita', 'Nioro du Sahel', 'Diéma', 'Yélimané', 'Bafoulabé', 'Kéniéba', 'Sadiola', 'Guémoukouraba', 'Diondougou', 'Fatao', 'Goumbou', 'Kolondiéba', 'Mahina', 'Niantaga', 'Sébégou', 'Siby', 'Toukoto'],
    'Koulikoro': ['Koulikoro', 'Kati', 'Kolokani', 'Banamba', 'Dioïla', 'Kangaba', 'Nara', 'Bougouni', 'Fana', 'Kalabancoro', 'Kignan', 'Mandé', 'Ouezzindougou', 'Sanankoroba', 'Sirakoro', 'Tienfala', 'Toula'],
    'Sikasso': ['Sikasso', 'Koutiala', 'Bougouni', 'Yorosso', 'Kolondiéba', 'Yanfolila', 'Kadiolo', 'Kignan', 'Zantiébougou', 'Farako', 'Garalo', 'Kolokoba', 'Ladji', 'Mafélé', 'Nangola', 'Niéna', 'Ouéléssébougou', 'Pimperna', 'Sindou', 'Tengrédougou', 'Wolon', 'Zanfina'],
    'Ségou': ['Ségou', 'Markala', 'Niono', 'Baraouéli', 'Macina', 'Blan', 'Dioma', 'Dougouolo', 'Fangué', 'Katiné', 'Kéména', 'Konodimini', 'Massina', 'Nampala', 'Ngarana', 'Pélengana', 'Sokolo', 'Toguna'],
    'Mopti': ['Mopti', 'Sévaré', 'Djenne', 'Bandiagara', 'Bankass', 'Koro', 'Douentza', 'Youwarou', 'Ténenkou', 'Mopti-Ville', 'Konna', 'Sokolo', 'Boré', 'Déguékoré', 'Dialloubé', 'Falgani', 'Fatoma', 'Gounari', 'Hombori', 'Kani-Bonzon', 'Koubéwel', 'Koundel', 'Modiagoué', 'Ouatagouna', 'Sokara'],
    'Tombouctou': ['Tombouctou', 'Goundam', 'Diré', 'Gourma-Rharous', 'Niafunké', 'Bamba', 'Araouane', 'Béré-Erag', 'Bourem', 'Dangha', 'Essakane', 'Karbane', 'Koriomé', 'Lafiabougou', 'M\'Bouna', 'Rharous', 'Salit', 'Sareyamou', 'Soboundou', 'Tinderé'],
    'Gao': ['Gao', 'Ansongo', 'Bourem', 'Ménaka', 'Tombouctou', 'Al Moustarat', 'Bintagoungou', 'Boulkessy', 'Djébock', 'Gao-Cinq', 'Gogorou', 'Hamzakalah', 'Inékar', 'Korienze', 'Labézanga', 'Mé-Sakiné', 'Norou', 'Petit Borkou', 'Tassiga', 'Tilia', 'Tindaradjine'],
    'Kidal': ['Kidal', 'Abeïbara', 'Anefif', 'Essouk', 'Tessalit', 'Aguelhok', 'Adjelhoc', 'Bogassa', 'Kidal-Ville', 'M\'Bouna', 'Tin-Essako', 'Tigharghar'],
    'Bamako': ['Commune I', 'Commune II', 'Commune III', 'Commune IV', 'Commune V', 'Commune VI', 'Kalabancoro', 'Kabala', 'Niamakoro', 'Sabalibougou', 'Daoudabougou', 'Faladié', 'Korofina', 'Magnambougou', 'Missira', 'Niaréla', 'Sotuba', 'Torokorobougou', 'Baco-Djicoroni', 'Bagadadji', 'Badialan', 'Balan-Sogoniko', 'Boulkassombougou', 'Djélibougou', 'Doumanzana', 'Fadjiguila', 'Hamdallaye', 'Hippodrome', 'Kalanban-Soto', 'Kouloublina', 'Lafiabougou', 'Médina-Coura', 'Mokolo', 'N\'Gorosabougou', 'Niarela', 'Quinzambougou', 'Sagaladougou', 'Sénou', 'Siby', 'Sokorodji', 'Sotuba', 'Tikorobougou', 'Torokorobougou', 'Yasso', 'Yirimadio'],
}

total_created = 0
for region_name, locality_names in localities_data.items():
    region = regions[region_name]
    for locality_name in locality_names:
        locality, created = Localite.objects.get_or_create(
            pays=mali,
            region=region,
            nom=locality_name
        )
        if created:
            total_created += 1
            print(f'  Created: {locality_name} in {region_name}')

print(f'\nTotal localities created: {total_created}')
