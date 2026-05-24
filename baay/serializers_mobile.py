# baay/serializers_mobile.py
# ── Sérialiseurs DRF pour l'application mobile Andd Baayi ──────────────────
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    Ferme,
    Localite,
    PrevisionRecolte,
    ProduitAgricole,
    Profile,
    Projet,
    ProjetProduit,
    Region,
)


# ── Utilitaire Cloudinary → URL ────────────────────────────────────────────
def _cloudinary_url(field_value) -> str | None:
    if not field_value:
        return None
    try:
        return field_value.url
    except Exception:
        return None


# ── Auth ───────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ["id", "user", "phone_number", "address"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirm password")
    phone_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "password2", "phone_number"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password2": "Les mots de passe ne correspondent pas."})
        if User.objects.filter(email=data.get("email", "")).exists():
            raise serializers.ValidationError({"email": "Cet email est déjà utilisé."})
        return data

    def create(self, validated_data):
        phone = validated_data.pop("phone_number", "")
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        profile = user.profile  # créé par signal post_save
        if phone:
            profile.phone_number = phone
            profile.save(update_fields=["phone_number"])
        return user


# ── Géographie ─────────────────────────────────────────────────────────────

class LocaliteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localite
        fields = ["id", "nom", "type_sol", "pluviometrie_moyenne", "latitude", "longitude"]


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "nom"]


# ── Produits agricoles ──────────────────────────────────────────────────────

class ProduitAgricoleSerializer(serializers.ModelSerializer):
    photo_principale = serializers.SerializerMethodField()

    class Meta:
        model = ProduitAgricole
        fields = [
            "id", "nom", "description", "saison", "prix_par_kg",
            "periode_recolte", "duree_avant_recolte", "rendement_moyen",
            "cycle_culture_jours", "besoin_eau_mm", "rendement_potentiel_max",
            "photo_principale",
        ]

    def get_photo_principale(self, obj):
        first = obj.photos.first()
        if first:
            return _cloudinary_url(first.image)
        return None


# ── Prévision récolte ───────────────────────────────────────────────────────

class PrevisionRecolteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrevisionRecolte
        fields = [
            "rendement_estime_min",
            "rendement_estime_max",
            "indice_confiance",
            "date_recolte_prevue",
            "date_prediction",
        ]


# ── ProjetProduit ───────────────────────────────────────────────────────────

class ProjetProduitSerializer(serializers.ModelSerializer):
    produit = ProduitAgricoleSerializer(read_only=True)
    produit_id = serializers.PrimaryKeyRelatedField(
        queryset=ProduitAgricole.objects.all(), source="produit", write_only=True
    )
    prevision = PrevisionRecolteSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    etat_vegetatif_label = serializers.SerializerMethodField()

    class Meta:
        model = ProjetProduit
        fields = [
            "id", "produit", "produit_id",
            "quantite_semences", "superficie_allouee",
            "date_semis", "date_recolte_prevue",
            "etat_vegetatif", "etat_vegetatif_label",
            "rendement_final", "date_recolte_effective",
            "notes", "image_url", "prevision",
            "date_creation", "date_modification",
        ]
        read_only_fields = ["id", "date_creation", "date_modification"]

    def get_image_url(self, obj):
        return _cloudinary_url(obj.image)

    def get_etat_vegetatif_label(self, obj):
        if obj.etat_vegetatif is None:
            return None
        return dict(obj.ETAT_VEGETATIF_CHOICES).get(obj.etat_vegetatif)


class ProjetProduitEtatSerializer(serializers.Serializer):
    """Sérialiseur léger pour la mise à jour de l'état végétatif."""
    etat_vegetatif = serializers.IntegerField(min_value=1, max_value=5, allow_null=True)


# ── Projet ──────────────────────────────────────────────────────────────────

