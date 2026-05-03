from django.contrib.auth.models import AbstractUser, User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from decimal import Decimal
import uuid
import secrets
import string

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    last_login = models.DateTimeField(auto_now=True)
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
        ('proprietaire', 'Propriétaire'),
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
    date_fin = models.DateField(null=True, blank=True, help_text="Date de fin prévue/réelle du projet")
    rendement_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_alloue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget prévisionnel total du projet (FCFA). Utilisé pour les alertes de dépassement.",
    )
    
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
            if self.statut != 'fini' and date_fin < timezone.localdate():
                raise ValidationError({"date_fin": "La date de fin ne peut pas être dans le passé pour un projet actif."})
            # Durée raisonnable ≤ 2 ans
            if (date_fin - date_lancement).days > 730:
                raise ValidationError({"date_fin": "La durée d'un projet ne doit pas excéder 2 ans."})
        else:
            # Projet en cours: ne pas démarrer dans un futur lointain (> 2 ans)
            today = timezone.localdate()
            if date_lancement > (today + _td(days=730)):
                raise ValidationError({"date_lancement": "La date de début ne peut pas dépasser 2 ans dans le futur."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def rendement_total_final(self):
        """Calcule le rendement final total de tous les produits du projet"""
        total = self.projet_produits.aggregate(total=models.Sum('rendement_final'))['total']
        return total or 0

    @property
    def taux_avancement(self):
        """Progression 0-100 prete pour les jauges du dashboard mobile."""
        if self.statut == 'fini':
            return 100

        taches = list(self.taches.exclude(statut='annulee').values_list('statut', flat=True))
        if taches:
            score_taches = sum(
                100 if statut == 'terminee' else 50 if statut == 'en_cours' else 0
                for statut in taches
            ) / len(taches)
        else:
            score_taches = 0

        lignes_culture = list(
            self.projet_produits.values('date_semis', 'date_recolte_prevue', 'date_recolte_effective')
        )
        if lignes_culture:
            etapes_scores = []
            for ligne in lignes_culture:
                score = 0
                if ligne['date_semis']:
                    score += 35
                if ligne['date_semis'] and not ligne['date_recolte_effective']:
                    score += 25
                if ligne['date_recolte_prevue']:
                    score += 15
                if ligne['date_recolte_effective']:
                    score = 100
                etapes_scores.append(score)
            score_etapes = sum(etapes_scores) / len(etapes_scores)
        else:
            score_etapes = 0

        progression = (score_taches * Decimal("0.45")) + (Decimal(str(score_etapes)) * Decimal("0.55"))
        if self.statut == 'en_pause':
            progression = min(progression, Decimal("75"))
        return int(max(0, min(100, round(progression))))


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

        projet = self.projet
        if projet is None and self.projet_id:
            projet = Projet.objects.filter(pk=self.projet_id).first()

        date_semis = _d(self.date_semis)
        date_recolte_prevue = _d(self.date_recolte_prevue)
        date_recolte_effective = _d(self.date_recolte_effective)

        if projet:
            debut = _d(projet.date_lancement)
            fin = _d(projet.date_fin)
            if date_semis and debut:
                if date_semis < debut:
                    raise ValidationError(
                        {
                            "date_semis": "La date de semis doit être postérieure ou égale à la date de début du projet "
                            "(date de lancement), et comprise dans la plage du projet."
                        }
                    )
                if fin and date_semis > fin:
                    raise ValidationError(
                        {
                            "date_semis": "La date de semis doit être antérieure ou égale à la date de fin du projet, "
                            "et comprise entre la date de début et la date de fin du projet."
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
        )
        if any(getattr(ancien, champ) != getattr(self, champ) for champ in champs_financiers):
            raise ValidationError("Cette depense est verrouillee car le projet est cloture.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.verrouille:
            raise ValidationError("Cette depense est verrouillee car le projet est cloture.")
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
    produit_vendu = models.CharField(max_length=150, blank=True)
    quantite_vendue = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unite = models.CharField(max_length=16, choices=UNITE_CHOICES, default=UNITE_KG)
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    montant_total = models.DecimalField(max_digits=18, decimal_places=2, editable=False)
    date_encaissement = models.DateField(default=now)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_encaissement', '-date_creation']
        indexes = [
            models.Index(fields=['projet', 'date_encaissement']),
            models.Index(fields=['projet_produit']),
        ]

    def clean(self):
        super().clean()
        if self.projet_produit_id and self.projet_id and self.projet_produit.projet_id != self.projet_id:
            raise ValidationError({"projet_produit": "Cette culture n'appartient pas au projet selectionne."})
        if not self.produit_vendu and self.projet_produit_id:
            self.produit_vendu = self.projet_produit.produit.nom

    def save(self, *args, **kwargs):
        self.full_clean()
        self.montant_total = (self.quantite_vendue or Decimal("0")) * (self.prix_unitaire or Decimal("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        produit = self.produit_vendu or (self.projet_produit.produit.nom if self.projet_produit_id else "Produit")
        return f"Recette {produit} - {self.montant_total} FCFA"

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
    row = ParticipationConversation.objects.filter(
        conversation_id=conversation_id,
        profile_id=profile_id,
    ).first()
    if row is None:
        return
    cur = row.last_read_at
    if cur is None or watermark > cur:
        row.last_read_at = watermark
        row.save(update_fields=['last_read_at'])


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    expediteur = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='messages_envoyes')
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    client_message_id = models.UUIDField(null=True, blank=True, db_index=True)
    lu_par = models.ManyToManyField(Profile, related_name='messages_lus', blank=True)
    piece_jointe = models.FileField(upload_to='messages/%Y/%m/', blank=True, null=True)
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

