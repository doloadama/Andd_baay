import os
import django

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Andd_Baayi.settings')
django.setup()

from baay.models import ProduitAgricole

# Données des produits agricoles avec leurs photos
produits_photos = [
    {
        "id": "d07bf2020e9f440bb28a1ab5e8b70926",
        "photo": "mil.jpg"  # Nom du fichier image dans le dossier media/produits/
    },
    {
        "id": "ed540fadb7e2477699212d34e86744c8",
        "photo": "arachide.jpg"
    },
    {
        "id": "accf9498651c4bf4abd55bb33cc1dd5c",
        "photo": "riz.jpg"
    },
    {
        "id": "4f7d69d0080e49818782fae75a6029a8",
        "photo": "mais.jpg"
    },
    {
        "id": "b218707f40ad47158ed1f02319029c9a",
        "photo": "haricot_vert.jpg"
    },
    {
        "id": "72f6bd3b9d654f2eaaf1a561820766d6",
        "photo": "mangue.jpg"
    },
    {
        "id": "8fac243fd0484f3db192d023ca46a7b6",
        "photo": "pastèque.jpg"
    },
    {
        "id": "d4bd52983c454be4af2975663245d145",
        "photo": "oignon.jpg"
    },
    {
        "id": "e7718a23745a48f394ea46718b2eb54f",
        "photo": "tomate.jpg"
    },
    {
        "id": "215f91483fe24144b438f92680393f33",
        "photo": "niébé.jpg"
    },
]

# Mettre à jour les produits agricoles avec les photos
for produit_data in produits_photos:
    produit = ProduitAgricole.objects.get(id=produit_data["id"])
    produit.photo = f"produits/{produit['photo']}"  # Chemin relatif vers l'image
    produit.save()


print("10 produits agricoles ont été ajoutés à la base de données.")