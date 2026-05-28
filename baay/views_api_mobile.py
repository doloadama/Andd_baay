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

import uuid as _uuid

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

from .models import Commentaire, Ferme, Localite, PrevisionRecolte, ProduitAgricole, Profile, Projet, ProjetProduit, Region, Tache
from .serializers_mobile import (
    CommentaireCreateSerializer,
    CommentaireSerializer,
    FermeCreateSerializer,
    FermeDetailSerializer,
    FermeListSerializer,
    LocaliteSerializer,
    PrevisionRecolteSerializer,
    ProfileSerializer,
    ProjetCreateSerializer,
    ProjetDetailSerializer,
    ProjetListSerializer,
    ProjetProduitEtatSerializer,
    ProjetProduitSerializer,
    ProduitAgricoleSerializer,
    RegionSerializer,
    RegisterSerializer,
    TacheCreateSerializer,
    TacheListSerializer,
    TacheStatutSerializer,
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


# ══════════════════════════════════════════════════════════════════════════════
# TÂCHES
# ══════════════════════════════════════════════════════════════════════════════

class TacheListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/taches/?ferme=<uuid>&projet=<uuid>
    POST /api/v1/taches/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TacheCreateSerializer
        return TacheListSerializer

    def get_queryset(self):
        profile = _profile(self.request)
        qs = Tache.objects.filter(ferme__proprietaire=profile).select_related(
            "assigne_a__user", "assigne_par__user", "ferme", "projet"
        )
        ferme_id = self.request.query_params.get("ferme")
        projet_id = self.request.query_params.get("projet")
        if ferme_id:
            qs = qs.filter(ferme_id=ferme_id)
        if projet_id:
            qs = qs.filter(projet_id=projet_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(assigne_par=_profile(self.request))


class TacheUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/v1/taches/<uuid>/statut/
    """
    serializer_class = TacheStatutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile = _profile(self.request)
        return Tache.objects.filter(ferme__proprietaire=profile) | Tache.objects.filter(assigne_a=profile)

    def update(self, request, *args, **kwargs):
        tache = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tache.statut = serializer.validated_data["statut"]
        if "commentaire_retour" in serializer.validated_data:
            tache.commentaire_retour = serializer.validated_data["commentaire_retour"]
        tache.save(update_fields=["statut", "commentaire_retour", "date_modification"])
        return Response(TacheListSerializer(tache).data)


# ══════════════════════════════════════════════════════════════════════════════
# COMMENTAIRES (GenericForeignKey)
# ══════════════════════════════════════════════════════════════════════════════

_CT_LABEL_MAP = {
    "ferme": "ferme",
    "tache": "tache",
    "projet": "projet",
}


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def commentaires_api(request, ct_label: str, object_id):
    """GET  /api/v1/commentaires/<ct_label>/<uuid>/
    POST /api/v1/commentaires/<ct_label>/<uuid>/"""
    ct_model = _CT_LABEL_MAP.get(ct_label.lower())
    if ct_model is None:
        return Response(
            {"detail": f"Type non supporté : {ct_label}. Valeurs acceptées : ferme, tache, projet."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        ct = ContentType.objects.get(app_label="baay", model=ct_model)
    except ContentType.DoesNotExist:
        return Response({"detail": "Type de contenu introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        commentaires = Commentaire.objects.filter(
            content_type=ct, object_id=object_id
        ).select_related("auteur__user")
        return Response(CommentaireSerializer(commentaires, many=True).data)

    # POST
    serializer = CommentaireCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    commentaire = Commentaire.objects.create(
        content_type=ct,
        object_id=object_id,
        auteur=_profile(request),
        texte=serializer.validated_data["texte"],
    )
    return Response(CommentaireSerializer(commentaire).data, status=status.HTTP_201_CREATED)


# ══════════════════════════════════════════════════════════════════════════════
# PRÉVISIONS RÉCOLTE
# ══════════════════════════════════════════════════════════════════════════════

class PrevisionRecolteListView(generics.ListAPIView):
    """GET /api/v1/previsions/?projet=<uuid>"""
    serializer_class = PrevisionRecolteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile = _profile(self.request)
        qs = PrevisionRecolte.objects.filter(projet__ferme__proprietaire=profile)
        projet_id = self.request.query_params.get("projet")
        if projet_id:
            qs = qs.filter(projet_id=projet_id)
        return qs


# ══════════════════════════════════════════════════════════════════════════════
# PROFIL UTILISATEUR (endpoint v1)
# ══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def profile_api(request):
    """GET /api/v1/profile/"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return Response({"detail": "Profil introuvable."}, status=status.HTTP_404_NOT_FOUND)
    return Response(ProfileSerializer(profile).data)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC ASYNC (API REST)
# ══════════════════════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def diagnostic_submit_api(request):
    """POST /api/v1/diagnostic/
    Soumet une image pour analyse phytosanitaire asynchrone.
    Retourne : {"task_id": "<uuid>"}
    """
    from baay.views_diagnostic import (
        ALLOWED_MIME,
        MAX_FILE_SIZE,
        _check_rate_limit,
        _client_ip,
        _CULTURES_MAP,
    )

    photo = request.FILES.get("photo")
    if not photo:
        return Response({"detail": "Le champ 'photo' est requis."}, status=status.HTTP_400_BAD_REQUEST)
    if photo.size > MAX_FILE_SIZE:
        return Response({"detail": "Fichier trop volumineux (max 10 Mo)."}, status=status.HTTP_400_BAD_REQUEST)
    if photo.content_type not in ALLOWED_MIME:
        return Response(
            {"detail": "Format non supporté. Utilisez JPEG, PNG ou WebP."},
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    if not _check_rate_limit(_client_ip(request)):
        return Response(
            {"detail": "Trop d'analyses récentes. Réessayez dans quelques minutes."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    culture_key = request.data.get("culture", "autre")
    culture_label = _CULTURES_MAP.get(culture_key, culture_key)
    langue = request.data.get("langue", "fr")
    if langue not in ("fr", "wo"):
        langue = "fr"

    image_bytes = photo.read()
    task_id = str(_uuid.uuid4())
    task_cache_key = f"task:{task_id}"
    cache.set(task_cache_key, {"status": "pending"}, 3600)

    from baay.tasks.diagnostic import analyze_plant_pest_task
    analyze_plant_pest_task.delay(
        image_bytes.hex(),
        photo.content_type,
        culture_label,
        langue,
        task_cache_key,
    )
    return Response({"task_id": task_id}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def diagnostic_result_api(request, task_id: str):
    """GET /api/v1/diagnostic/<task_id>/
    Retourne le résultat d'une analyse (polling par task_id).
    Statuts : pending | done | error | expired
    """
    task_cache_key = f"task:{task_id}"
    task_data = cache.get(task_cache_key)

    if task_data is None:
        return Response(
            {"status": "expired", "detail": "Résultat expiré ou introuvable."},
            status=status.HTTP_410_GONE,
        )
    if task_data["status"] == "pending":
        return Response({"status": "pending"})
    elif task_data["status"] == "done":
        return Response({"status": "done", "result": task_data["result"]})
    else:
        return Response({"status": "error", "error": task_data.get("error", "Erreur inconnue.")})


# ── Actualités agro-météo ──────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def actualites_api(request):
    """GET /api/mobile/actualites/
    Retourne les articles d'actualité agro-météo (ANACIM, MAE, FAO…).

    Query params :
      source    — filtre par source (anacim | mae | fao | ansd | autre)
      categorie — filtre par catégorie (meteo | conseil | politique | marche | autre)
      page      — page (défaut 1)
      page_size — taille de page (défaut 20, max 50)
    """
    from .models import ArticleActualite

    source    = request.query_params.get("source", "").strip()
    categorie = request.query_params.get("categorie", "").strip()
    try:
        page      = max(1, int(request.query_params.get("page", 1)))
        page_size = min(50, max(1, int(request.query_params.get("page_size", 20))))
    except (ValueError, TypeError):
        page, page_size = 1, 20

    qs = ArticleActualite.objects.filter(actif=True)
    if source and source in dict(ArticleActualite.SOURCE_CHOICES):
        qs = qs.filter(source=source)
    if categorie and categorie in dict(ArticleActualite.CATEGORIE_CHOICES):
        qs = qs.filter(categorie=categorie)

    total  = qs.count()
    offset = (page - 1) * page_size
    articles = qs[offset: offset + page_size]

    results = [
        {
            "id":               str(a.id),
            "source":           a.source,
            "source_label":     a.get_source_display(),
            "categorie":        a.categorie,
            "categorie_label":  a.get_categorie_display(),
            "titre":            a.titre,
            "resume":           a.resume,
            "url":              a.url_originale,
            "image_url":        a.image_url,
            "date_publication": a.date_publication.isoformat() if a.date_publication else None,
            "date_collecte":    a.date_collecte.isoformat(),
        }
        for a in articles
    ]

    return Response({
        "count":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     -(-total // page_size),   # ceil division
        "results":   results,
    })


# ── Prix marchés ──────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def prix_marche_api(request):
    """
    GET /api/mobile/prix/
    Retourne les relevés de prix agricoles (paginé).

    Filtres :
      produit  — nom du produit (recherche partielle)
      region   — région (recherche partielle)
      marche   — nom du marché (recherche partielle)
      periode  — nombre de jours d'historique (7, 30, 90 ; défaut 30)
      page     — numéro de page (défaut 1)
      page_size — taille de page (max 50 ; défaut 20)

    Réponse :
      {count, page, page_size, pages, results: [{id, produit_nom, marche_nom,
       region, prix_unitaire, unite, source, date_relevee, date_collecte}]}
    """
    from baay.models import PrixMarche
    from datetime import date, timedelta

    produit = request.query_params.get("produit", "").strip()
    region  = request.query_params.get("region", "").strip()
    marche  = request.query_params.get("marche", "").strip()
    try:
        periode = int(request.query_params.get("periode", 30))
        periode = max(7, min(90, periode))
    except (ValueError, TypeError):
        periode = 30

    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(50, max(1, int(request.query_params.get("page_size", 20))))
    except (ValueError, TypeError):
        page_size = 20

    date_debut = date.today() - timedelta(days=periode)
    qs = PrixMarche.objects.filter(date_relevee__gte=date_debut)

    if produit:
        qs = qs.filter(produit_nom__icontains=produit)
    if region:
        qs = qs.filter(region__icontains=region)
    if marche:
        qs = qs.filter(marche_nom__icontains=marche)

    qs = qs.order_by("-date_relevee", "produit_nom")
    total  = qs.count()
    offset = (page - 1) * page_size
    items  = qs[offset: offset + page_size]

    results = [
        {
            "id":           str(p.id),
            "produit_nom":  p.produit_nom,
            "marche_nom":   p.marche_nom,
            "region":       p.region,
            "pays":         p.pays,
            "prix_unitaire": float(p.prix_unitaire),
            "unite":        p.unite,
            "qualite":      p.qualite,
            "source":       p.source,
            "source_label": p.get_source_display(),
            "date_relevee": str(p.date_relevee),
            "date_collecte": p.date_collecte.isoformat(),
        }
        for p in items
    ]

    return Response({
        "count":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     -(-total // page_size),
        "periode_jours": periode,
        "results":   results,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def alertes_prix_api(request):
    """
    GET /api/mobile/prix/alertes/
    Retourne les alertes de variation de prix actives.

    Filtres :
      niveau    — info | warning | critique
      produit   — filtrer par produit
      jours     — fenêtre max en jours depuis la détection (défaut 30)
      page      — numéro de page
      page_size — taille de page (max 50 ; défaut 20)

    Réponse :
      {count, page, page_size, pages, results: [{id, produit_nom, marche_nom,
       variation_pct, variation_sens, prix_actuel, prix_reference, unite,
       periode_jours, niveau, icone, date_detection}]}
    """
    from baay.models import AlertePrix
    from django.utils.timezone import now
    from datetime import timedelta

    niveau_filtre  = request.query_params.get("niveau", "").strip()
    produit_filtre = request.query_params.get("produit", "").strip()
    try:
        jours = min(90, max(1, int(request.query_params.get("jours", 30))))
    except (ValueError, TypeError):
        jours = 30
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(50, max(1, int(request.query_params.get("page_size", 20))))
    except (ValueError, TypeError):
        page_size = 20

    qs = AlertePrix.objects.filter(date_detection__gte=now() - timedelta(days=jours))

    if niveau_filtre in (AlertePrix.NIVEAU_INFO, AlertePrix.NIVEAU_WARNING, AlertePrix.NIVEAU_CRITIQUE):
        qs = qs.filter(niveau=niveau_filtre)
    else:
        # Par défaut : warning + critique uniquement
        qs = qs.filter(niveau__in=[AlertePrix.NIVEAU_WARNING, AlertePrix.NIVEAU_CRITIQUE])

    if produit_filtre:
        qs = qs.filter(produit_nom__icontains=produit_filtre)

    qs = qs.order_by("-date_detection")
    total  = qs.count()
    offset = (page - 1) * page_size
    items  = qs[offset: offset + page_size]

    results = [
        {
            "id":             str(a.id),
            "produit_nom":    a.produit_nom,
            "marche_nom":     a.marche_nom,
            "region":         a.region,
            "variation_pct":  a.variation_pct,
            "variation_sens": "hausse" if a.variation_pct > 0 else "baisse",
            "variation_abs":  abs(a.variation_pct),
            "prix_actuel":    float(a.prix_actuel),
            "prix_reference": float(a.prix_reference),
            "unite":          a.unite,
            "periode_jours":  a.periode_jours,
            "niveau":         a.niveau,
            "niveau_label":   a.get_niveau_display(),
            "icone":          a.icone,
            "vue":            a.vue,
            "date_detection": a.date_detection.isoformat(),
        }
        for a in items
    ]

    return Response({
        "count":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     -(-total // page_size),
        "results":   results,
    })
