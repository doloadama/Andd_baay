
# myapp/models.py

from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.db import models
import uuid

from django.utils.timezone import now


class Culture(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    periode_recolte = models.CharField(max_length=100, null=True, blank=True)
    duree_avant_recolte = models.IntegerField(null=True, blank=True)
    rendement_moyen = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.nom

class Localite(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    type_sol = models.CharField(max_length=50, null=True, blank=True)
    conditions_meteo = models.CharField(max_length=100, null=True, blank=True)
    details_meteo = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nom

class Utilisateur(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prenom = models.CharField(max_length=100,default=" alexandra")
    nom = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True, default="unknown@example.com")
    date_creation = models.DateTimeField(default=now)
    mot_de_passe = models.TextField()


    def __str__(self):
        return self.nom

    def set_password(self, new_password):
        self.mot_de_passe = make_password(new_password)
        self.save()


class Investissement(models.Model):
    culture = models.ForeignKey(Culture, on_delete=models.CASCADE)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE)
    cout_par_hectare = models.DecimalField(max_digits=10, decimal_places=2)
    autres_frais = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class Projet(models.Model):
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    culture = models.ForeignKey(Culture, on_delete=models.CASCADE)
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    investissement_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    benefices_estimes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


# models.py de votre application Django
from django.db import models

class FruitLegume(models.Model):
    nom = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nom
