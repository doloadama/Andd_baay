from django.contrib.auth.models import AbstractUser, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.timezone import now
from decimal import Decimal
import uuid
import secrets
import string

from cloudinary.models import CloudinaryField

from baay.cloudinary_paths import cloudinary_media_folder


class Profile(models.Model):
    # Type de compte choisi à l'inscription : pilote UNIQUEMENT le parcours
    # d'onboarding, jamais les permissions (celles-ci viennent des rôles
    # MembreFerme / MembreCooperative). NULL = pas encore choisi.
    ACCOUNT_TYPE_FERMIER = 'fermier'
    ACCOUNT_TYPE_COOPERATIVE = 'cooperative'
    ACCOUNT_TYPE_TECHNICIEN = 'technicien'
    ACCOUNT_TYPE_OUVRIER = 'ouvrier'
    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_TYPE_FERMIER, 'Fermier indépendant'),
        (ACCOUNT_TYPE_COOPERATIVE, 'Coopérative'),
        (ACCOUNT_TYPE_TECHNICIEN, 'Technicien agricole'),
        (ACCOUNT_TYPE_OUVRIER, 'Ouvrier agricole'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Type de compte choisi à l'inscription ; pilote le parcours d'onboarding.",
    )
    onboarding_completed = models.BooleanField(
        default=False,
        help_text="True lorsque l'utilisateur a terminé ou ignoré l'assistant de première connexion.",
    )

    def __str__(self):
        return self.user.username

class Ferme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    proprietaire = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='fermes')
    cooperative = models.ForeignKey(
        'Cooperative', on_delete=models.SET_NULL, null=True, blank=True, related_name='fermes',
        help_text="Coopérative à laquelle la ferme est affiliée (le propriétaire reste propriétaire).",
    )
    pays = models.ForeignKey('Pays', on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(
        "Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fermes",
        help_text="Division administrative (filtre performances / cartes).",
    )
    localite = models.ForeignKey('Localite', on_delete=models.SET_NULL, null=True, blank=True)
    superficie_totale = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Superficie totale de la ferme en hectares")
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude GPS de la ferme")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude GPS de la ferme")
    image_couverture = CloudinaryField(
        "image_couverture",
        null=True,
        blank=True,
        folder=cloudinary_media_folder("fermes"),
        help_text="Photo principale / vue de la ferme",
    )
    image_infrastructure = CloudinaryField(
        "image_infrastructure",
        null=True,
        blank=True,
        folder=cloudinary_media_folder("fermes/infrastructures"),
        help_text="Photo des infrastructures ou équipements (optionnel)",
    )
    code_acces = models.CharField(max_length=12, unique=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    TIER_BASIC = 'basic'
    TIER_PRO = 'pro'
    TIER_COOP = 'coop'
    TIER_CHOICES = [
        (TIER_BASIC, 'Baay Basique (Gratuit)'),
        (TIER_PRO, 'Baay Pro (SaaS)'),
        (TIER_COOP, 'Baay Coopérative (B2B)'),
    ]

    subscription_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_BASIC,
        help_text="Niveau d'abonnement de la ferme"
    )
    subscription_expiration = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date d'expiration de l'abonnement premium"
    )

    @property
    def is_premium(self):
        if self.subscription_tier in [self.TIER_PRO, self.TIER_COOP]:
            if self.subscription_expiration is None or self.subscription_expiration > timezone.now():
                return True
        return False

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Ferme {self.nom} ({self.proprietaire.user.username})"

    def clean(self):
        super().clean()
        if self.region_id and self.pays_id and self.region and self.region.pays_id != self.pays_id:
            raise ValidationError({"region": "La région ne correspond pas au pays de la ferme."})
        if self.localite_id and self.pays_id and self.localite and self.localite.pays_id and self.localite.pays_id != self.pays_id:
            raise ValidationError({"localite": "La localité sélectionnée n'est pas dans le même pays que la ferme."})
        if self.localite_id and self.region_id and self.localite and self.localite.region_id and self.localite.region_id != self.region_id:
            raise ValidationError(
                {"localite": "La localité doit appartenir à la même région que celle sélectionnée lorsque les deux sont renseignées."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.code_acces:
            self.code_acces = self.generate_unique_code_acces(
                exclude_pk=self.pk if self.pk else None
            )
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_code_acces(cls, exclude_pk=None):
        """Génère un code alphanumérique unique (8 caractères)."""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            qs = cls.objects.filter(code_acces=code)
            if exclude_pk:
                qs = qs.exclude(pk=exclude_pk)
            if not qs.exists():
                return code

    def regenerate_code_acces(self):
        """Nouveau code d'accès (invalide l'ancien). À n'utiliser que pour le propriétaire."""
        self.code_acces = self.generate_unique_code_acces(exclude_pk=self.pk)
        self.save(update_fields=["code_acces", "date_modification"])


class MembreFerme(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('technicien', 'Technicien'),
        ('ouvrier', 'Ouvrier'),
        ('consultant', 'Consultant'),
        ('invite', 'Invité'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='membres')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='fermes_membre')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ouvrier')
    peut_gerer_membres = models.BooleanField(default=False)
    date_expiration = models.DateTimeField(
        null=True, blank=True,
        help_text="Date d'expiration de l'accès (pour les rôles temporaires)."
    )
    date_ajout = models.DateTimeField(auto_now_add=True)
    photo_profil = CloudinaryField(
        "photo_profil",
        null=True,
        blank=True,
        folder=cloudinary_media_folder("profils"),
        help_text="Photo du collaborateur (membre de la ferme)",
    )

    class Meta:
        unique_together = ('ferme', 'utilisateur')
        indexes = [
            models.Index(fields=["utilisateur", "date_expiration"], name="baay_membre_user_expiry_idx"),
            models.Index(fields=["ferme", "date_expiration"], name="baay_membre_ferme_expiry_idx"),
        ]

    def __str__(self):
        return f"{self.utilisateur.user.username} - {self.get_role_display()} de {self.ferme.nom}"


class Cooperative(models.Model):
    """Organisation regroupant plusieurs fermes affiliées. Couche de gestion
    au-dessus des fermes : les fermes gardent leur propriétaire, la coopérative
    y accède via les rôles MembreCooperative (cf. permissions.py)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    pays = models.ForeignKey('Pays', on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey('Region', on_delete=models.SET_NULL, null=True, blank=True)
    localite = models.ForeignKey('Localite', on_delete=models.SET_NULL, null=True, blank=True)
    code_acces = models.CharField(max_length=12, unique=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.code_acces:
            self.code_acces = self.generate_unique_code_acces(
                exclude_pk=self.pk if self.pk else None
            )
        super().save(*args, **kwargs)

    @classmethod
    def generate_unique_code_acces(cls, exclude_pk=None):
        """Code alphanumérique unique (8 caractères), préfixé C pour les coops."""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "C" + "".join(secrets.choice(alphabet) for _ in range(7))
            qs = cls.objects.filter(code_acces=code)
            if exclude_pk:
                qs = qs.exclude(pk=exclude_pk)
            if not qs.exists():
                return code

    def regenerate_code_acces(self):
        self.code_acces = self.generate_unique_code_acces(exclude_pk=self.pk)
        self.save(update_fields=["code_acces", "date_modification"])


class MembreCooperative(models.Model):
    ROLE_ADMIN = 'admin'                 # Président / admin : contrôle total de la coop
    ROLE_GESTIONNAIRE = 'gestionnaire'   # Gère fermes & projets, pas membres/finances
    ROLE_TECHNICIEN = 'technicien'       # Suivi technique sur toutes les fermes de la coop
    ROLE_CONSULTANT = 'consultant'       # Lecture seule (finance / performance)
    ROLE_FERMIER_AFFILIE = 'fermier_affilie'  # Possède sa ferme, agrégée dans la coop
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin / Président'),
        (ROLE_GESTIONNAIRE, 'Gestionnaire'),
        (ROLE_TECHNICIEN, 'Technicien coop'),
        (ROLE_CONSULTANT, 'Consultant'),
        (ROLE_FERMIER_AFFILIE, 'Fermier affilié'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE, related_name='membres')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='cooperatives_membre')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_FERMIER_AFFILIE)
    peut_gerer_membres = models.BooleanField(default=False)
    statut = models.CharField(
        max_length=12,
        choices=[('actif', 'Actif'), ('suspendu', 'Suspendu')],
        default='actif',
    )
    date_adhesion = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('cooperative', 'utilisateur')
        indexes = [
            models.Index(fields=["utilisateur", "statut"], name="baay_coopmembre_user_idx"),
        ]

    def __str__(self):
        return f"{self.utilisateur.user.username} - {self.get_role_display()} de {self.cooperative.nom}"


class InvitationFerme(models.Model):
    """Lien d'invitation tokenisé permettant à un propriétaire d'inviter techniciens/ouvriers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='invitations')
    token = models.CharField(max_length=64, unique=True, editable=False)
    cree_par = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='invitations_creees')
    role_invite = models.CharField(
        max_length=20,
        choices=[('technician', 'Technicien'), ('worker', 'Ouvrier')],
        default='technician'
    )
    email_invite = models.EmailField(blank=True)
    utilisee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            from django.utils import timezone as _tz
            from datetime import timedelta
            self.expires_at = _tz.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        from django.utils import timezone as _tz
        return not self.utilisee and self.expires_at > _tz.now()

    def __str__(self):
        return f"Invitation {self.ferme.nom} ({self.role_invite}) — {'utilisée' if self.utilisee else 'active'}"


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

    def clean(self):
        super().clean()
        if not self.ferme_id or not self.utilisateur_id:
            return
        if self.ferme.proprietaire_id == self.utilisateur_id:
            raise ValidationError(
                {"utilisateur": "Le propriétaire d'une ferme ne peut pas envoyer de demande d'accès pour celle-ci."}
            )
        if MembreFerme.objects.filter(ferme_id=self.ferme_id, utilisateur_id=self.utilisateur_id).exists():
            raise ValidationError(
                {"utilisateur": "Vous êtes déjà membre de cette ferme ; une demande d'accès est inutile."}
            )
        # Empêche plusieurs demandes actives (en attente) pour la même ferme
        active_qs = DemandeAccesFerme.objects.filter(
            ferme_id=self.ferme_id,
            utilisateur_id=self.utilisateur_id,
            statut='en_attente',
        )
        if self.pk:
            active_qs = active_qs.exclude(pk=self.pk)
        if active_qs.exists():
            raise ValidationError({"statut": "Une demande en attente existe déjà pour cette ferme."})


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
    image = CloudinaryField("image", folder=cloudinary_media_folder("produits/catalogue"))
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