class ProjetListSerializer(serializers.ModelSerializer):
    """Version légère pour la liste des projets."""
    localite_nom = serializers.CharField(source="localite.nom", read_only=True)
    taux_avancement = serializers.IntegerField(read_only=True)
    nb_produits = serializers.SerializerMethodField()
    image_fond_url = serializers.SerializerMethodField()

    class Meta:
        model = Projet
        fields = [
            "id", "nom", "statut", "type_cycle",
            "superficie", "date_lancement", "date_fin",
            "localite_nom", "taux_avancement", "nb_produits",
            "image_fond_url",
        ]

    def get_nb_produits(self, obj):
        return obj.projet_produits.count()

    def get_image_fond_url(self, obj):
        return _cloudinary_url(obj.image_fond)


class ProjetDetailSerializer(serializers.ModelSerializer):
    """Version complète avec produits et prévisions."""
    localite = LocaliteSerializer(read_only=True)
    projet_produits = ProjetProduitSerializer(many=True, read_only=True)
    avancement = serializers.SerializerMethodField()
    image_fond_url = serializers.SerializerMethodField()

    class Meta:
        model = Projet
        fields = [
            "id", "nom", "statut", "type_cycle",
            "superficie", "date_lancement", "date_fin",
            "type_irrigation", "type_engrais",
            "budget_alloue", "rendement_total_final",
            "localite", "projet_produits",
            "avancement", "image_fond_url",
        ]

    def get_avancement(self, obj):
        return obj.avancement_pour_api()

    def get_image_fond_url(self, obj):
        return _cloudinary_url(obj.image_fond)


class ProjetCreateSerializer(serializers.ModelSerializer):
    localite_id = serializers.PrimaryKeyRelatedField(
        queryset=Localite.objects.all(), source="localite"
    )

    class Meta:
        model = Projet
        fields = [
            "nom", "localite_id", "superficie",
            "date_lancement", "date_fin",
            "type_cycle", "type_irrigation", "type_engrais",
            "budget_alloue",
        ]

    def validate(self, data):
        # Validation minimale — le modèle (full_clean) fera le reste.
        if data.get("date_fin") and data.get("date_lancement"):
            if data["date_fin"] <= data["date_lancement"]:
                raise serializers.ValidationError(
                    {"date_fin": "La date de fin doit être postérieure au lancement."}
                )
        return data


# ── Ferme ───────────────────────────────────────────────────────────────────

class FermeListSerializer(serializers.ModelSerializer):
    localite_nom = serializers.CharField(source="localite.nom", read_only=True, default=None)
    nb_projets = serializers.SerializerMethodField()
    image_couverture_url = serializers.SerializerMethodField()

    class Meta:
        model = Ferme
        fields = [
            "id", "nom", "description", "superficie_totale",
            "latitude", "longitude", "localite_nom",
            "subscription_tier", "is_premium",
            "nb_projets", "image_couverture_url",
            "date_creation",
        ]

    def get_nb_projets(self, obj):
        return obj.projets.count()

    def get_image_couverture_url(self, obj):
        return _cloudinary_url(obj.image_couverture)


class FermeDetailSerializer(serializers.ModelSerializer):
    localite = LocaliteSerializer(read_only=True)
    projets = ProjetListSerializer(many=True, read_only=True)
    image_couverture_url = serializers.SerializerMethodField()
    nb_membres = serializers.SerializerMethodField()

    class Meta:
        model = Ferme
        fields = [
            "id", "nom", "description",
            "superficie_totale", "latitude", "longitude",
            "localite", "subscription_tier", "is_premium",
            "code_acces", "projets",
            "image_couverture_url", "nb_membres",
            "date_creation",
        ]

    def get_image_couverture_url(self, obj):
        return _cloudinary_url(obj.image_couverture)

    def get_nb_membres(self, obj):
        return obj.membres.count()


class FermeCreateSerializer(serializers.ModelSerializer):
    localite_id = serializers.PrimaryKeyRelatedField(
        queryset=Localite.objects.all(), source="localite", required=False, allow_null=True
    )

    class Meta:
        model = Ferme
        fields = ["nom", "description", "superficie_totale", "localite_id", "latitude", "longitude"]
