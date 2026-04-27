from django.contrib.auth.models import AbstractUser, User
from django.core.validators import MinValueValidator
from django.db import models
import uuid
import secrets
import string
from django.utils.timezone import now

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class Ferme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    proprietaire = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='fermes')
    pays = models.ForeignKey('Pays', on_delete=models.SET_NULL, null=True, blank=True)
    localite = models.ForeignKey('Localite', on_delete=models.SET_NULL, null=True, blank=True)
    superficie_totale = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Superficie totale de la ferme en hectares")
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude GPS de la ferme")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude GPS de la ferme")
    code_acces = models.CharField(max_length=12, unique=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Ferme {self.nom} ({self.proprietaire.user.username})"

    def save(self, *args, **kwargs):
        if not self.code_acces:
            alphabet = string.ascii_uppercase + string.digits
            while True:
                code = ''.join(secrets.choice(alphabet) for _ in range(8))
                if not Ferme.objects.filter(code_acces=code).exists():
                    self.code_acces = code
                    break
        super().save(*args, **kwargs)


class MembreFerme(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('technicien', 'Technicien'),
        ('ouvrier', 'Ouvrier'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='membres')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='fermes_membre')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ouvrier')
    peut_gerer_membres = models.BooleanField(default=False)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ferme', 'utilisateur')

    def __str__(self):
        return f"{self.utilisateur.user.username} - {self.get_role_display()} de {self.ferme.nom}"


class DemandeAccesFerme(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuvee', 'Approuvée'),
        ('refusee', 'Refusée'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='demandes_acces')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='demandes_acces_ferme')
    code = models.CharField(max_length=12)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_demande']
        constraints = [
            models.UniqueConstraint(
                fields=['ferme', 'utilisateur'],
                condition=models.Q(statut='en_attente'),
                name='unique_demande_en_attente_par_ferme_utilisateur',
            ),
        ]

    def __str__(self):
        return f"{self.utilisateur.user.username} demande l'accès à {self.ferme.nom}"


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
    
    # Nouveaux champs pour IA (agronomiques)
    cycle_culture_jours = models.IntegerField(null=True, blank=True, help_text="Durée moyenne entre semis et récolte (jours)")
    besoin_eau_mm = models.FloatField(null=True, blank=True, help_text="Besoin en eau total pour le cycle (mm)")
    rendement_potentiel_max = models.FloatField(null=True, blank=True, help_text="Rendement record possible (kg/ha)")

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
    class TypeSol(models.TextChoices):
        DIOR = 'Dior', 'Dior'
        DECK = 'Deck', 'Deck'
        DECK_DIOR = 'Deck-Dior', 'Deck-Dior'
        SABLONNEUX = 'Sablonneux', 'Sablonneux'
        LATERITIQUE = 'Latéritique', 'Latéritique'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, null=True, blank=True, related_name='localites')
    nom = models.CharField(max_length=100, unique=True)
    type_sol = models.CharField(max_length=50, choices=TypeSol.choices, null=True, blank=True)
    pluviometrie_moyenne = models.FloatField(null=True, blank=True, help_text="Pluviométrie moyenne annuelle/saisonnière (mm)")
    conditions_meteo = models.CharField(max_length=100, null=True, blank=True)
    details_meteo = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.nom
        




class HistoriqueRendement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE, related_name='historiques')
    produit = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, related_name='historiques')
    annee = models.IntegerField(help_text="Année de la récolte")
    rendement_reel_kg_ha = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rendement réel obtenu (kg/hectare)")
    pluviometrie_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Pluviométrie enregistrée cette année-là (mm)")

    class Meta:
        unique_together = ['localite', 'produit', 'annee']
        verbose_name_plural = "Historiques de Rendement"

    def __str__(self):
        return f"{self.produit.nom} à {self.localite.nom} ({self.annee})"



