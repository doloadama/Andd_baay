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



class Pays(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    code_iso = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return self.nom

class Localite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, null=True, blank=True, related_name='localites')
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
    pays = models.ForeignKey(Pays, on_delete=models.SET_NULL, null=True, blank=True)
    # Keep culture for backwards compatibility, but produits will be the main relation
    culture = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, null=True, blank=True)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE)
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Multiple products relation
    produits = models.ManyToManyField(ProduitAgricole, through='ProjetProduit', related_name='projets_multi')

    def __str__(self):
        cultures = self.projet_produits.all()
        if cultures.exists():
            culture_names = ", ".join([pp.produit.nom for pp in cultures[:2]])
            if cultures.count() > 2:
                culture_names += f" (+{cultures.count() - 2})"
            return f"Projet {self.nom} - {culture_names} by {self.utilisateur.user.username}"
        elif self.culture:
            return f"Projet {self.nom} - {self.culture.nom} by {self.utilisateur.user.username}"
        return f"Projet {self.nom} by {self.utilisateur.user.username}"
    
    @property
    def rendement_total_final(self):
        """Calcule le rendement final total de tous les produits du projet"""
        total = self.projet_produits.aggregate(total=models.Sum('rendement_final'))['total']
        return total or 0


class ProjetProduit(models.Model):
    """Model to link products to projects with sowing and harvest data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='projet_produits')
    produit = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, related_name='projet_produits')
    
    # Sowing data
    quantite_semences = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Quantite de semences en kg")
    superficie_allouee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Superficie allouee a ce produit en hectares")
    date_semis = models.DateField(null=True, blank=True, help_text="Date du semis")
    date_recolte_prevue = models.DateField(null=True, blank=True, help_text="Date de recolte prevue")

    # Current state
    image = models.ImageField(upload_to='plants_photos/', null=True, blank=True, help_text="Photo du plant")
    age_plant = models.IntegerField(null=True, blank=True, help_text="Age du plant (ex: en jours)")
    
    # Harvest data (filled when project is finished)
    rendement_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rendement final obtenu en kg")
    date_recolte_effective = models.DateField(null=True, blank=True, help_text="Date de recolte effective")
    notes = models.TextField(blank=True, null=True, help_text="Notes et observations")
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_creation']
        unique_together = ['projet', 'produit']
        verbose_name = 'Produit du Projet'
        verbose_name_plural = 'Produits du Projet'
    
    def __str__(self):
        return f"{self.produit.nom} - {self.projet.nom}"
    
    @property
    def rendement_estime(self):
        """Calcule le rendement estime base sur la superficie et le rendement moyen du produit"""
        if self.superficie_allouee and self.produit.rendement_moyen:
            return float(self.superficie_allouee * self.produit.rendement_moyen)
        return 0



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








