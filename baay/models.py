# myapp/models.py
from datetime import datetime


from django.contrib.auth.models import PermissionsMixin, AbstractUser, User
from django.db import models
import uuid

from django.utils.timezone import now

class ProduitAgricole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    saison = models.CharField(max_length=50, null=True, blank=True)
    prix_par_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    apport_nutritionnel = models.TextField(null=True, blank=True)
    quantite_disponible = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    periode_recolte = models.CharField(max_length=100, null=True, blank=True)
    duree_avant_recolte = models.IntegerField(null=True, blank=True)
    rendement_moyen = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    photo = models.ImageField(upload_to='baay/media/produits/', null=True, blank=True)  # Champ pour la photo

    def __str__(self):
        return self.nom

class Localite(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    type_sol = models.CharField(max_length=50, null=True, blank=True)
    conditions_meteo = models.CharField(max_length=100, null=True, blank=True)
    details_meteo = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)  # Champ pour la latitude
    longitude = models.FloatField(null=True, blank=True)  # Champ pour la longitude

    def __str__(self):
        return self.nom

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


# Modèles de projet
class Projet(models.Model):
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('en_pause', 'En pause'),
        ('fini', 'Fini'),
    ]
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE)
    culture = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE, default= "b37e9b5f2b00463db21fe0a6f207a338")
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    statut = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Projet {self.id} - {self.culture.nom} by {self.utilisateur.user.username}"

class Investissement(models.Model):
    projet = models.ForeignKey('Projet', on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=False)
    cout_par_hectare = models.DecimalField(max_digits=10, decimal_places=2)
    date_investissement = models.DateField(default=now)

    def calculer_investissement_total(self):
        """
        Calculate the total investment cost for this investment.
        :return: Decimal
        """
        return self.cout_par_hectare * self.projet.superficie + (self.autres_frais or 0)

    def __str__(self):
        return f"Investissement {self.id_invest} pour le projet {self.projet.id}"