class Projet(models.Model):
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('en_pause', 'En pause'),
        ('fini', 'Fini'),
    ]

    class TypeIrrigation(models.TextChoices):
        AUCUNE = 'Aucune', 'Aucune (Pluvial)'
        GOUTTE_A_GOUTTE = 'Goutte-à-goutte', 'Goutte-à-goutte'
        ASPERSION = 'Aspersion', 'Aspersion'
        GRAVITAIRE = 'Gravitaire', 'Gravitaire (Canaux)'
        MANUELLE = 'Manuelle', 'Manuelle (Arrosoir)'

    class TypeEngrais(models.TextChoices):
        AUCUN = 'Aucun', 'Aucun (Naturel)'
        ORGANIQUE = 'Organique', 'Organique (Fumier, Compost)'
        MINERAL_NPK = 'Minéral NPK', 'Minéral (NPK)'
        MINERAL_UREE = 'Minéral Urée', 'Minéral (Urée)'
        MIXTE = 'Mixte', 'Mixte (Organique + Minéral)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='projets')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE)
    pays = models.ForeignKey(Pays, on_delete=models.SET_NULL, null=True, blank=True)
    culture = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, null=True, blank=True)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE)
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Image de fond du projet
    image_fond = models.ImageField(upload_to='projets_fonds/', null=True, blank=True, help_text="Image de couverture du projet (optionnelle)")
    
    # Pratiques Agronomiques
    type_irrigation = models.CharField(max_length=50, choices=TypeIrrigation.choices, default=TypeIrrigation.AUCUNE)
    type_engrais = models.CharField(max_length=50, choices=TypeEngrais.choices, default=TypeEngrais.AUCUN)
    
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
    quantite_semences = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.1)], help_text="Quantite de semences en kg")
    superficie_allouee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.01)], help_text="Superficie allouee a ce produit en hectares")
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

class PrevisionRecolte(models.Model):
    projet = models.OneToOneField(Projet, on_delete=models.CASCADE, related_name='prevision')
    rendement_estime_min = models.FloatField(default=0)
    rendement_estime_max = models.FloatField(default=0)
    indice_confiance = models.FloatField(null=True, blank=True, help_text="Indice de confiance du modèle IA (pourcentage)")
    date_recolte_prevue = models.DateField(null=True, blank=True)
    date_prediction = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prévision pour {self.projet.nom} ({self.indice_confiance or 0}%)"


class Tache(models.Model):
    """Tâche assignée à un membre d'une ferme par un supérieur hiérarchique.

    Hiérarchie d'attribution :
      - Propriétaire : peut assigner à manager, technicien, ouvrier
      - Manager      : peut assigner à technicien, ouvrier
      - Technicien   : peut assigner à ouvrier
      - Ouvrier      : ne peut pas créer de tâches (exécute uniquement)

    L'assigné peut faire évoluer le statut de SES tâches (à_faire → en_cours →
    terminée) et ajouter un commentaire de retour. Le créateur ou le
    propriétaire de la ferme peut annuler ou supprimer.
    """
    PRIORITE_CHOICES = [
        ('basse', 'Basse'),
        ('normale', 'Normale'),
        ('haute', 'Haute'),
        ('urgente', 'Urgente'),
    ]
    STATUT_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='taches')
    projet = models.ForeignKey(
        Projet, on_delete=models.SET_NULL, related_name='taches',
        null=True, blank=True,
        help_text="Projet concerné par la tâche (optionnel)."
    )
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigne_a = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='taches_recues',
        help_text="Membre à qui la tâche est assignée."
    )
    assigne_par = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, related_name='taches_creees',
        help_text="Auteur de la tâche."
    )
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default='normale')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='a_faire')
    date_echeance = models.DateField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_terminee = models.DateTimeField(null=True, blank=True)
    commentaire_retour = models.TextField(
        blank=True,
        help_text="Commentaire laissé par l'assigné lors de la mise à jour."
    )

    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['ferme', 'statut']),
            models.Index(fields=['assigne_a', 'statut']),
        ]

    def __str__(self):
        return f"{self.titre} → {self.assigne_a.user.username} ({self.get_statut_display()})"

    @property
    def est_en_retard(self):
        if not self.date_echeance or self.statut in ('terminee', 'annulee'):
            return False
        from django.utils.timezone import now as _now
        return self.date_echeance < _now().date()

    @staticmethod
    def role_dans_ferme(profile, ferme):
        """Retourne 'proprietaire' / 'manager' / 'technicien' / 'ouvrier' / None."""
        if ferme.proprietaire_id == profile.id:
            return 'proprietaire'
        membre = ferme.membres.filter(utilisateur=profile).first()
        return membre.role if membre else None

    @staticmethod
    def roles_assignables_par(role):
        """Rôles qu'un utilisateur peut assigner selon son propre rôle."""
        return {
            'proprietaire': ['manager', 'technicien', 'ouvrier'],
            'manager': ['technicien', 'ouvrier'],
            'technicien': ['ouvrier'],
            'ouvrier': [],
            None: [],
        }.get(role, [])

    def peut_etre_modifiee_par(self, profile):
        """Le créateur, le propriétaire de la ferme, ou l'assigné (statut/commentaire)."""
        if self.assigne_par_id == profile.id:
            return True
        if self.ferme.proprietaire_id == profile.id:
            return True
        return False

    def peut_changer_statut(self, profile):
        return self.assigne_a_id == profile.id or self.peut_etre_modifiee_par(profile)