class Region(models.Model):
    """Région / division administrative nationale (filtre géographique fin)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name="regions")
    nom = models.CharField(max_length=150)
    code = models.CharField(
        max_length=32,
        blank=True,
        help_text="Code officiel facultatif (ex. ISO subdivisions).",
    )

    class Meta:
        verbose_name = "Région"
        verbose_name_plural = "Régions"
        ordering = ["pays__nom", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["pays", "nom"], name="uniq_region_nom_par_pays"),
        ]

    def __str__(self):
        return f"{self.nom} ({self.pays})"


class Localite(models.Model):
    class TypeSol(models.TextChoices):
        DIOR = 'Dior', 'Dior'
        DECK = 'Deck', 'Deck'
        DECK_DIOR = 'Deck-Dior', 'Deck-Dior'
        SABLONNEUX = 'Sablonneux', 'Sablonneux'
        LATERITIQUE = 'Latéritique', 'Latéritique'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, null=True, blank=True, related_name='localites')
    region = models.ForeignKey(
        "Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="localites",
        help_text="Rattache la localité pour des filtres cartographiques / agrégations régionales.",
    )
    nom = models.CharField(max_length=100, unique=True)
    type_sol = models.CharField(max_length=50, choices=TypeSol.choices, null=True, blank=True)
    pluviometrie_moyenne = models.FloatField(null=True, blank=True, help_text="Pluviométrie moyenne annuelle/saisonnière (mm)")
    conditions_meteo = models.CharField(max_length=100, null=True, blank=True)
    details_meteo = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def clean(self):
        super().clean()
        if self.region_id and self.pays_id and self.region and self.region.pays_id != self.pays_id:
            raise ValidationError(
                {"region": "La région choisie n'appartient pas au même pays que la localité."}
            )

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
    """
    Statuts projet :
    - en_cours / en_pause : activité en cours.
    - fini : travaux ou récolte terminés ; saisie de recettes / investissements / dépenses encore possible.

    - cloture : clôture comptable (via cloturer_projet ou passage manuel depuis « Fini » uniquement).
      Aucun mouvement financier ni modification de recette/dépense/investissement.
    """
    STATUT_CLOTURE = "cloture"

    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('en_pause', 'En pause'),
        ('fini', 'Fini'),
        (STATUT_CLOTURE, 'Clôturé'),
    ]

    TYPE_CYCLE_CAMPAGNE = "campagne"
    TYPE_CYCLE_PERENNE = "perenne"
    TYPE_CYCLE_CHOICES = [
        (TYPE_CYCLE_CAMPAGNE, "Campagne saisonniere"),
        (TYPE_CYCLE_PERENNE, "Projet perenne"),
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
    type_cycle = models.CharField(
        max_length=20,
        choices=TYPE_CYCLE_CHOICES,
        default=TYPE_CYCLE_CAMPAGNE,
        help_text="Campagne courte (riz, mais...) ou projet perenne avec campagnes successives.",
    )
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE)
    pays = models.ForeignKey(Pays, on_delete=models.SET_NULL, null=True, blank=True)
    culture = models.ForeignKey(ProduitAgricole, on_delete=models.CASCADE, null=True, blank=True)
    localite = models.ForeignKey(Localite, on_delete=models.CASCADE)
    superficie = models.DecimalField(max_digits=10, decimal_places=2)
    date_lancement = models.DateField()
    date_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Date de fin prévue ou de clôture opérationnelle du projet (avec la date de "
        "lancement, sert au calcul du taux d'avancement par défaut).",
    )
    taux_avancement_personnalise = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Remplace le calcul automatique (dates début / fin). Réservé au manager de la "
        "ferme et aux administrateurs.",
    )
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_alloue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget prévisionnel total du projet (FCFA). Utilisé pour les alertes de dépassement.",
    )
    
    # Image de fond du projet
    image_fond = CloudinaryField(
        "image_fond",
        null=True,
        blank=True,
        folder=cloudinary_media_folder("projets/couvertures"),
        help_text="Image de couverture du projet (optionnelle)",
    )
    
    # Pratiques Agronomiques (optionnel côté saisie ; défauts si non renseigné)
    type_irrigation = models.CharField(
        max_length=50,
        choices=TypeIrrigation.choices,
        default=TypeIrrigation.AUCUNE,
        blank=True,
    )
    type_engrais = models.CharField(
        max_length=50,
        choices=TypeEngrais.choices,
        default=TypeEngrais.AUCUN,
        blank=True,
    )
    
    # Multiple products relation
    produits = models.ManyToManyField(ProduitAgricole, through='ProjetProduit', related_name='projets_multi')

    class Meta:
        indexes = [
            models.Index(fields=["ferme", "statut"], name="baay_projet_ferme_stat_idx"),
            models.Index(fields=["utilisateur", "statut"], name="baay_projet_user_stat_idx"),
            models.Index(fields=["ferme", "date_lancement"], name="baay_projet_ferme_lanc_idx"),
        ]

    def __str__(self):
        return f"Projet {self.nom}"

    @classmethod
    def statuts_fin_activite(cls):
        """Fini (opérationnel) ou Clôturé (comptable) : plus d'activité terrain habituelle."""
        return ('fini', cls.STATUT_CLOTURE)

    def clean(self):
        super().clean()
        from datetime import timedelta as _td
        from django.utils.dateparse import parse_date

        date_lancement = parse_date(self.date_lancement) if isinstance(self.date_lancement, str) else self.date_lancement
        date_fin = parse_date(self.date_fin) if isinstance(self.date_fin, str) else self.date_fin

        if not date_lancement:
            raise ValidationError({"date_lancement": "La date de début est obligatoire."})
        if date_fin:
            if date_fin <= date_lancement:
                raise ValidationError(
                    {
                        "date_fin": "La date de fin doit être strictement postérieure à la date de début du projet "
                        "(date de lancement)."
                    }
                )
            if self.statut not in ('fini', self.STATUT_CLOTURE) and date_fin < timezone.localdate():
                raise ValidationError({"date_fin": "La date de fin ne peut pas être dans le passé pour un projet actif."})
            # Durée raisonnable ≤ 2 ans
            if self.type_cycle != self.TYPE_CYCLE_PERENNE and (date_fin - date_lancement).days > 730:
                raise ValidationError({"date_fin": "La durée d'un projet ne doit pas excéder 2 ans."})
        else:
            # Projet en cours: ne pas démarrer dans un futur lointain (> 2 ans)
            today = timezone.localdate()
            if date_lancement > (today + _td(days=730)):
                raise ValidationError({"date_lancement": "La date de début ne peut pas dépasser 2 ans dans le futur."})

        if self.statut == self.STATUT_CLOTURE and not self.pk:
            raise ValidationError(
                {"statut": "Un projet ne peut pas être créé directement à l'état « Clôturé »."}
            )
        if self.pk:
            precedent = Projet.objects.filter(pk=self.pk).only("statut").first()
            if precedent is not None and self.statut == self.STATUT_CLOTURE:
                if precedent.statut != self.STATUT_CLOTURE and precedent.statut != "fini":
                    raise ValidationError(
                        {
                            "statut": "Le statut « Clôturé » n'est possible qu'après « Fini » "
                            "(fin des travaux). Ensuite, utilisez la clôture comptable côté finance "
                            "ou passez le statut manuellement depuis « Fini »."
                        }
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def rendement_total_final(self):
        """Calcule le rendement final total de tous les produits du projet"""
        total = self.projet_produits.aggregate(total=models.Sum('rendement_final'))['total']
        return total or 0

    def _taux_avancement_temporel(self) -> float:
        """
        Avancement 0–100 % à partir de la date de début et de la date de fin (clôture prévue/réelle).
        Sans date_fin : progression provisoire sur une fenêtre de 365 jours après le lancement.
        """
        today = timezone.localdate()
        if self.statut in ("fini", self.STATUT_CLOTURE):
            return 100.0
        start = self.date_lancement
        if not start:
            return 0.0
        end = self.date_fin
        if end and end > start:
            denom_days = (end - start).days or 1
            if today >= end:
                return 100.0
            elapsed = (min(today, end) - start).days
            return max(0.0, min(100.0, (elapsed / denom_days) * 100.0))
        elapsed = (today - start).days
        return max(0.0, min(100.0, (elapsed / 365.0) * 100.0))

    def _temps_pct_ajuste_pause(self) -> float:
        """Progression temporelle 0–100 (plafonnée pour les projets en pause)."""
        t = self._taux_avancement_temporel()
        if self.statut == "en_pause":
            t = min(t, 75.0)
        return t

    def _taches_avancement_stats(self) -> tuple[int, int, float | None]:
        """
        Tâches rattachées au projet (hors annulées) : (total, terminées, % terminées ou None).

        Utilise le cache prefetch ``_taches_for_avancement`` si disponible (detail_projet view)
        pour éviter une requête SQL supplémentaire sur les pages qui ont déjà préchargé les tâches.
        """
        cached = getattr(self, "_taches_for_avancement", None)
        if cached is not None:
            # Le prefetch exclut déjà 'annulee' ; on filtre par sécurité
            taches = [t for t in cached if t.statut != "annulee"]
            total = len(taches)
            done = sum(1 for t in taches if t.statut == "terminee")
        else:
            stats = self.taches.exclude(statut="annulee").aggregate(
                total=Count("id"),
                done=Count("id", filter=Q(statut="terminee")),
            )
            total = stats["total"] or 0
            done = stats["done"] or 0
        if total <= 0:
            return 0, 0, None
        return total, done, max(0.0, min(100.0, (done / total) * 100.0))

    def _progression_auto_combinee(
        self, taches_stats: tuple[int, int, float | None] | None = None
    ) -> float:
        """
        Taux 0–100 sans valeur manuelle : moyenne du temps et des tâches si des tâches existent,
        sinon uniquement le temps.
        """
        time_v = self._temps_pct_ajuste_pause()
        if self.statut in ("fini", self.STATUT_CLOTURE):
            return 100.0
        if taches_stats is None:
            taches_stats = self._taches_avancement_stats()
        _total, _done, tasks_pct = taches_stats
        if tasks_pct is not None:
            return max(0.0, min(100.0, (time_v + tasks_pct) / 2.0))
        return max(0.0, min(100.0, time_v))

    def _taux_avancement_calcule(self) -> int:
        """Taux calculé (temps + tâches du projet) avant toute valeur personnalisée."""
        return int(max(0, min(100, round(self._progression_auto_combinee()))))

    def _avancement_breakdown(self) -> dict:
        time_pct = self._temps_pct_ajuste_pause()
        t_stats = self._taches_avancement_stats()
        t_total, t_done, tasks_pct = t_stats
        has_tasks = t_total > 0
        tasks_pct_rounded = None if tasks_pct is None else round(tasks_pct, 1)
        auto_f = self._progression_auto_combinee(t_stats)

        manual = self.taux_avancement_personnalise
        if manual is not None:
            combined = int(max(0, min(100, manual)))
            return {
                "combined": combined,
                "tasks_pct": tasks_pct_rounded,
                "time_pct": round(time_pct, 1),
                "has_tasks": has_tasks,
                "tasks_total": t_total,
                "tasks_done": t_done,
                "is_manual": True,
                "_auto_progress_float": auto_f,
            }

        combined = int(max(0, min(100, round(auto_f))))
        return {
            "combined": combined,
            "tasks_pct": tasks_pct_rounded,
            "time_pct": round(time_pct, 1),
            "has_tasks": has_tasks,
            "tasks_total": t_total,
            "tasks_done": t_done,
            "is_manual": False,
            "_auto_progress_float": auto_f,
        }

    @property
    def taux_avancement(self) -> int:
        """Progression 0–100 : tâches (liées au projet) + temps, ou valeur personnalisée."""
        return self._avancement_breakdown()["combined"]

    def avancement_pour_api(self) -> dict:
        """Sous-scores de progression pour les composants UI (anneaux, barres)."""
        d = self._avancement_breakdown()
        calc = int(max(0, min(100, round(d.pop("_auto_progress_float")))))
        out = {
            "taux_avancement": d["combined"],
            "progress_tasks_pct": d["tasks_pct"],
            "progress_time_pct": d["time_pct"],
            "taux_avancement_source": "personnalise" if d.get("is_manual") else "calcule",
            "has_project_tasks": d["has_tasks"],
            "tasks_total": d["tasks_total"],
            "tasks_done": d["tasks_done"],
        }
        if d.get("is_manual"):
            out["taux_avancement_calcule"] = calc
        return out

    @property
    def est_perenne(self) -> bool:
        return self.type_cycle == self.TYPE_CYCLE_PERENNE


class CampagneProjet(models.Model):
    """Cycle saisonnier rattache a un projet, surtout utile aux cultures perennes."""

    STATUT_PREPARATION = "preparation"
    STATUT_EN_COURS = "en_cours"
    STATUT_FINI = "fini"
    STATUT_CHOICES = [
        (STATUT_PREPARATION, "Preparation"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_FINI, "Terminee"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="campagnes")
    nom = models.CharField(max_length=120)
    saison = models.CharField(max_length=80, blank=True, default="")
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_EN_COURS)
    rendement_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Rendement total obtenu pendant cette campagne (kg).",
    )
    cout_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Cout total estime de cette campagne (FCFA).",
    )
    recette_totale = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Recette totale estimee de cette campagne (FCFA).",
    )
    notes = models.TextField(blank=True, default="")
    campagne_precedente = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campagnes_suivantes",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_debut", "-date_creation"]
        constraints = [
            models.UniqueConstraint(fields=["projet", "nom"], name="unique_campagne_nom_par_projet"),
        ]
        indexes = [
            models.Index(fields=["projet", "statut"], name="baay_campag_projet_stat_idx"),
            models.Index(fields=["projet", "date_debut"], name="baay_campag_projet_debut_idx"),
        ]
        verbose_name = "Campagne de projet"
        verbose_name_plural = "Campagnes de projet"

    def __str__(self):
        return f"{self.nom} - {self.projet.nom}"

    @property
    def benefice(self):
        if self.recette_totale is None and self.cout_total is None:
            return None
        return (self.recette_totale or Decimal("0")) - (self.cout_total or Decimal("0"))

    @property
    def rendement_par_hectare(self):
        if not self.rendement_total or not self.projet.superficie:
            return None
        return self.rendement_total / self.projet.superficie

    def clean(self):
        super().clean()
        if self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin ne peut pas etre anterieure a la date de debut."})
        if self.statut == self.STATUT_FINI and not self.date_fin:
            raise ValidationError({"date_fin": "Une campagne terminee doit avoir une date de fin."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
    image = CloudinaryField(
        "image",
        null=True,
        blank=True,
        folder=cloudinary_media_folder("projets/plants"),
        help_text="Photo du plant",
    )
    age_plant = models.IntegerField(null=True, blank=True, help_text="Age du plant (ex: en jours)")
    
    # Observation terrain (remplie par l'agriculteur en cours de culture)
    ETAT_VEGETATIF_CHOICES = [
        (1, 'Très mauvais'),
        (2, 'Mauvais'),
        (3, 'Normal'),
        (4, 'Bon'),
        (5, 'Excellent'),
    ]
    etat_vegetatif = models.IntegerField(
        choices=ETAT_VEGETATIF_CHOICES,
        null=True,
        blank=True,
        help_text="Observation terrain de l'état de la culture (1=très mauvais, 5=excellent).",
    )

    # Harvest data (filled when project is finished)
    rendement_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Rendement final obtenu en kg")
    date_recolte_effective = models.DateField(null=True, blank=True, help_text="Date de recolte effective")
    notes = models.TextField(blank=True, null=True, help_text="Notes et observations")
    budget_alloue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget optionnel alloué à cette culture (FCFA), pour alertes par produit.",
    )
    
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

    def clean(self):
        super().clean()
        from django.utils.dateparse import parse_date

        def _d(value):
            if value is None:
                return None
            return parse_date(value) if isinstance(value, str) else value

        projet = (
            Projet.objects.filter(pk=self.projet_id).first() if self.projet_id else None
        )

        date_semis = _d(self.date_semis)
        date_recolte_prevue = _d(self.date_recolte_prevue)
        date_recolte_effective = _d(self.date_recolte_effective)

        if projet:
            debut = _d(projet.date_lancement)
            fin = _d(projet.date_fin)
            if date_semis and debut:
                if date_semis <= debut:
                    raise ValidationError(
                        {
                            "date_semis": "La date de semis doit être strictement postérieure à la date de début "
                            "(lancement) du projet."
                        }
                    )
                if fin and date_semis >= fin:
                    raise ValidationError(
                        {
                            "date_semis": "La date de semis doit être strictement antérieure à la date de fin du projet."
                        }
                    )
            elif date_semis and not debut:
                raise ValidationError(
                    {"date_semis": "Le projet parent doit avoir une date de lancement pour valider la date de semis."}
                )

        if date_recolte_prevue:
            if not date_semis:
                raise ValidationError(
                    {
                        "date_recolte_prevue": "Renseignez d'abord la date de semis pour pouvoir indiquer une prévision de récolte."
                    }
                )
            if date_recolte_prevue <= date_semis:
                raise ValidationError(
                    {
                        "date_recolte_prevue": "La date de prévision de récolte doit être strictement postérieure à la date de semis."
                    }
                )

        if date_recolte_effective and date_semis:
            if date_recolte_effective < date_semis:
                raise ValidationError(
                    {
                        "date_recolte_effective": "La date de récolte effective ne peut pas être antérieure à la date de semis."
                    }
                )
        if date_recolte_prevue and projet:
            fin = _d(projet.date_fin)
            if fin and date_recolte_prevue > fin:
                raise ValidationError(
                    {
                        "date_recolte_prevue": "La prévision de récolte ne peut pas être postérieure à la date de fin du projet."
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AnalyseImageCulture(models.Model):
    """Résultat d'analyse IA (photo plante / ravageur) pour une culture."""

    TYPE_PLANT_PEST = "PLANT_PEST"
    TYPE_CHOICES = [(TYPE_PLANT_PEST, "Plante / ravageur (photo rapprochée)")]

    STATUT_EN_ATTENTE = "en_attente"
    STATUT_EN_COURS = "en_cours"
    STATUT_TERMINEE = "terminee"
    STATUT_ECHEC = "echec"
    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, "En attente"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_TERMINEE, "Terminée"),
        (STATUT_ECHEC, "Échec"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet_produit = models.ForeignKey(
        ProjetProduit,
        on_delete=models.CASCADE,
        related_name="analyses_image",
    )
    demandee_par = models.ForeignKey(
        "Profile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analyses_image_demandees",
    )
    type_analyse = models.CharField(
        max_length=32,
        choices=TYPE_CHOICES,
        default=TYPE_PLANT_PEST,
    )
    statut = models.CharField(
        max_length=16,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE,
        db_index=True,
    )
    image_hash = models.CharField(max_length=64, blank=True, db_index=True)
    resultat = models.JSONField(null=True, blank=True)
    sujet_type = models.CharField(max_length=32, blank=True)
    sujet_description = models.TextField(blank=True)
    message_erreur = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Analyse image culture"
        verbose_name_plural = "Analyses image culture"
        indexes = [
            models.Index(fields=["projet_produit", "-date_creation"]),
        ]

    def __str__(self):
        return f"Analyse {self.type_analyse} — {self.projet_produit_id} ({self.statut})"


class Investissement(models.Model):
    CATEGORIE_GENERAL = "general"
    CATEGORIE_CHOICES = [
        (CATEGORIE_GENERAL, "Général"),
        ("intrant", "Intrant"),
        ("main_oeuvre", "Main d'œuvre"),
        ("transport", "Transport"),
        ("irrigation", "Irrigation"),
        ("materiel", "Matériel"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE)
    projet_produit = models.ForeignKey(
        "ProjetProduit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investissements",
        help_text="Si vide : dépense générale au niveau projet. Sinon : affectée à cette culture.",
    )
    libelle = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Titre court affiché dans les listes (ex. achat engrais).",
    )
    categorie = models.CharField(
        max_length=32,
        choices=CATEGORIE_CHOICES,
        default=CATEGORIE_GENERAL,
    )
    description = models.TextField(null=True, blank=True)
    cout_par_hectare = models.DecimalField(max_digits=10, decimal_places=2)
    autres_frais = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    date_investissement = models.DateField(default=now)
    piece_justificative = CloudinaryField(
        "piece_justificative",
        null=True,
        blank=True,
        resource_type="auto",
        folder=cloudinary_media_folder("finance/investissements"),
        help_text="Justificatif (scan photo ou PDF — optimisé côté Cloudinary pour images)",
    )
    verrouille = models.BooleanField(default=False, help_text="Bloque la modification apres cloture du projet.")
    date_verrouillage = models.DateTimeField(null=True, blank=True)

    def superficie_reference(self):
        """Hectares utilisés pour le calcul du montant (culture si renseignée, sinon projet)."""
        if self.projet_produit_id and self.projet_produit.superficie_allouee:
            return self.projet_produit.superficie_allouee
        return self.projet.superficie

    def calculer_investissement_total(self):
        from decimal import Decimal

        autres = self.autres_frais or Decimal("0")
        ha = self.superficie_reference()
        return self.cout_par_hectare * ha + autres

    def libelle_affichage(self):
        """Libellé tableau / cartes : champ libelle ou extrait de description."""
        if self.libelle and self.libelle.strip():
            return self.libelle.strip()
        text = (self.description or "").strip()
        if text:
            return text.split("\n")[0][:255]
        return "—"

    def __str__(self):
        return f"Investissement {self.id} pour le projet {self.projet.nom}"

    def clean(self):
        super().clean()
        projet = (
            Projet.objects.filter(pk=self.projet_id).only("statut").first()
            if self.projet_id
            else None
        )
        if projet and projet.statut == Projet.STATUT_CLOTURE:
            raise ValidationError(
                "Impossible d'ajouter ou de modifier un investissement : le projet est clôturé."
            )
        if not self.pk:
            return
        ancien = Investissement.objects.filter(pk=self.pk).first()
        if not ancien or not ancien.verrouille:
            return
        champs_financiers = (
            "projet_id",
            "projet_produit_id",
            "libelle",
            "categorie",
            "description",
            "cout_par_hectare",
            "autres_frais",
            "date_investissement",
            "piece_justificative",
        )
        if any(getattr(ancien, champ) != getattr(self, champ) for champ in champs_financiers):
            raise ValidationError(
                "Cet investissement est verrouillé : la ligne ne peut plus être modifiée."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        projet = (
            Projet.objects.filter(pk=self.projet_id).only("statut").first()
            if self.projet_id
            else None
        )
        if projet and projet.statut == Projet.STATUT_CLOTURE:
            raise ValidationError(
                "Impossible de supprimer cet investissement : le projet est clôturé."
            )
        if self.verrouille:
            raise ValidationError(
                "Impossible de supprimer cet investissement : la ligne est verrouillée."
            )
        return super().delete(*args, **kwargs)


class Depense(models.Model):
    """Dépense simple liée à un projet (saisie directe, distincte des lignes Investissement)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="depenses")
    libelle = models.CharField(max_length=255)
    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date_depense = models.DateField(default=now)
    description = models.TextField(blank=True)
    justificatif = CloudinaryField(
        "justificatif",
        null=True,
        blank=True,
        resource_type="auto",
        folder=cloudinary_media_folder("finance/depenses"),
        help_text="Justificatif (photo / scan — léger pour le mobile)",
    )
    verrouille = models.BooleanField(
        default=False,
        help_text="Verrouillage après clôture comptable : la ligne ne peut plus être modifiée.",
    )
    date_verrouillage = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_depense", "-pk"]
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"

    def __str__(self):
        return f"{self.libelle} — {self.projet.nom}"

    def clean(self):
        super().clean()
        projet = (
            Projet.objects.filter(pk=self.projet_id).only("statut").first()
            if self.projet_id
            else None
        )
        if projet and projet.statut == Projet.STATUT_CLOTURE:
            raise ValidationError(
                "Impossible d'ajouter ou de modifier une dépense : le projet est clôturé."
            )
        if not self.pk:
            return
        ancienne = Depense.objects.filter(pk=self.pk).first()
        if not ancienne or not ancienne.verrouille:
            return
        champs = ("projet_id", "libelle", "montant", "date_depense", "description", "justificatif")
        if any(getattr(ancienne, ch) != getattr(self, ch) for ch in champs):
            raise ValidationError("Cette dépense est verrouillée : modification interdite.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        projet = (
            Projet.objects.filter(pk=self.projet_id).only("statut").first()
            if self.projet_id
            else None
        )
        if projet and projet.statut == Projet.STATUT_CLOTURE:
            raise ValidationError(
                "Impossible de supprimer cette dépense : le projet est clôturé."
            )
        if self.verrouille:
            raise ValidationError("Impossible de supprimer cette dépense : ligne verrouillée.")
        return super().delete(*args, **kwargs)


class Recette(models.Model):
    UNITE_KG = "kg"
    UNITE_TONNE = "tonne"
    UNITE_SAC = "sac"
    UNITE_CHOICES = [
        (UNITE_KG, "Kg"),
        (UNITE_TONNE, "Tonne"),
        (UNITE_SAC, "Sac"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='recettes')
    projet_produit = models.ForeignKey(
        ProjetProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recettes',
        help_text="Culture vendue lorsque la recette est liee a une ligne de projet.",
    )
    produit = models.CharField(max_length=150, blank=True)
    quantite = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unite = models.CharField(max_length=16, choices=UNITE_CHOICES, default=UNITE_KG)
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    montant_total = models.DecimalField(max_digits=18, decimal_places=2, editable=False)
    date_vente = models.DateField(default=now)
    justificatif_facture = CloudinaryField(
        "justificatif_facture",
        null=True,
        blank=True,
        resource_type="auto",
        folder=cloudinary_media_folder("finance/recettes"),
        help_text="Justificatif de vente (facture ou photo pesée)",
    )

    # Workflow Validation (V2)
    STATUT_EN_ATTENTE = 'en_attente'
    STATUT_VALIDEE = 'validee'
    STATUT_REFUSEE = 'refusee'
    STATUT_VALIDATION_CHOICES = [
        (STATUT_EN_ATTENTE, 'En attente de validation'),
        (STATUT_VALIDEE, 'Validée'),
        (STATUT_REFUSEE, 'Refusée'),
    ]

    statut_validation = models.CharField(
        max_length=15,
        choices=STATUT_VALIDATION_CHOICES,
        default=STATUT_EN_ATTENTE,
        help_text="Statut de validation par le manager de la ferme",
    )
    validee_par = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recettes_validees',
        help_text="Manager ayant validé la recette",
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de validation/refus",
    )
    commentaire_validation = models.TextField(
        blank=True,
        help_text="Commentaire du validateur (en cas de refus ou validation)",
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_vente', '-date_creation']
        indexes = [
            models.Index(fields=['projet', 'date_vente']),
            models.Index(fields=['projet_produit']),
            models.Index(fields=['statut_validation', '-date_creation']),
            models.Index(fields=['projet', 'statut_validation']),
        ]

    @property
    def est_validee(self):
        """Retourne True si la recette est validée."""
        return self.statut_validation == self.STATUT_VALIDEE

    @property
    def est_en_attente(self):
        """Retourne True si la recette est en attente de validation."""
        return self.statut_validation == self.STATUT_EN_ATTENTE

    @property
    def est_refusee(self):
        """Retourne True si la recette est refusée."""
        return self.statut_validation == self.STATUT_REFUSEE

    def valider(self, profile, commentaire=""):
        """Valide la recette (workflow manager)."""
        from django.utils import timezone
        self.statut_validation = self.STATUT_VALIDEE
        self.validee_par = profile
        self.date_validation = timezone.now()
        self.commentaire_validation = commentaire
        self.save(update_fields=['statut_validation', 'validee_par', 'date_validation', 'commentaire_validation'])

    def refuser(self, profile, commentaire=""):
        """Refuse la recette (workflow manager)."""
        from django.utils import timezone
        self.statut_validation = self.STATUT_REFUSEE
        self.validee_par = profile
        self.date_validation = timezone.now()
        self.commentaire_validation = commentaire
        self.save(update_fields=['statut_validation', 'validee_par', 'date_validation', 'commentaire_validation'])

    def clean(self):
        super().clean()
        if self.projet_produit_id and self.projet_id and self.projet_produit.projet_id != self.projet_id:
            raise ValidationError({"projet_produit": "Cette culture n'appartient pas au projet selectionne."})
        if not self.produit and self.projet_produit_id:
            self.produit = self.projet_produit.produit.nom

        projet = (
            Projet.objects.filter(pk=self.projet_id).only("statut").first()
            if self.projet_id
            else None
        )
        if projet and projet.statut == Projet.STATUT_CLOTURE:
            raise ValidationError(
                "Impossible d'ajouter ou de modifier une recette : le projet est clôturé."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.montant_total = (self.quantite or Decimal("0")) * (self.prix_unitaire or Decimal("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        produit = self.produit or (self.projet_produit.produit.nom if self.projet_produit_id else "Produit")
        return f"Recette {produit} - {self.montant_total} FCFA"

    def delete(self, *args, **kwargs):
        projet = (
            Projet.objects.filter(pk=self.projet_id).only("statut").first()
            if self.projet_id
            else None
        )
        if projet and projet.statut == Projet.STATUT_CLOTURE:
            raise ValidationError(
                "Impossible de supprimer cette recette : le projet est clôturé."
            )
        return super().delete(*args, **kwargs)


class PrevisionRecolte(models.Model):
    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name='previsions')
    projet_produit = models.OneToOneField(
        ProjetProduit,
        on_delete=models.CASCADE,
        related_name='prevision',
        null=True,
        blank=True,
    )
    rendement_estime_min = models.FloatField(default=0)
    rendement_estime_max = models.FloatField(default=0)
    indice_confiance = models.FloatField(null=True, blank=True, help_text="Indice de confiance du modèle IA (pourcentage)")
    date_recolte_prevue = models.DateField(null=True, blank=True)
    date_prediction = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prévision pour {self.projet.nom} ({self.indice_confiance or 0}%)"

    def clean(self):
        super().clean()
        if (
            self.date_recolte_prevue
            and self.projet_produit_id
            and self.projet_produit.date_semis
            and self.date_recolte_prevue <= self.projet_produit.date_semis
        ):
            raise ValidationError(
                {"date_recolte_prevue": "La date de récolte prévue doit être postérieure au semis."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PrevisionFeatures(models.Model):
    """
    Vecteur de features capturé au moment de chaque prédiction (P4).

    Permet l'export d'un dataset d'entraînement pour XGBoost/sklearn dès
    que suffisamment de projets clôturés ont été validés (rendement_reel non nul).

    Le champ `features` (JSON) contient toutes les variables agronomiques
    utilisées par estimer_rendement_ia() au moment du calcul :
    sol, eau, fertilisation, calendar, source des données, modificateurs, etc.

    Alimenté automatiquement par update_prediction_for_projet_produit().
    Validé à la clôture via le signal post_save(ProjetProduit) dès que
    rendement_final est renseigné.
    """

    prevision = models.OneToOneField(
        PrevisionRecolte,
        on_delete=models.CASCADE,
        related_name='features',
    )
    features = models.JSONField(
        default=dict,
        help_text="Vecteur de features au moment de la prédiction (dict JSON).",
    )
    rendement_reel = models.FloatField(
        null=True,
        blank=True,
        help_text="Rendement réel (kg) enregistré à la clôture du projet.",
    )
    erreur_pct = models.FloatField(
        null=True,
        blank=True,
        help_text="Erreur relative en % : (mid_predit - reel) / reel * 100.",
    )
    synthetique = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True si l'observation provient de données générées (seed). "
                  "EXCLUE de l'entraînement ML pour ne pas réapprendre le générateur.",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date à laquelle le rendement réel a été enregistré (label ML).",
    )

    class Meta:
        verbose_name = 'Features de prévision'
        verbose_name_plural = 'Features de prévisions'
        indexes = [
            models.Index(fields=['date_creation']),
            models.Index(fields=['rendement_reel']),
        ]


class MLModeleInfo(models.Model):
    """Historique des entraînements XGBoost par culture.

    Chaque ligne correspond à une session d'entraînement.
    Le champ ``actif`` désigne le modèle actuellement chargé en production
    pour cette culture. Un seul enregistrement ``actif=True`` par culture_slug.

    Permet de :
    - suivre l'évolution de R² et RMSE au fil du temps ;
    - décider si un nouveau modèle améliore le précédent avant de le déployer ;
    - tracer les déclencheurs (manuel, planifié, signal post-clôture).
    """

    DECLENCHEUR_CHOICES = [
        ('manuel', 'Manuel (commande)'),
        ('auto', 'Automatique (Beat hebdomadaire)'),
        ('signal', 'Signal (nouvelle clôture)'),
    ]

    culture_slug = models.CharField(max_length=100, db_index=True)
    culture_nom = models.CharField(max_length=100)
    date_entrainement = models.DateTimeField(auto_now_add=True)
    n_observations = models.IntegerField(help_text="Taille du dataset d'entraînement.")
    r2_score = models.FloatField(
        null=True, blank=True,
        help_text="R² moyen en cross-validation.",
    )
    rmse = models.FloatField(
        null=True, blank=True,
        help_text="RMSE moyen en cross-validation (kg/ha).",
    )
    actif = models.BooleanField(
        default=True,
        help_text="True si ce modèle est actuellement utilisé en production.",
    )
    declencheur = models.CharField(
        max_length=20,
        choices=DECLENCHEUR_CHOICES,
        default='manuel',
    )
    warm_start = models.BooleanField(
        default=False,
        help_text="True si entraîné en warm-start sur le modèle précédent.",
    )
    fichier_pkl = models.CharField(
        max_length=500,
        help_text="Chemin absolu vers le fichier .pkl du modèle.",
    )

    class Meta:
        verbose_name = 'Modèle ML'
        verbose_name_plural = 'Modèles ML'
        ordering = ['-date_entrainement']
        indexes = [
            models.Index(fields=['culture_slug', '-date_entrainement']),
            models.Index(fields=['actif']),
        ]

    def __str__(self):
        r2_str = f"R²={self.r2_score:.3f}" if self.r2_score is not None else "R²=N/D"
        actif_str = " [actif]" if self.actif else ""
        return f"{self.culture_nom} — {self.date_entrainement:%Y-%m-%d} ({r2_str}){actif_str}"

    @classmethod
    def derniere_date_entrainement(cls, culture_slug: str):
        """Date du dernier entraînement (actif ou non) pour cette culture."""
        obj = cls.objects.filter(culture_slug=culture_slug).order_by('-date_entrainement').first()
        return obj.date_entrainement if obj else None

    @classmethod
    def meilleur_r2(cls, culture_slug: str) -> float | None:
        """Meilleur R² connu pour cette culture (modèle actif)."""
        obj = cls.objects.filter(culture_slug=culture_slug, actif=True).order_by('-date_entrainement').first()
        return obj.r2_score if obj else None

    def __str__(self):
        return f"Features {self.prevision_id} (validé: {bool(self.rendement_reel)})"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sujet = models.CharField(max_length=200, blank=True)
    participants = models.ManyToManyField(
        Profile,
        related_name='conversations',
        through='ParticipationConversation',
    )
    dernier_message = models.DateTimeField(auto_now=True)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, null=True, blank=True, related_name='conversations')

    class Meta:
        ordering = ['-dernier_message']

    def __str__(self):
        p = list(self.participants.all())
        if self.sujet:
            return f"{self.sujet} ({len(p)} participants)"
        return f"Conversation entre {', '.join(str(x) for x in p[:3])}"


class ParticipationConversation(models.Model):
    """Through-model for Conversation.participants enabling per-user state
    (last_read_at, pinned, archived, muted) without altering the M2M API.

    All extra fields are nullable so existing `conversation.participants.add(...)`
    calls keep working without further changes.
    """
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='participations'
    )
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='participations'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    pinned_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    muted_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('profile', 'conversation')]
        indexes = [
            models.Index(fields=['profile', 'pinned_at']),
            models.Index(fields=['profile', 'archived_at']),
        ]

    def __str__(self):
        return f"{self.profile} <-> {self.conversation_id}"


def bump_participation_last_read(conversation_id, profile_id, watermark):
    """Met à jour `ParticipationConversation.last_read_at` (point de lecture conversation)."""
    if watermark is None:
        watermark = timezone.now()
    from django.db.models import F, Value
    from django.db.models.functions import Coalesce, Greatest

    # Single-query, monotonic bump: last_read_at = max(last_read_at, watermark)
    ParticipationConversation.objects.filter(
        conversation_id=conversation_id,
        profile_id=profile_id,
    ).update(
        last_read_at=Greatest(
            Coalesce(F("last_read_at"), Value(watermark)),
            Value(watermark),
        )
    )


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    expediteur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='messages_envoyes')
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    client_message_id = models.UUIDField(null=True, blank=True, db_index=True)
    lu_par = models.ManyToManyField(Profile, related_name='messages_lus', blank=True)
    piece_jointe = CloudinaryField(
        "piece_jointe",
        blank=True,
        null=True,
        resource_type="auto",
        folder=cloudinary_media_folder("messagerie/pieces_jointes"),
        help_text="Pièce jointe (photo optimisée ou document)",
    )
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reponses')

    class Meta:
        ordering = ['date_envoi']
        indexes = [
            models.Index(fields=['conversation', 'date_envoi']),
            models.Index(fields=['expediteur', 'date_envoi']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'expediteur', 'client_message_id'],
                condition=models.Q(client_message_id__isnull=False),
                name='uniq_message_client_id_per_sender_conversation',
            ),
        ]

    def __str__(self):
        return f"Message de {self.expediteur} — {self.date_envoi.strftime('%d/%m %H:%M')}"

    def is_lu_par_tous(self):
        """Returns True if all participants except sender have read the message."""
        participants_count = self.conversation.participants.exclude(id=self.expediteur_id).count()
        lu_count = self.lu_par.exclude(id=self.expediteur_id).count()
        return lu_count >= participants_count

    @property
    def lecture_statut(self):
        """État lecture côté expéditeur : envoye | recu_partiel | recu (Participation.last_read_at + lu_par)."""
        expediteur_id = self.expediteur_id
        recipients = [
            p for p in self.conversation.participations.all()
            if p.profile_id != expediteur_id
        ]
        if not recipients:
            return 'recu'
        lu_ids = set(self.lu_par.exclude(id=expediteur_id).values_list('pk', flat=True))
        read_flags = []
        for p in recipients:
            ts = p.last_read_at
            par_lu = ts is not None and ts >= self.date_envoi
            if not par_lu:
                par_lu = p.profile_id in lu_ids
            read_flags.append(par_lu)
        if all(read_flags):
            return 'recu'
        if any(read_flags):
            return 'recu_partiel'
        return 'envoye'

    @property
    def lecture_statut_label(self):
        st = self.lecture_statut
        if st == 'recu':
            return 'Reçu'
        if st == 'recu_partiel':
            return 'Reçu (partiel)'
        return 'Envoyé'


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    utilisateur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reactions_message')
    emoji = models.CharField(max_length=8)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['message', 'utilisateur', 'emoji']]
        indexes = [
            models.Index(fields=['message', 'emoji']),
        ]

    def __str__(self):
        return f"{self.utilisateur} reacted {self.emoji} to {self.message.id}"


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
        """Compat helper delegating to centralized permission policy."""
        from baay.permissions import role_dans_ferme as permission_role_dans_ferme
        return permission_role_dans_ferme(profile, ferme)

    @staticmethod
    def roles_assignables_par(role):
        """Compat helper delegating to centralized permission policy."""
        from baay.permissions import roles_assignables_par as permission_roles_assignables_par
        return permission_roles_assignables_par(role)

    def peut_etre_modifiee_par(self, profile):
        """Le créateur, le propriétaire de la ferme, ou l'assigné (statut/commentaire)."""
        if self.assigne_par_id == profile.id:
            return True
        if self.ferme.proprietaire_id == profile.id:
            return True
        return False

    def peut_changer_statut(self, profile):
        return self.assigne_a_id == profile.id or self.peut_etre_modifiee_par(profile)


class HistoriqueSol(models.Model):
    """
    Suivi historique de la santé des sols par ferme (Soil Ledger).

    Permet de suivre pH, NPK et cultures précédentes pour guider
    les recommandations de semis de la saison suivante.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(
        Ferme,
        on_delete=models.CASCADE,
        related_name="historiques_sol",
    )
    parcelle_nom = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nom libre de la parcelle ou zone (ex. 'Parcelle Nord', 'Champ A').",
    )
    date_mesure = models.DateField(help_text="Date du prélèvement / analyse de sol.")

    ph = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="pH du sol (0–14). Idéal cultures : 5.5–7.0.",
        validators=[MinValueValidator(0), MaxValueValidator(14)],
    )
    azote_ppm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Teneur en azote (N) en ppm.",
        validators=[MinValueValidator(0)],
    )
    phosphore_ppm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Teneur en phosphore (P) en ppm.",
        validators=[MinValueValidator(0)],
    )
    potassium_ppm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Teneur en potassium (K) en ppm.",
        validators=[MinValueValidator(0)],
    )
    culture_precedente = models.ForeignKey(
        ProduitAgricole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historiques_sol_precedents",
        help_text="Culture cultivée lors du cycle précédent (rotation).",
    )
    notes = models.TextField(blank=True, help_text="Observations agronomiques libres.")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique Sol"
        verbose_name_plural = "Historiques Sol"
        ordering = ["-date_mesure"]
        indexes = [
            models.Index(fields=["ferme", "-date_mesure"]),
        ]

    def __str__(self):
        parcelle = f" — {self.parcelle_nom}" if self.parcelle_nom else ""
        return f"{self.ferme.nom}{parcelle} ({self.date_mesure})"

    def analyser_et_recommander(self, culture_cible=None):
        """
        Génère une recommandation de fertilisation basée sur N-P-K et pH.
        Méthode Fat Model - appelle le service de fertilisation.
        """
        from baay.services.fertilisation_service import generer_recommandation
        return generer_recommandation(self, culture_cible)


class RecommandationFertilisation(models.Model):
    """
    Recommandation IA de fertilisation générée à partir d'un HistoriqueSol.
    Stocke le conseil persistant pour référence ultérieure.
    """
    TYPE_ENGRAIS_CHOICES = [
        ('organique', 'Organique (Compost, Fumier)'),
        ('mineral_npk', 'Minéral NPK'),
        ('mineral_uree', 'Minéral (Urée)'),
        ('mixte', 'Mixte (Organique + Minéral)'),
        ('aucun', 'Aucun - Sol équilibré'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    historique_sol = models.ForeignKey(
        HistoriqueSol,
        on_delete=models.CASCADE,
        related_name='recommandations',
    )
    culture_cible = models.ForeignKey(
        ProduitAgricole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommandations_fertilisation',
        help_text="Culture pour laquelle la recommandation est faite",
    )

    type_engrais_conseille = models.CharField(
        max_length=20,
        choices=TYPE_ENGRAIS_CHOICES,
        help_text="Type d'engrais recommandé",
    )
    quantite_kg_ha = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Quantité recommandée en kg par hectare",
    )
    message_explication = models.TextField(
        help_text="Explication détaillée de la recommandation (raisonnement IA)",
    )
    priorite_actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste d'actions prioritaires [{'action': '...', 'urgence': 'haute|moyenne|basse'}]",
    )
    confiance_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.75,
        help_text="Score de confiance de la recommandation (0.0 - 1.0)",
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    vue_par_utilisateur = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de consultation par l'utilisateur",
    )

    class Meta:
        verbose_name = "Recommandation Fertilisation"
        verbose_name_plural = "Recommandations Fertilisation"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["historique_sol", "-date_creation"]),
            models.Index(fields=["culture_cible", "-confiance_score"]),
        ]

    def __str__(self):
        culture = f" pour {self.culture_cible.nom}" if self.culture_cible else ""
        return f"Recommandation {self.type_engrais_conseille}{culture} ({self.historique_sol.ferme.nom})"


class IncidentRapporte(models.Model):
    """
    Incident agricole signalé via l'assistant vocal (hands-free).
    Capture transcription audio + géolocalisation pour traitement rapide.
    """
    TYPE_INCIDENT_CHOICES = [
        ('invasion_ravageurs', 'Invasion de ravageurs (criquets, chenilles...)'),
        ('maladie_feuilles', 'Maladie des feuilles'),
        ('maladie_racines', 'Maladie des racines/tiges'),
        ('stress_hydrique', 'Stress hydrique / Sécheresse'),
        ('inondation', 'Inondation / Excès d\'eau'),
        ('vol', 'Vol / Intrusion'),
        ('incident_materiel', 'Incident matériel / Dégâts'),
        ('autre', 'Autre incident'),
    ]

    GRAVITE_CHOICES = [
        ('faible', 'Faible - À surveiller'),
        ('moyenne', 'Moyenne - Action nécessaire'),
        ('haute', 'Haute - Urgent'),
        ('critique', 'Critique - Danger immédiat'),
    ]

    STATUT_CHOICES = [
        ('signale', 'Signalé - Non traité'),
        ('en_cours', 'Traitement en cours'),
        ('resolu', 'Résolu'),
        ('escalade', 'Escaladé au manager'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(
        Ferme,
        on_delete=models.CASCADE,
        related_name='incidents',
    )
    signale_par = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='incidents_signales',
        help_text="Utilisateur qui a signalé l'incident",
    )

    type_incident = models.CharField(
        max_length=30,
        choices=TYPE_INCIDENT_CHOICES,
        help_text="Catégorie de l'incident détectée",
    )
    gravite_detectee = models.CharField(
        max_length=10,
        choices=GRAVITE_CHOICES,
        default='moyenne',
        help_text="Gravité estimée par l'IA ou l'utilisateur",
    )
    statut = models.CharField(
        max_length=15,
        choices=STATUT_CHOICES,
        default='signale',
    )

    transcription_audio = models.TextField(
        help_text="Texte transcrit de l'audio de signalement",
    )
    audio_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL du fichier audio stocké (Cloudinary ou autre)",
    )
    localisation_gps_lat = models.FloatField(
        null=True,
        blank=True,
        help_text="Latitude GPS au moment du signalement",
    )
    localisation_gps_lon = models.FloatField(
        null=True,
        blank=True,
        help_text="Longitude GPS au moment du signalement",
    )
    parcelle_concernee = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nom de la parcelle si mentionnée",
    )

    traite_par = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents_traites',
        help_text="Responsable ayant pris en charge l'incident",
    )
    date_signalement = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    commentaire_resolution = models.TextField(blank=True)

    class Meta:
        verbose_name = "Incident Rapporté"
        verbose_name_plural = "Incidents Rapportés"
        ordering = ["-date_signalement"]
        indexes = [
            models.Index(fields=["ferme", "statut"]),
            models.Index(fields=["type_incident", "-date_signalement"]),
            models.Index(fields=["signale_par", "-date_signalement"]),
        ]

    def __str__(self):
        return f"{self.get_type_incident_display()} - {self.ferme.nom} ({self.get_gravite_detectee_display()})"


class DocumentConnaissance(models.Model):
    """
    Document de base de connaissances pour le RAG (Retrieval Augmented Generation).
    Stocke les textes d'expertise agronomique indexés pour requêtage LLM.
    """
    CATEGORIE_CHOICES = [
        ('culture', 'Culture / Semis / Récolte'),
        ('fertilisation', 'Fertilisation / Sol'),
        ('irrigation', 'Irrigation / Eau'),
        ('ravageurs', 'Ravageurs / Maladies'),
        ('climat', 'Climat / Météo'),
        ('economie', 'Économie / Marché'),
        ('pratiques', 'Pratiques paysannes'),
        ('reglementation', 'Réglementation / Certif'),
        ('autre', 'Autre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(max_length=200)
    contenu = models.TextField(help_text="Contenu textuel complet du document")
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='autre',
    )
    mots_cles = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste de mots-clés pour recherche",
    )
    source_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL source si document externe",
    )
    auteur = models.CharField(
        max_length=100,
        blank=True,
        help_text="Auteur ou organisation source",
    )

    embedding_status = models.CharField(
        max_length=15,
        choices=[('pending', 'En attente'), ('indexed', 'Indexé'), ('failed', 'Échec')],
        default='pending',
        help_text="Statut de l'indexation vectorielle",
    )
    date_indexation = models.DateTimeField(null=True, blank=True)

    is_actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document de Connaissance"
        verbose_name_plural = "Documents de Connaissance"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["categorie", "is_actif"]),
            models.Index(fields=["mots_cles"]),
        ]

    def __str__(self):
        return f"{self.titre} ({self.get_categorie_display()})"


class SimulationROI(models.Model):
    """
    Simulation de retour sur investissement (prévisionnel vs réel).
    Permet de modéliser différents scénarios de rendement et prix.
    """
    SCENARIO_TYPES = [
        ('optimiste', 'Optimiste'),
        ('realiste', 'Réaliste'),
        ('pessimiste', 'Pessimiste'),
        ('personnalise', 'Personnalisé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey(
        Projet,
        on_delete=models.CASCADE,
        related_name='simulations_roi',
        help_text="Projet concerné par la simulation",
    )
    projet_produit = models.ForeignKey(
        ProjetProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='simulations_roi',
        help_text="Culture spécifique (optionnel)",
    )

    # Type de scénario
    scenario_type = models.CharField(
        max_length=15,
        choices=SCENARIO_TYPES,
        default='realiste',
        help_text="Type de scénario simulé",
    )
    nom_simulation = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nom personnalisé (ex: 'Scenario prix haut')",
    )

    # Hypothèses simulation
    rendement_prevu_kg_ha = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Rendement prévisionnel (kg/hectare)",
    )
    prix_prevu_fcfa_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Prix prévisionnel (FCFA/kg)",
    )
    investissement_prevu = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Investissement prévisionnel total (FCFA)",
    )

    # Résultats calculés
    recette_prevue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        editable=False,
        help_text="Recette prévisionnelle calculée",
    )
    benefice_prevu = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        editable=False,
        help_text="Bénéfice net prévisionnel",
    )
    roi_calcule_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        editable=False,
        help_text="ROI prévisionnel en pourcentage",
    )

    # Comparaison avec réel (rempli automatiquement)
    recette_reelle = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Recette réalisée (pour comparaison)",
    )
    ecart_reel_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Écart réel vs prévision en %",
    )

    # Métadonnées
    description = models.TextField(
        blank=True,
        help_text="Notes et hypothèses de la simulation",
    )
    cree_par = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='simulations_roi_creees',
        help_text="Utilisateur ayant créé la simulation",
    )
    date_simulation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Simulation ROI"
        verbose_name_plural = "Simulations ROI"
        ordering = ["-date_simulation"]
        indexes = [
            models.Index(fields=["projet", "scenario_type"]),
            models.Index(fields=["cree_par", "-date_simulation"]),
        ]

    def __str__(self):
        scenario = self.nom_simulation or self.get_scenario_type_display()
        return f"Simulation {scenario} - {self.projet.nom} (ROI: {self.roi_calcule_pct}%)"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()

        # Calculs automatiques
        superficie = self.projet_produit.superficie_allouee if self.projet_produit else self.projet.superficie
        if superficie:
            self.recette_prevue = self.rendement_prevu_kg_ha * self.prix_prevu_fcfa_kg * superficie
        else:
            self.recette_prevue = self.rendement_prevu_kg_ha * self.prix_prevu_fcfa_kg

        self.benefice_prevu = self.recette_prevue - self.investissement_prevu

        if self.investissement_prevu > 0:
            self.roi_calcule_pct = (self.benefice_prevu / self.investissement_prevu) * 100
        else:
            self.roi_calcule_pct = 0

        # Comparaison avec réel si disponible
        if self.recette_reelle is not None and self.recette_prevue > 0:
            self.ecart_reel_pct = ((self.recette_reelle - self.recette_prevue) / self.recette_prevue) * 100

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OffreProduit(models.Model):
    """
    Offre de produit agricole sur le marketplace interne.
    Permet aux fermes de vendre leurs surplus de stock.
    """
    QUALITE_CHOICES = [
        ('A', 'Qualité A - Premium'),
        ('B', 'Qualité B - Standard'),
        ('C', 'Qualité C - Acceptable'),
    ]

    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('reserve', 'Réservé'),
        ('vendu', 'Vendu'),
        ('expire', 'Expiré'),
        ('annule', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendeur = models.ForeignKey(
        Ferme,
        on_delete=models.CASCADE,
        related_name='offres',
        help_text="Ferme vendeuse du produit",
    )
    produit = models.ForeignKey(
        ProduitAgricole,
        on_delete=models.CASCADE,
        related_name='offres_marketplace',
        help_text="Type de produit agricole",
    )

    titre_annonce = models.CharField(
        max_length=200,
        help_text="Titre de l'annonce (ex: 'Mil blanc de qualité premium')",
    )
    description = models.TextField(
        blank=True,
        help_text="Description détaillée du produit",
    )

    quantite_disponible = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Quantité disponible (kg)",
    )
    unite = models.CharField(
        max_length=10,
        choices=[('kg', 'Kilogramme'), ('tonne', 'Tonne'), ('sac', 'Sac (50kg)')],
        default='kg',
    )

    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Prix unitaire (FCFA)",
    )
    prix_negociable = models.BooleanField(
        default=True,
        help_text="Le prix est-il négociable ?",
    )

    qualite = models.CharField(
        max_length=1,
        choices=QUALITE_CHOICES,
        default='B',
        help_text="Qualité du produit",
    )
    date_recolte = models.DateField(
        null=True,
        blank=True,
        help_text="Date de récolte (pour fraîcheur)",
    )
    certification_bio = models.BooleanField(
        default=False,
        help_text="Produit certifié bio/organique",
    )

    localite_retrait = models.ForeignKey(
        Localite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offres_retrait',
        help_text="Localité de retrait/livraison",
    )
    livraison_possible = models.BooleanField(
        default=False,
        help_text="Livraison possible (à définir avec acheteur)",
    )
    frais_livraison = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Frais de livraison estimés (si applicable)",
    )

    statut = models.CharField(
        max_length=15,
        choices=STATUT_CHOICES,
        default='disponible',
    )
    date_expiration = models.DateField(
        help_text="Date d'expiration de l'offre",
    )

    photos = models.JSONField(
        default=list,
        blank=True,
        help_text="URLs des photos (Cloudinary)",
    )

    nb_vues = models.PositiveIntegerField(default=0)
    nb_contacts = models.PositiveIntegerField(default=0)

    cree_par = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='offres_creees',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Offre Produit"
        verbose_name_plural = "Offres Produits"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["produit", "statut", "-date_creation"]),
            models.Index(fields=["vendeur", "statut"]),
            models.Index(fields=["localite_retrait", "statut"]),
            models.Index(fields=["qualite", "prix_unitaire"]),
        ]

    def __str__(self):
        return f"{self.titre_annonce} - {self.vendeur.nom} ({self.quantite_disponible} {self.unite})"

    @property
    def prix_total(self):
        """Prix total pour la quantité disponible."""
        return self.quantite_disponible * self.prix_unitaire

    @property
    def est_disponible(self):
        """L'offre est-elle encore disponible ?"""
        from django.utils import timezone
        return (
            self.statut == 'disponible' and
            self.date_expiration >= timezone.now().date()
        )

    def reserver(self, acheteur, quantite):
        """Réserve une quantité pour un acheteur (crée une transaction)."""
        if not self.est_disponible:
            raise ValueError("Cette offre n'est plus disponible")
        if quantite > self.quantite_disponible:
            raise ValueError("Quantité demandée supérieure au stock disponible")

        transaction = TransactionMarche.objects.create(
            offre=self,
            acheteur=acheteur,
            quantite_achetee=quantite,
            prix_total=quantite * self.prix_unitaire,
            statut='en_negociation',
        )

        # Mettre à jour le statut si tout est réservé
        if quantite >= self.quantite_disponible:
            self.statut = 'reserve'
            self.save(update_fields=['statut'])

        return transaction


class TransactionMarche(models.Model):
    """
    Transaction entre vendeur et acheteur sur le marketplace.
    """
    STATUT_CHOICES = [
        ('en_negociation', 'En négociation'),
        ('confirme', 'Confirmé'),
        ('paye', 'Payé'),
        ('livre', 'Livré'),
        ('annule', 'Annulé'),
        ('litige', 'Litige'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offre = models.ForeignKey(
        OffreProduit,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    acheteur = models.ForeignKey(
        Ferme,
        on_delete=models.CASCADE,
        related_name='achats',
        help_text="Ferme acheteuse",
    )

    quantite_achetee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Quantité finalement achetée",
    )
    prix_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Prix total de la transaction",
    )
    prix_negocie_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix unitaire négocié (si différent de l'offre)",
    )

    statut = models.CharField(
        max_length=15,
        choices=STATUT_CHOICES,
        default='en_negociation',
    )

    # Détails de la transaction
    date_transaction = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

    mode_paiement = models.CharField(
        max_length=50,
        blank=True,
        help_text="Mode de paiement utilisé",
    )
    reference_paiement = models.CharField(
        max_length=100,
        blank=True,
        help_text="Référence de transaction (mobile money, virement...)",
    )

    lieu_retrait = models.TextField(
        blank=True,
        help_text="Adresse ou lieu de retrait convenu",
    )

    # Notes
    note_vendeur = models.TextField(blank=True, help_text="Note du vendeur sur l'acheteur")
    note_acheteur = models.TextField(blank=True, help_text="Note de l'acheteur sur le vendeur")
    rating_vendeur = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Évaluation vendeur (1-5)",
    )
    rating_acheteur = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Évaluation acheteur (1-5)",
    )

    cree_par = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='transactions_initiees',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transaction Marché"
        verbose_name_plural = "Transactions Marché"
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["offre", "statut"]),
            models.Index(fields=["acheteur", "-date_creation"]),
            models.Index(fields=["statut", "-date_creation"]),
        ]

    def __str__(self):
        return f"Transaction {self.offre.produit.nom} - {self.acheteur.nom} ({self.get_statut_display()})"


class NoteAgronomique(models.Model):
    """Note ou commentaire agronomique lié à un projet."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    projet = models.ForeignKey('Projet', on_delete=models.CASCADE, related_name='notes_agronomiques')
    auteur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notes_agronomiques')
    contenu = models.TextField(help_text="Contenu de la note ou du commentaire agronomique")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Note agronomique"
        verbose_name_plural = "Notes agronomiques"

    def __str__(self):
        return f"Note {self.auteur.user.username} sur {self.projet.nom} ({self.date_creation.strftime('%d/%m/%Y')})"


class StockIntrant(models.Model):
    """Stock d'intrants agricoles (engrais, semences, pesticides, etc.)."""
    CATEGORIE_ENGRAIS = 'engrais'
    CATEGORIE_SEMENCE = 'semence'
    CATEGORIE_PESTICIDE = 'pesticide'
    CATEGORIE_AUTRE = 'autre'
    CATEGORIE_CHOICES = [
        (CATEGORIE_ENGRAIS, 'Engrais'),
        (CATEGORIE_SEMENCE, 'Semence'),
        (CATEGORIE_PESTICIDE, 'Pesticide'),
        (CATEGORIE_AUTRE, 'Autre'),
    ]

    UNITE_KG = 'kg'
    UNITE_L = 'L'
    UNITE_SACS = 'sacs'
    UNITE_UNITES = 'unites'
    UNITE_CHOICES = [
        (UNITE_KG, 'Kilogrammes'),
        (UNITE_L, 'Litres'),
        (UNITE_SACS, 'Sacs'),
        (UNITE_UNITES, 'Unités'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='intrants')
    nom = models.CharField(max_length=100, help_text="Nom de l'intrant (ex: Urée, Semences de maïs)")
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES, default=CATEGORIE_AUTRE)
    quantite = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    unite = models.CharField(max_length=10, choices=UNITE_CHOICES, default=UNITE_KG)
    seuil_alerte = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('10.00'),
        help_text="Seuil en dessous duquel une alerte de stock bas est déclenchée"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Stock d'intrant"
        verbose_name_plural = "Stocks d'intrants"

    def __str__(self):
        return f"{self.nom} ({self.quantite} {self.get_unite_display()})"


class StockRecolte(models.Model):
    """Stock de récoltes (produits agricoles récoltés)."""
    UNITE_KG = 'kg'
    UNITE_TONNES = 'tonnes'
    UNITE_SACS = 'sacs'
    UNITE_CHOICES = [
        (UNITE_KG, 'Kilogrammes'),
        (UNITE_TONNES, 'Tonnes'),
        (UNITE_SACS, 'Sacs'),
    ]

    QUALITE_A = 'A'
    QUALITE_B = 'B'
    QUALITE_C = 'C'
    QUALITE_D = 'D'
    QUALITE_NC = 'NC'
    QUALITE_CHOICES = [
        (QUALITE_A, 'Grade A'),
        (QUALITE_B, 'Grade B'),
        (QUALITE_C, 'Grade C'),
        (QUALITE_D, 'Grade D'),
        (QUALITE_NC, 'Non classé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='recoltes')
    projet = models.ForeignKey('Projet', on_delete=models.SET_NULL, null=True, blank=True, related_name='recoltes')
    produit = models.ForeignKey('ProduitAgricole', on_delete=models.CASCADE, related_name='recoltes_stock')
    quantite = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    unite = models.CharField(max_length=10, choices=UNITE_CHOICES, default=UNITE_KG)
    date_recolte = models.DateField(help_text="Date de la récolte")
    qualite = models.CharField(max_length=2, choices=QUALITE_CHOICES, default=QUALITE_NC)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_recolte', '-date_creation']
        verbose_name = "Stock de récolte"
        verbose_name_plural = "Stocks de récoltes"

    def __str__(self):
        return f"{self.produit.nom} ({self.quantite} {self.get_unite_display()}) — {self.get_qualite_display()}"


class MouvementStock(models.Model):
    """Historique des entrées et sorties de stock."""
    TYPE_ENTREE = 'entree'
    TYPE_SORTIE = 'sortie'
    TYPE_CHOICES = [
        (TYPE_ENTREE, 'Entrée'),
        (TYPE_SORTIE, 'Sortie'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ferme = models.ForeignKey(Ferme, on_delete=models.CASCADE, related_name='mouvements_stock')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    stock_intrant = models.ForeignKey(StockIntrant, on_delete=models.CASCADE, null=True, blank=True, related_name='mouvements')
    stock_recolte = models.ForeignKey(StockRecolte, on_delete=models.CASCADE, null=True, blank=True, related_name='mouvements')
    quantite = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    date_mouvement = models.DateTimeField(auto_now_add=True)
    raison = models.CharField(max_length=255, blank=True, help_text="Raison du mouvement (ex: achat, utilisation, vente)")
    utilisateur = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements_stock')
    investissement = models.ForeignKey('Investissement', on_delete=models.SET_NULL, null=True, blank=True, related_name='mouvements_stock')

    class Meta:
        ordering = ['-date_mouvement']
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"

    def __str__(self):
        cible = self.stock_intrant or self.stock_recolte
        return f"{self.get_type_display()} — {cible} ({self.quantite}) — {self.date_mouvement.strftime('%d/%m/%Y %H:%M')}"


class Commentaire(models.Model):
    """Commentaire générique attaché à une Ferme, un Projet ou une Tâche.

    Remplace la messagerie WebSocket par un fil de discussion HTMX léger,
    accessible directement depuis les pages de détail des objets concernés.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")

    auteur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="commentaires")
    texte = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"

    def __str__(self):
        return f"{self.auteur} — {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class AppelAPILog(models.Model):
    """Journal des appels API (Gemini, HuggingFace, etc.) pour le monitoring des coûts."""
    SERVICE_GEMINI = "gemini"
    SERVICE_GALSENAI = "galsenai"
    SERVICE_CHOICES = [
        (SERVICE_GEMINI, "Gemini Vision"),
        (SERVICE_GALSENAI, "GalsenAI (HuggingFace)"),
    ]

    service = models.CharField(max_length=32, choices=SERVICE_CHOICES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    cout_estime_usd = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal("0"))
    cache_hit = models.BooleanField(default=False, db_index=True)
    modele = models.CharField(max_length=64, blank=True)
    duree_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Appel API"
        verbose_name_plural = "Appels API"
        indexes = [
            models.Index(fields=["service", "-timestamp"]),
            models.Index(fields=["timestamp", "cache_hit"]),
        ]

    def __str__(self):
        return f"{self.service} — {self.timestamp.strftime('%d/%m/%Y %H:%M')} — ${self.cout_estime_usd}"


# ─────────────────────────────────────────────────────────────────────────────
#  ArticleActualite — Agrégation de l'actualité agro-météo (ANACIM + MAE)
# ─────────────────────────────────────────────────────────────────────────────

class ArticleActualite(models.Model):
    """
    Article d'actualité agro-météo agrégé depuis des sources officielles.

    Sources supportées :
      - ANACIM (Agence Nationale de l'Aviation Civile et de la Météorologie)
      - MAE (Ministère de l'Agriculture et de l'Équipement Rural du Sénégal)
      - Autres sources agro (ANSD, FAO, etc.)

    Mis à jour toutes les 6h via la tâche Celery `fetch_actualites_task`.
    """

    SOURCE_ANACIM = "anacim"
    SOURCE_MAE    = "mae"
    SOURCE_ANSD   = "ansd"
    SOURCE_FAO    = "fao"
    SOURCE_AUTRE  = "autre"

    SOURCE_CHOICES = [
        (SOURCE_ANACIM, "ANACIM — Météo & Agroclimat"),
        (SOURCE_MAE,    "Ministère de l'Agriculture"),
        (SOURCE_ANSD,   "ANSD — Statistiques"),
        (SOURCE_FAO,    "FAO Sénégal"),
        (SOURCE_AUTRE,  "Autre source"),
    ]

    CATEGORIE_METEO    = "meteo"
    CATEGORIE_CONSEIL  = "conseil"
    CATEGORIE_POLITIQUE = "politique"
    CATEGORIE_MARCHE   = "marche"
    CATEGORIE_AUTRE    = "autre"

    CATEGORIE_CHOICES = [
        (CATEGORIE_METEO,     "Météo & Agroclimat"),
        (CATEGORIE_CONSEIL,   "Conseils agricoles"),
        (CATEGORIE_POLITIQUE, "Politique agricole"),
        (CATEGORIE_MARCHE,    "Marchés & prix"),
        (CATEGORIE_AUTRE,     "Autre"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source          = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_AUTRE, db_index=True)
    categorie       = models.CharField(max_length=20, choices=CATEGORIE_CHOICES, default=CATEGORIE_AUTRE, db_index=True)
    titre           = models.CharField(max_length=500)
    resume          = models.TextField(blank=True)
    contenu         = models.TextField(blank=True)
    url_originale   = models.URLField(max_length=2000, unique=True)
    image_url       = models.URLField(max_length=2000, blank=True)
    date_publication = models.DateTimeField(null=True, blank=True, db_index=True)
    date_collecte   = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    actif           = models.BooleanField(default=True, db_index=True,
                                          help_text="False = masqué de la liste publique (spam, erreur).")

    class Meta:
        ordering = ["-date_publication", "-date_collecte"]
        verbose_name = "Article actualité"
        verbose_name_plural = "Articles actualités"
        indexes = [
            models.Index(fields=["source", "-date_publication"]),
            models.Index(fields=["categorie", "-date_publication"]),
            models.Index(fields=["actif", "-date_publication"]),
        ]

    def __str__(self):
        return f"[{self.get_source_display()}] {self.titre[:80]}"

    @property
    def source_label(self) -> str:
        return self.get_source_display()

    @property
    def categorie_label(self) -> str:
        return self.get_categorie_display()


# ──────────────────────────────────────────────────────────────────────────────
# Prix marché & alertes
# ──────────────────────────────────────────────────────────────────────────────

class PrixMarche(models.Model):
    """
    Prix observé d'un produit agricole sur un marché à une date donnée.

    Collecté automatiquement via :
      - FAO FPMA API (primaire, sans clé, données SEN)
      - Scraping OMA Sénégal (fallback)

    Idempotence : unique_together (produit_nom, marche_nom, date_relevee, source).
    """

    SOURCE_FAO_FPMA = "fao_fpma"
    SOURCE_OMA      = "oma"
    SOURCE_RESIMAO  = "resimao"
    SOURCE_AUTRE    = "autre"

    SOURCE_CHOICES = [
        (SOURCE_FAO_FPMA, "FAO FPMA (Global Food Prices)"),
        (SOURCE_OMA,      "OMA Sénégal"),
        (SOURCE_RESIMAO,  "RESIMAO (Afrique de l'Ouest)"),
        (SOURCE_AUTRE,    "Autre source"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    produit_nom   = models.CharField(
        max_length=100, db_index=True,
        help_text="Nom normalisé du produit (mil, sorgho, maïs, arachide…).",
    )
    marche_nom    = models.CharField(
        max_length=150, db_index=True,
        help_text="Nom du marché (Kaolack, Dakar-Sandaga, Ziguinchor…).",
    )
    region        = models.CharField(max_length=100, blank=True, db_index=True)
    pays          = models.CharField(max_length=50, default="Sénégal")
    prix_unitaire = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Prix en FCFA par unité (généralement kg ou sac 50 kg).",
    )
    unite         = models.CharField(
        max_length=30, default="FCFA/kg",
        help_text="Unité du prix : FCFA/kg, FCFA/sac50kg, etc.",
    )
    qualite       = models.CharField(
        max_length=50, blank=True,
        help_text="Qualité ou type : local, importé, gros, détail…",
    )
    source        = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_AUTRE, db_index=True,
    )
    source_id     = models.CharField(
        max_length=200, blank=True,
        help_text="Identifiant externe utilisé pour l'idempotence (ex: FAO FPMA point ID).",
    )
    date_relevee  = models.DateField(db_index=True, help_text="Date d'observation du prix.")
    date_collecte = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_relevee", "produit_nom"]
        verbose_name = "Prix marché"
        verbose_name_plural = "Prix marchés"
        unique_together = [("produit_nom", "marche_nom", "date_relevee", "source")]
        indexes = [
            models.Index(fields=["produit_nom", "-date_relevee"]),
            models.Index(fields=["marche_nom", "-date_relevee"]),
            models.Index(fields=["region", "-date_relevee"]),
            models.Index(fields=["source", "-date_relevee"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.produit_nom} — {self.marche_nom} "
            f"({self.prix_unitaire} {self.unite}, {self.date_relevee})"
        )

    @property
    def source_label(self) -> str:
        return self.get_source_display()


class AlertePrix(models.Model):
    """
    Variation significative de prix détectée automatiquement par comparaison
    entre le dernier prix relevé et le prix N jours avant.

    Niveaux :
      - info     : variation < seuil warning (informatif)
      - warning  : ≥ 15 % sur 7 j  / ≥ 20 % sur 30 j
      - critique : ≥ 30 % sur 7 j  / ≥ 40 % sur 30 j

    Idempotence : unique_together (produit_nom, marche_nom, periode_jours, date_detection).
    """

    NIVEAU_INFO     = "info"
    NIVEAU_WARNING  = "warning"
    NIVEAU_CRITIQUE = "critique"

    NIVEAU_CHOICES = [
        (NIVEAU_INFO,     "ℹ️ Informatif"),
        (NIVEAU_WARNING,  "⚠️ Variation importante"),
        (NIVEAU_CRITIQUE, "🔴 Variation critique"),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    produit_nom     = models.CharField(max_length=100, db_index=True)
    marche_nom      = models.CharField(max_length=150)
    region          = models.CharField(max_length=100, blank=True)
    variation_pct   = models.FloatField(
        help_text="Variation en % (positif = hausse, négatif = baisse).",
    )
    prix_actuel     = models.DecimalField(max_digits=12, decimal_places=2)
    prix_reference  = models.DecimalField(max_digits=12, decimal_places=2)
    unite           = models.CharField(max_length=30, default="FCFA/kg")
    periode_jours   = models.IntegerField(
        default=7, help_text="Fenêtre de comparaison : 7 ou 30 jours.",
    )
    niveau          = models.CharField(
        max_length=20, choices=NIVEAU_CHOICES, default=NIVEAU_WARNING, db_index=True,
    )
    date_detection  = models.DateTimeField(auto_now_add=True, db_index=True)
    vue             = models.BooleanField(
        default=False, db_index=True,
        help_text="True = l'alerte a été vue dans le dashboard.",
    )

    class Meta:
        ordering = ["-date_detection"]
        verbose_name = "Alerte prix"
        verbose_name_plural = "Alertes prix"
        unique_together = [("produit_nom", "marche_nom", "periode_jours", "date_detection")]
        indexes = [
            models.Index(fields=["niveau", "-date_detection"]),
            models.Index(fields=["vue", "-date_detection"]),
            models.Index(fields=["produit_nom", "-date_detection"]),
        ]

    def __str__(self) -> str:
        sens = "↑" if self.variation_pct > 0 else "↓"
        return (
            f"{self.produit_nom} {sens}{abs(self.variation_pct):.1f}% "
            f"— {self.marche_nom} ({self.periode_jours}j) [{self.niveau}]"
        )

    @property
    def est_hausse(self) -> bool:
        return self.variation_pct > 0

    @property
    def icone(self) -> str:
        if self.niveau == self.NIVEAU_CRITIQUE:
            return "🔴"
        if self.niveau == self.NIVEAU_WARNING:
            return "⚠️"
        return "ℹ️"

    @property
    def variation_abs(self) -> float:
        return abs(self.variation_pct)
