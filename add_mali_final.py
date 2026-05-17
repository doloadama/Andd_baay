import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baay.settings')
django.setup()

from baay.models import Pays, Region, Localite
from django.core.exceptions import ValidationError
import uuid

# Create Mali
mali, _ = Pays.objects.get_or_create(nom='Mali', defaults={'code_iso': 'ML'})

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
for name, code in regions_data.items():
    regions[name], _ = Region.objects.get_or_create(pays=mali, nom=name, defaults={'code': code})

# Create localities using bulk operations
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

# Use get_or_create for each locality with error handling
count = 0
skipped = 0
for region_name, locality_names in localities_data.items():
    region = regions[region_name]
    for name in locality_names:
        try:
            obj, created = Localite.objects.get_or_create(pays=mali, region=region, nom=name)
            if created:
                count += 1
                print(f'  Created: {name} in {region_name}')
            else:
                skipped += 1
        except ValidationError:
            skipped += 1
            print(f'  Skipped (already exists): {name}')

print(f'Added {count} localities, skipped {skipped} localities')
