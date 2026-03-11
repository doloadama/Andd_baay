from django.contrib.auth.models import AbstractUser, User
from django.db import models
import uuid
from django.dispatch import receiver
from django.utils.timezone import now
from django.db.models.signals import post_save

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class ProduitAgricole(models.Model):
    STATUTS = [
        ('En croissance', 'En croissance'),
        ('Récolté', 'Récolté'),
        ('Problème', 'Problème'),
        ('Autre', 'Autre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        return f"{self.nom} - {self.saison or 'Indéfini'}"
        

class PhotoProduitAgricole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    produit = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='produits_photos/')
    description = models.TextField(blank=True, null=True)

    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo de {self.produit.nom} - {self.date_ajout.strftime('%Y-%m-%d %H:%M:%S')}"



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


class Semis(models.Model):
    """Model to track sowings/plantings by users"""
    STATUT_CHOICES = [
        ('planifie', 'Planifié'),
        ('seme', 'Semé'),
        ('en_croissance', 'En croissance'),
        ('recolte', 'Récolté'),
        ('echec', 'Échec'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='semis')
    culture = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, related_name='semis')
    projet = models.ForeignKey(Projet, on_delete=models.SET_NULL, null=True, blank=True, related_name='semis')
    
    quantite_semences = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantité de semences en kg")
    superficie_semee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Superficie semée en hectares")
    
    date_semis = models.DateField(help_text="Date du semis")
    date_recolte_prevue = models.DateField(null=True, blank=True, help_text="Date de récolte prévue")
    date_recolte_effective = models.DateField(null=True, blank=True, help_text="Date de récolte effective")
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifie')
    
    notes = models.TextField(blank=True, null=True, help_text="Notes et observations")
    
    rendement_obtenu = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rendement obtenu en kg")
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_semis']
        verbose_name = 'Semis'
        verbose_name_plural = 'Semis'
    
    def __str__(self):
        return f"Semis de {self.culture.nom} - {self.date_semis}"
    
    @property
    def jours_depuis_semis(self):
        """Calcule le nombre de jours depuis le semis"""
        from datetime import date
        if self.date_semis:
            return (date.today() - self.date_semis).days
        return 0
    
    @property
    def jours_avant_recolte(self):
        """Calcule le nombre de jours avant la récolte prévue"""
        from datetime import date
        if self.date_recolte_prevue:
            delta = (self.date_recolte_prevue - date.today()).days
            return max(0, delta)
        return None



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

