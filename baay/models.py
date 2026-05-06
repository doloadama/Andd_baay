from django.contrib.auth.models import AbstractUser, User
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
    photo_profil = CloudinaryField(
        "photo_profil",
        null=True,
        blank=True,
        folder=cloudinary_media_folder("profils"),
        help_text="Photo du collaborateur (membre de la ferme)",
    )

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
            if (date_fin - date_lancement).days > 730:
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
        """
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
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_vente', '-date_creation']
        indexes = [
            models.Index(fields=['projet', 'date_vente']),
            models.Index(fields=['projet_produit']),
        ]

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

