from django.core.management.base import BaseCommand
from baay.models import Pays, Region, Localite
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = 'Add all localities of Mali to the database'

    def handle(self, *args, **options):
        # Create Mali
        mali, created = Pays.objects.get_or_create(nom='Mali', defaults={'code_iso': 'ML'})
        self.stdout.write(f'Mali: {"created" if created else "already exists"}')

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
            region, created = Region.objects.get_or_create(pays=mali, nom=name, defaults={'code': code})
            regions[name] = region
            self.stdout.write(f'Region {name}: {"created" if created else "already exists"}')

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

        count = 0
        skipped = 0
        for region_name, locality_names in localities_data.items():
            region = regions[region_name]
            for name in locality_names:
                try:
                    obj, created = Localite.objects.get_or_create(pays=mali, region=region, nom=name)
                    if created:
                        count += 1
                        self.stdout.write(f'  Created: {name} in {region_name}')
                    else:
                        skipped += 1
                except ValidationError:
                    skipped += 1
                    self.stdout.write(f'  Skipped (already exists): {name}')

        self.stdout.write(f'\nAdded {count} localities, skipped {skipped} localities')
