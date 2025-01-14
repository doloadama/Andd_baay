# myapp/models.py
from datetime import datetime

from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import PermissionsMixin, AbstractUser, User
from django.db import models
import uuid

from django.utils.timezone import now

class FruitLegume(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True, default='')
    saison = models.CharField(max_length=50, null=True, blank=True, default="")  # Example: "Summer", "Winter"
    prix_par_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    apport_nutritionnel = models.TextField(null=True, blank=True, default="")  # Example: "Rich in Vitamin C"
    quantite_disponible = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default="")  # in kilograms


    def __str__(self):
        return self.nom

    def est_en_saison(self, saison_actuelle):
        """
        Check if the fruit/vegetable is in season.
        :param saison_actuelle: Current season as a string.
        :return: Boolean
        """
        return self.saison and saison_actuelle.lower() in self.saison.lower()

    def calculer_valeur_totale(self):
        """
        Calculate the total value of available stock based on price per kilogram.
        :return: Decimal
        """
        if self.prix_par_kg and self.quantite_disponible:
            return self.prix_par_kg * self.quantite_disponible
        return 0

class Culture(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    fruit_legume = models.ForeignKey(FruitLegume, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)
    periode_recolte = models.CharField(max_length=100, null=True, blank=True)
    duree_avant_recolte = models.IntegerField(null=True, blank=True)
    rendement_moyen = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.nom

class Localite(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    type_sol = models.CharField(max_length=50, null=True, blank=True)
    conditions_meteo = models.CharField(max_length=100, null=True, blank=True)
    details_meteo = models.TextField(null=True, blank=True)

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


class Investissement(models.Model):
    culture = models.ForeignKey(Culture, on_delete=models.CASCADE)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE)
    cout_par_hectare = models.DecimalField(max_digits=10, decimal_places=2)
    autres_frais = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class Projet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE)
    culture = models.ForeignKey(Culture, on_delete=models.CASCADE)
    investissement = models.ForeignKey(Investissement, on_delete=models.CASCADE)
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    investissement_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    benefices_estimes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def calculer_investissement_total(self):
        return self.investissement.cout_par_hectare * self.superficie + (self.investissement.autres_frais or 0)

    def __str__(self):
        return f"Projet {self.id} - {self.culture.nom} by {self.utilisateur.user.username}"


