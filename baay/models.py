from django.contrib.auth.models import AbstractUser, User
from django.db import models
import uuid
from django.utils.timezone import now

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username




class ProduitAgricole(models.Model):
    STATUTS = {
        'En croissance': 'bg-success',
        'Récolté': 'bg-primary',
        'Problème': 'bg-danger',
        'Autre': 'bg-secondary'
    }

    id = models.UUIDField(primary_key=True, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    saison = models.CharField(max_length=50, blank=True, null=True)
    prix_par_kg = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    apport_nutritionnel = models.TextField(blank=True, null=True)
    quantite_disponible = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    periode_recolte = models.CharField(max_length=100, blank=True, null=True)
    duree_avant_recolte = models.IntegerField(blank=True, null=True)
    rendement_moyen = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    etat = models.CharField(max_length=100, choices= STATUTS, default='En croissance')

    def __str__(self):
        return self.nom


class Localite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    type_sol = models.CharField(max_length=50, null=True, blank=True)
    conditions_meteo = models.CharField(max_length=100, null=True, blank=True)
    details_meteo = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.nom



class Projet(models.Model):
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('en_pause', 'En pause'),
        ('fini', 'Fini'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE)
    culture = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE)
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Projet {self.nom} - {self.culture.nom} by {self.utilisateur.user.username}"



class Investissement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=False)
    cout_par_hectare = models.DecimalField(max_digits=10, decimal_places=2)
    autres_frais = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    date_investissement = models.DateField(default=now)

    def calculer_investissement_total(self):
        return self.cout_par_hectare * self.projet.superficie + self.autres_frais

    def __str__(self):
        return f"Investissement {self.id} pour le projet {self.projet.nom}"

class PredictionRendement(models.Model):
    projet = models.OneToOneField('Projet', on_delete=models.CASCADE, related_name='prediction')
    rendement_estime = models.FloatField()
    date_prediction = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prédiction pour {self.projet.nom}"
