# baay/views_api_mobile.py
# ── Vues REST pour l'application mobile Andd Baayi ─────────────────────────
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Ferme, Localite, ProduitAgricole, Profile, Projet, ProjetProduit, Region
from .serializers_mobile import (
    FermeCreateSerializer,
    FermeDetailSerializer,
    FermeListSerializer,
    LocaliteSerializer,
    ProfileSerializer,
    ProjetCreateSerializer,
    ProjetDetailSerializer,
    ProjetListSerializer,
    ProjetProduitEtatSerializer,
    ProjetProduitSerializer,
    ProduitAgricoleSerializer,
    RegionSerializer,
    RegisterSerializer,
)
from .core_services import update_prediction_for_projet_produit


# ── helpers ────────────────────────────────────────────────────────────────

def _profile(request) -> Profile:
    return request.user.profile


def _ferme_du_user(ferme_id, request) -> Ferme:
    """Retourne la ferme si elle appartient à l'utilisateur, sinon 404."""
    return get_object_or_404(
        Ferme, id=ferme_id, proprietaire=_profile(request)
    )


def _projet_du_user(projet_id, request) -> Projet:
    """Retourne le projet si l'utilisateur en est le titulaire."""
    return get_object_or_404(
        Projet, id=projet_id, utilisateur=_profile(request)
    )


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

class RegisterView(APIView):
    """POST /api/mobile/auth/register/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user: User = serializer.save()

        # Génère une paire de tokens JWT directement
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/mobile/auth/me/"""
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return _profile(self.request)

    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        # Champs user modifiables depuis le profil
        user_fields = {k: v for k, v in request.data.items() if k in ("first_name", "last_name", "email")}
        if user_fields:
            for field, value in user_fields.items():
                setattr(profile.user, field, value)
            profile.user.save(update_fields=list(user_fields.keys()))
        # Champs profil
        profile_fields = {k: v for k, v in request.data.items() if k in ("phone_number", "address")}
        if profile_fields:
            for field, value in profile_fields.items():
                setattr(profile, field, value)
            profile.save(update_fields=list(profile_fields.keys()))
        return Response(ProfileSerializer(profile).data)


# ══════════════════════════════════════════════════════════════════════════════
# GÉOGRAPHIE
# ══════════════════════════════════════════════════════════════════════════════

class LocaliteListView(generics.ListAPIView):
    """GET /api/mobile/localites/?region=<id>&search=<q>"""
    serializer_class = LocaliteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Localite.objects.select_related("region").all()
        region_id = self.request.query_params.get("region")
        if region_id:
            qs = qs.filter(region_id=region_id)
        q = self.request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(nom__icontains=q)
        return qs.order_by("nom")[:100]


class RegionListView(generics.ListAPIView):
    """GET /api/mobile/regions/?pays=<id>"""
    serializer_class = RegionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Region.objects.select_related("pays").all()
        pays_id = self.request.query_params.get("pays")
        if pays_id:
            qs = qs.filter(pays_id=pays_id)
        return qs.order_by("nom")


# ══════════════════════════════════════════════════════════════════════════════
# CATALOGUE PRODUITS
# ══════════════════════════════════════════════════════════════════════════════

class ProduitListView(generics.ListAPIView):
    """GET /api/mobile/produits/?search=<q>"""
    serializer_class = ProduitAgricoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ProduitAgricole.objects.prefetch_related("photos")
        q = self.request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(nom__icontains=q)
        return qs.order_by("nom")


# ══════════════════════════════════════════════════════════════════════════════
# FERMES
# ══════════════════════════════════════════════════════════════════════════════

class FermeListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/mobile/fermes/     → liste des fermes de l'utilisateur
    POST /api/mobile/fermes/     → créer une ferme
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FermeCreateSerializer
        return FermeListSerializer

    def get_queryset(self):
        return (
            Ferme.objects
            .filter(proprietaire=_profile(self.request))
            .select_related("localite")
            .prefetch_related("projets")
            .order_by("-date_creation")
        )

    def perform_create(self, serializer):
        serializer.save(proprietaire=_profile(self.request))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            ferme = serializer.save(proprietaire=_profile(request))
        out = FermeDetailSerializer(ferme, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class FermeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/mobile/fermes/<id>/
    PATCH  /api/mobile/fermes/<id>/
    DELETE /api/mobile/fermes/<id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return FermeCreateSerializer
        return FermeDetailSerializer

    def get_object(self):
        return (
            Ferme.objects
            .select_related("localite")
            .prefetch_related("projets__localite", "projets__projet_produits__produit", "membres")
            .get(id=self.kwargs["ferme_id"], proprietaire=_profile(self.request))
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            ferme = self.get_object()
        except Ferme.DoesNotExist:
            return Response({"detail": "Ferme introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(FermeDetailSerializer(ferme).data)


# ══════════════════════════════════════════════════════════════════════════════
# PROJETS
# ══════════════════════════════════════════════════════════════════════════════

class ProjetListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/mobile/fermes/<ferme_id>/projets/
    POST /api/mobile/fermes/<ferme_id>/projets/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProjetCreateSerializer
        return ProjetListSerializer

    def get_queryset(self):
        ferme = _ferme_du_user(self.kwargs["ferme_id"], self.request)
        qs = (
            Projet.objects
            .filter(ferme=ferme)
            .select_related("localite")
            .prefetch_related("projet_produits")
            .order_by("-date_lancement")
        )
        statut = self.request.query_params.get("statut")
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def create(self, request, *args, **kwargs):
        ferme = _ferme_du_user(self.kwargs["ferme_id"], request)
        serializer = ProjetCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            projet = serializer.save(
                ferme=ferme,
                utilisateur=_profile(request),
            )
        out = ProjetDetailSerializer(projet)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProjetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/mobile/projets/<projet_id>/
    PATCH  /api/mobile/projets/<projet_id>/
    DELETE /api/mobile/projets/<projet_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProjetCreateSerializer
        return ProjetDetailSerializer

    def get_object(self):
        return (
            Projet.objects
            .select_related("localite")
            .prefetch_related(
                "projet_produits__produit__photos",
                "projet_produits__prevision",
            )
            .get(id=self.kwargs["projet_id"], utilisateur=_profile(self.request))
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            return Response(ProjetDetailSerializer(self.get_object()).data)
        except Projet.DoesNotExist:
            return Response({"detail": "Projet introuvable."}, status=status.HTTP_404_NOT_FOUND)


# ── Statut rapide d'un projet ───────────────────────────────────────────────

@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def projet_statut_view(request, projet_id):
    """PATCH /api/mobile/projets/<id>/statut/  body: {"statut": "en_pause"}"""
    projet = _projet_du_user(projet_id, request)
    nouveau = request.data.get("statut")
    choix_valides = [c[0] for c in Projet.STATUT_CHOICES]
    if nouveau not in choix_valides:
        return Response(
            {"statut": f"Valeur invalide. Choix : {choix_valides}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    projet.statut = nouveau
    try:
        projet.save(update_fields=["statut"])
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"statut": projet.statut})


# ── Avancement personnalisé ─────────────────────────────────────────────────

@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def projet_avancement_view(request, projet_id):
    """PATCH /api/mobile/projets/<id>/avancement/  body: {"taux": 65}"""
    projet = _projet_du_user(projet_id, request)
    taux = request.data.get("taux")
    if taux is None:
        return Response({"taux": "Champ requis."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        taux = int(taux)
        assert 0 <= taux <= 100
    except (ValueError, AssertionError):
        return Response({"taux": "Entier entre 0 et 100 requis."}, status=status.HTTP_400_BAD_REQUEST)
    projet.taux_avancement_personnalise = taux
    projet.save(update_fields=["taux_avancement_personnalise"])
    return Response({"taux_avancement": taux})


# ══════════════════════════════════════════════════════════════════════════════
# PRODUITS DU PROJET
# ══════════════════════════════════════════════════════════════════════════════

class ProjetProduitListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/mobile/projets/<projet_id>/produits/
    POST /api/mobile/projets/<projet_id>/produits/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjetProduitSerializer

    def get_queryset(self):
        projet = _projet_du_user(self.kwargs["projet_id"], self.request)
        return (
            ProjetProduit.objects
            .filter(projet=projet)
            .select_related("produit")
            .prefetch_related("produit__photos", "prevision")
        )

    def create(self, request, *args, **kwargs):
        projet = _projet_du_user(self.kwargs["projet_id"], request)
        serializer = ProjetProduitSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            pp = serializer.save(projet=projet)
        # Déclenche la prédiction de rendement IA
        try:
            update_prediction_for_projet_produit(pp)
        except Exception:
            pass
        out = ProjetProduitSerializer(pp)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProjetProduitDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/mobile/projet-produits/<id>/
    PATCH  /api/mobile/projet-produits/<id>/
    DELETE /api/mobile/projet-produits/<id>/
    """
    serializer_class = ProjetProduitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            ProjetProduit.objects.select_related("produit").prefetch_related("produit__photos", "prevision"),
            id=self.kwargs["pp_id"],
            projet__utilisateur=_profile(self.request),
        )

    def update(self, request, *args, **kwargs):
        pp = self.get_object()
        serializer = ProjetProduitSerializer(pp, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            pp = serializer.save()
        # Recalcule la prédiction si les données de semis/surface changent
        recalc_fields = {"superficie_allouee", "date_semis", "etat_vegetatif", "rendement_final"}
        if recalc_fields & set(request.data.keys()):
            try:
                update_prediction_for_projet_produit(pp)
            except Exception:
                pass
        return Response(ProjetProduitSerializer(pp).data)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def projet_produit_etat_view(request, pp_id):
    """PATCH /api/mobile/projet-produits/<id>/etat/  body: {"etat_vegetatif": 4}"""
    pp = get_object_or_404(
        ProjetProduit,
        id=pp_id,
        projet__utilisateur=_profile(request),
    )
    serializer = ProjetProduitEtatSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    pp.etat_vegetatif = serializer.validated_data["etat_vegetatif"]
    pp.save(update_fields=["etat_vegetatif", "date_modification"])

    try:
        update_prediction_for_projet_produit(pp)
    except Exception:
        pass

    labels = dict(pp.ETAT_VEGETATIF_CHOICES)
    prevision_data = None
    if hasattr(pp, "prevision"):
        from .serializers_mobile import PrevisionRecolteSerializer
        prevision_data = PrevisionRecolteSerializer(pp.prevision).data

    return Response({
        "etat_vegetatif": pp.etat_vegetatif,
        "etat_vegetatif_label": labels.get(pp.etat_vegetatif),
        "prevision": prevision_data,
    })


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD RAPIDE
# ══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def mobile_dashboard_view(request):
    """GET /api/mobile/dashboard/  — KPIs personnels condensés."""
    profile = _profile(request)
    fermes = Ferme.objects.filter(proprietaire=profile)
    projets = Projet.objects.filter(utilisateur=profile)

    nb_fermes = fermes.count()
    nb_projets_actifs = projets.filter(statut__in=["en_cours", "en_pause"]).count()
    nb_projets_termines = projets.filter(statut__in=["fini", "cloture"]).count()

    # Derniers projets actifs (max 5) pour widget accueil
    derniers = (
        projets
        .filter(statut="en_cours")
        .select_related("localite")
        .prefetch_related("projet_produits__produit")
        .order_by("-date_lancement")[:5]
    )

    return Response({
        "nb_fermes": nb_fermes,
        "nb_projets_actifs": nb_projets_actifs,
        "nb_projets_termines": nb_projets_termines,
        "projets_recents": ProjetListSerializer(derniers, many=True).data,
    })
