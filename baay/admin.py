from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import Truncator
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from baay.dashboard_services import DashboardChangelistMixin

from .models import (
    AlertePrix,
    AppelAPILog,
    ArticleActualite,
    PrixMarche,
    Conversation,
    CampagneProjet,
    Cooperative,
    MembreCooperative,
    DemandeAccesFerme,
    Depense,
    Ferme,
    HistoriqueSol,
    Investissement,
    Localite,
    Message,
    MessageReaction,
    MouvementStock,
    Pays,
    PhotoProduitAgricole,
    PrevisionRecolte,
    ProduitAgricole,
    Profile,
    Projet,
    ProjetProduit,
    Recette,
    Region,
    StockIntrant,
    StockRecolte,
    Tache,
)


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    """Interface utilisateurs Django compatibles Unfold."""


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    """Interface groupes compatibles Unfold."""


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ("nom", "pays", "code")
    list_filter = (("pays", AutocompleteSelectFilter),)
    search_fields = ("nom", "code", "pays__nom")
    ordering = ("pays__nom", "nom")


@admin.register(Pays)
class PaysAdmin(ModelAdmin):
    list_display = ("nom", "code_iso")
    search_fields = ("nom", "code_iso")
    ordering = ("nom",)
    list_per_page = 50


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ("user", "phone_number", "onboarding_completed")
    search_fields = ("user__username", "user__email", "phone_number")
    ordering = ("user__username",)
    list_filter_submit = True


class HistoriqueSolInline(admin.TabularInline):
    model = HistoriqueSol
    extra = 0
    fields = ("date_mesure", "parcelle_nom", "ph", "azote_ppm", "phosphore_ppm", "potassium_ppm", "culture_precedente", "notes")
    show_change_link = True
    ordering = ("-date_mesure",)


@admin.register(Ferme)
class FermeAdmin(DashboardChangelistMixin, ModelAdmin):
    list_before_template = "admin/baay/changelist_dashboard_note.html"
    baay_dashboard_slug = "ferme"
    # Colonnes réduites : pays / localité restent filtrables sans encombrer la grille
    list_display = ("nom", "proprietaire", "code_acces", "date_creation")
    list_filter = [
        ("pays", AutocompleteSelectFilter),
        ("region", AutocompleteSelectFilter),
        ("localite", AutocompleteSelectFilter),
    ]
    search_fields = ("nom", "code_acces", "proprietaire__user__username")
    ordering = ("-date_creation",)
    list_select_related = ("proprietaire__user", "pays", "region", "localite")
    list_filter_submit = True
    inlines = [HistoriqueSolInline]


@admin.register(ProduitAgricole)
class ProduitAgricoleAdmin(ModelAdmin):
    list_display = ("nom", "etat", "prix_par_kg")
    search_fields = ("nom", "saison")
    list_filter = [
        ("etat", ChoicesDropdownFilter),
    ]
    ordering = ("nom",)
    list_per_page = 25
    list_filter_submit = True


@admin.register(PhotoProduitAgricole)
class PhotoProduitAgricoleAdmin(ModelAdmin):
    @admin.display(description="Description")
    def description_courte(self, obj):
        return Truncator(obj.description or "").chars(48)

    list_display = ("produit", "description_courte", "date_ajout")
    search_fields = ("produit__nom",)
    ordering = ("-date_ajout",)
    list_per_page = 25
    list_select_related = ("produit",)


@admin.register(Projet)
class ProjetAdmin(DashboardChangelistMixin, ModelAdmin):
    list_before_template = "admin/baay/changelist_dashboard_note.html"
    baay_dashboard_slug = "projet"
    list_display = ("nom", "ferme", "type_cycle", "statut", "budget_alloue", "date_lancement")
    list_filter = [
        ("type_cycle", ChoicesDropdownFilter),
        ("statut", ChoicesDropdownFilter),
        ("ferme", AutocompleteSelectFilter),
        ("pays", AutocompleteSelectFilter),
        ("localite", AutocompleteSelectFilter),
        ("culture", AutocompleteSelectFilter),
    ]
    search_fields = ("nom", "ferme__nom")
    ordering = ("-date_lancement",)
    list_select_related = ("ferme", "culture", "localite", "pays", "utilisateur__user")
    list_filter_submit = True


@admin.register(CampagneProjet)
class CampagneProjetAdmin(ModelAdmin):
    list_display = ("nom", "projet", "saison", "statut", "date_debut", "date_fin", "rendement_total")
    list_filter = [
        ("statut", ChoicesDropdownFilter),
        ("projet", AutocompleteSelectFilter),
    ]
    search_fields = ("nom", "saison", "projet__nom")
    ordering = ("-date_debut",)
    list_select_related = ("projet", "projet__ferme")
    list_filter_submit = True


@admin.register(Localite)
class LocaliteAdmin(ModelAdmin):
    list_display = ("nom", "pays", "region", "type_sol")
    list_filter = [
        ("pays", AutocompleteSelectFilter),
        ("region", AutocompleteSelectFilter),
        ("type_sol", ChoicesDropdownFilter),
    ]
    search_fields = ("nom",)
    ordering = ("nom",)
    list_filter_submit = True


@admin.register(Investissement)
class InvestissementAdmin(DashboardChangelistMixin, ModelAdmin):
    list_before_template = "admin/baay/changelist_dashboard_note.html"
    baay_dashboard_slug = "investissement"
    list_display = (
        "projet",
        "libelle",
        "categorie",
        "projet_produit",
        "cout_par_hectare",
        "autres_frais",
        "verrouille",
        "date_investissement",
    )
    list_filter = [
        ("date_investissement", RangeDateFilter),
        ("projet", AutocompleteSelectFilter),
    ]
    search_fields = ("projet__nom", "libelle", "description", "projet_produit__produit__nom")
    ordering = ("-date_investissement",)
    list_select_related = ("projet", "projet__ferme", "projet_produit", "projet_produit__produit")
    list_filter_submit = True


@admin.register(Depense)
class DepenseAdmin(DashboardChangelistMixin, ModelAdmin):
    list_display = ("projet", "libelle", "montant", "date_depense")
    list_filter = [
        ("projet", AutocompleteSelectFilter),
        ("date_depense", RangeDateFilter),
    ]
    search_fields = ("libelle", "description", "projet__nom")
    ordering = ("-date_depense",)
    list_select_related = ("projet", "projet__ferme")
    list_filter_submit = True


@admin.register(Recette)
class RecetteAdmin(DashboardChangelistMixin, ModelAdmin):
    list_before_template = "admin/baay/changelist_dashboard_note.html"
    baay_dashboard_slug = "recette"
    readonly_fields = ("montant_total", "date_creation", "date_modification")
    list_display = (
        "projet",
        "produit",
        "quantite",
        "unite",
        "prix_unitaire",
        "montant_total",
        "date_vente",
    )
    list_filter = [
        ("projet", AutocompleteSelectFilter),
        ("date_vente", RangeDateFilter),
    ]
    search_fields = ("projet__nom", "produit", "projet_produit__produit__nom")
    ordering = ("-date_vente",)
    list_select_related = ("projet", "projet_produit", "projet_produit__produit")
    list_filter_submit = True


@admin.register(DemandeAccesFerme)
class DemandeAccesFermeAdmin(ModelAdmin):
    list_display = ("utilisateur", "ferme", "statut", "date_demande")
    list_filter = [
        ("ferme", AutocompleteSelectFilter),
        ("utilisateur", AutocompleteSelectFilter),
        ("statut", ChoicesDropdownFilter),
        ("date_demande", RangeDateTimeFilter),
    ]
    search_fields = ("code", "utilisateur__user__username", "ferme__nom")
    ordering = ("-date_demande",)
    list_select_related = ("ferme", "utilisateur__user")
    list_filter_submit = True


@admin.register(ProjetProduit)
class ProjetProduitAdmin(ModelAdmin):
    readonly_fields = ("date_creation", "date_modification")
    list_display = ("produit", "projet", "superficie_allouee", "budget_alloue")
    list_filter = [
        ("produit", AutocompleteSelectFilter),
        ("projet", AutocompleteSelectFilter),
        ("projet__ferme", AutocompleteSelectFilter),
    ]
    search_fields = ("produit__nom", "projet__nom")
    ordering = ("-date_creation",)
    list_select_related = ("produit", "projet", "projet__ferme")
    list_filter_submit = True


@admin.register(PrevisionRecolte)
class PrevisionRecolteAdmin(DashboardChangelistMixin, ModelAdmin):
    list_before_template = "admin/baay/changelist_dashboard_note.html"
    baay_dashboard_slug = "previsionrecolte"

    @admin.display(description="Rendement (min – max)")
    def rendement_fourchette(self, obj):
        return f"{obj.rendement_estime_min} – {obj.rendement_estime_max}"

    list_display = (
        "projet",
        "projet_produit",
        "rendement_fourchette",
        "indice_confiance",
        "date_recolte_prevue",
    )
    list_filter = [
        ("projet", AutocompleteSelectFilter),
        ("date_prediction", RangeDateTimeFilter),
    ]
    search_fields = ("projet__nom", "projet_produit__produit__nom")
    ordering = ("-date_prediction",)
    list_select_related = ("projet", "projet_produit", "projet_produit__produit")
    list_filter_submit = True


@admin.register(Conversation)
class ConversationAdmin(ModelAdmin):
    list_display = ("sujet", "ferme", "dernier_message")
    list_filter = [
        ("ferme", AutocompleteSelectFilter),
    ]
    search_fields = ("sujet",)
    ordering = ("-dernier_message",)
    list_select_related = ("ferme",)
    list_filter_submit = True


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    @admin.display(description="Aperçu")
    def contenu_apercu(self, obj):
        return Truncator(obj.contenu or "").chars(56)

    list_display = ("conversation", "expediteur", "date_envoi", "contenu_apercu")
    list_filter = [
        ("conversation", AutocompleteSelectFilter),
        ("expediteur", AutocompleteSelectFilter),
        ("date_envoi", RangeDateTimeFilter),
    ]
    search_fields = ("contenu", "expediteur__user__username")
    ordering = ("-date_envoi",)
    list_select_related = ("conversation", "expediteur__user")
    list_filter_submit = True


@admin.register(MessageReaction)
class MessageReactionAdmin(ModelAdmin):
    @admin.display(description="Message")
    def message_ref(self, obj):
        return Truncator(str(obj.message)).chars(40)

    list_display = ("message_ref", "utilisateur", "emoji", "date_ajout")
    search_fields = ("emoji", "utilisateur__user__username")
    ordering = ("-date_ajout",)
    list_select_related = ("message", "utilisateur__user")
    list_filter_submit = True


@admin.register(Tache)
class TacheAdmin(DashboardChangelistMixin, ModelAdmin):
    list_before_template = "admin/baay/changelist_dashboard_note.html"
    baay_dashboard_slug = "tache"
    # ferme / projet / priorité : filtres latéraux ; liste centrée sur exécution
    list_display = ("titre", "assigne_a", "statut", "date_echeance")
    list_filter = [
        ("statut", ChoicesDropdownFilter),
        ("priorite", ChoicesDropdownFilter),
        ("ferme", AutocompleteSelectFilter),
        ("projet", AutocompleteSelectFilter),
    ]
    search_fields = ("titre", "description", "assigne_a__user__username")
    ordering = ("-date_creation",)
    list_select_related = ("ferme", "projet", "assigne_a__user", "assigne_par__user")
    list_filter_submit = True


@admin.register(HistoriqueSol)
class HistoriqueSolAdmin(ModelAdmin):
    list_display = ("ferme", "parcelle_nom", "date_mesure", "ph", "azote_ppm", "phosphore_ppm", "potassium_ppm", "culture_precedente")
    list_filter = [
        ("ferme", AutocompleteSelectFilter),
        ("date_mesure", RangeDateFilter),
    ]
    search_fields = ("ferme__nom", "parcelle_nom", "notes")
    ordering = ("-date_mesure",)
    list_select_related = ("ferme", "culture_precedente")
    autocomplete_fields = ("ferme", "culture_precedente")
    list_filter_submit = True


@admin.register(StockIntrant)
class StockIntrantAdmin(ModelAdmin):
    list_display = ("nom", "ferme", "categorie", "quantite", "unite", "seuil_alerte", "date_modification")
    list_filter = [
        ("ferme", AutocompleteSelectFilter),
        ("categorie", ChoicesDropdownFilter),
    ]
    search_fields = ("nom", "ferme__nom")
    ordering = ("-date_modification",)
    list_select_related = ("ferme",)
    list_filter_submit = True


@admin.register(StockRecolte)
class StockRecolteAdmin(ModelAdmin):
    list_display = ("produit", "ferme", "projet", "quantite", "unite", "date_recolte", "qualite")
    list_filter = [
        ("ferme", AutocompleteSelectFilter),
        ("qualite", ChoicesDropdownFilter),
        ("date_recolte", RangeDateFilter),
    ]
    search_fields = ("produit__nom", "ferme__nom")
    ordering = ("-date_recolte",)
    list_select_related = ("ferme", "projet", "produit")
    list_filter_submit = True


@admin.register(MouvementStock)
class MouvementStockAdmin(ModelAdmin):
    list_display = ("type", "stock_intrant", "stock_recolte", "quantite", "date_mouvement", "utilisateur")
    list_filter = [
        ("ferme", AutocompleteSelectFilter),
        ("type", ChoicesDropdownFilter),
        ("date_mouvement", RangeDateTimeFilter),
    ]
    search_fields = ("raison", "stock_intrant__nom", "stock_recolte__produit__nom")
    ordering = ("-date_mouvement",)
    list_select_related = ("ferme", "stock_intrant", "stock_recolte", "utilisateur__user")
    list_filter_submit = True


@admin.register(AppelAPILog)
class AppelAPILogAdmin(ModelAdmin):
    list_display = ("service", "modele", "timestamp", "cout_estime_usd", "cache_hit", "duree_ms", "alerte_cout")
    list_filter = [
        ("service", ChoicesDropdownFilter),
        ("cache_hit", ChoicesDropdownFilter),
        ("timestamp", RangeDateTimeFilter),
    ]
    ordering = ("-timestamp",)
    readonly_fields = ("service", "modele", "timestamp", "cout_estime_usd", "cache_hit", "duree_ms")
    list_filter_submit = True

    def alerte_cout(self, obj):
        seuil = Decimal(str(getattr(settings, "API_COUT_ALERTE_USD_JOUR", "1.00")))
        today = timezone.now().date()
        cout_jour = AppelAPILog.objects.filter(
            timestamp__date=today,
            cache_hit=False,
        ).aggregate(total=Sum("cout_estime_usd"))["total"] or Decimal("0")
        if cout_jour >= seuil:
            return format_html('<span style="color:red;font-weight:700;">⚠ ${}</span>', cout_jour)
        return format_html('<span style="color:green;">${}</span>', cout_jour)
    alerte_cout.short_description = "Coût jour"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        today = timezone.now().date()
        week_ago = today - timezone.timedelta(days=7)

        agg_day = AppelAPILog.objects.filter(timestamp__date=today).aggregate(
            total=Sum("cout_estime_usd"),
            hits=Count("id", filter=Q(cache_hit=True)),
            misses=Count("id", filter=Q(cache_hit=False)),
        )
        agg_week = AppelAPILog.objects.filter(timestamp__date__gte=week_ago).aggregate(
            total=Sum("cout_estime_usd"),
            hits=Count("id", filter=Q(cache_hit=True)),
            misses=Count("id", filter=Q(cache_hit=False)),
        )

        seuil = Decimal(str(getattr(settings, "API_COUT_ALERTE_USD_JOUR", "1.00")))
        cout_jour = agg_day["total"] or Decimal("0")
        alerte = cout_jour >= seuil

        total_day = (agg_day["hits"] or 0) + (agg_day["misses"] or 0)
        total_week = (agg_week["hits"] or 0) + (agg_week["misses"] or 0)

        extra_context.update({
            "cout_jour": cout_jour,
            "cout_semaine": agg_week["total"] or Decimal("0"),
            "taux_cache_jour": round(100 * (agg_day["hits"] or 0) / total_day) if total_day else 0,
            "taux_cache_semaine": round(100 * (agg_week["hits"] or 0) / total_week) if total_week else 0,
            "seuil_alerte": seuil,
            "alerte_active": alerte,
        })
        return super().changelist_view(request, extra_context=extra_context)


# ─── Actualités ───────────────────────────────────────────────────────────────

@admin.register(ArticleActualite)
class ArticleActualiteAdmin(ModelAdmin):
    list_display  = ("titre_tronque", "source", "categorie", "date_publication", "actif", "date_collecte")
    list_filter   = (
        ("source", ChoicesDropdownFilter),
        ("categorie", ChoicesDropdownFilter),
        "actif",
    )
    search_fields = ("titre", "resume", "url_originale")
    readonly_fields = ("date_collecte", "date_modification", "id")
    ordering = ("-date_publication", "-date_collecte")
    list_per_page = 50

    @admin.display(description="Titre")
    def titre_tronque(self, obj):
        return Truncator(obj.titre).chars(80)


# ─── Prix marchés ─────────────────────────────────────────────────────────────

@admin.register(PrixMarche)
class PrixMarcheAdmin(ModelAdmin):
    list_display  = (
        "produit_nom", "marche_nom", "region",
        "prix_unitaire", "unite", "source", "date_relevee", "date_collecte",
    )
    list_filter   = (
        ("source",      ChoicesDropdownFilter),
        ("date_relevee", RangeDateFilter),
    )
    search_fields  = ("produit_nom", "marche_nom", "region")
    readonly_fields = ("id", "date_collecte", "source_id")
    ordering       = ("-date_relevee", "produit_nom")
    list_per_page  = 50
    date_hierarchy = "date_relevee"


@admin.register(AlertePrix)
class AlertePrixAdmin(ModelAdmin):
    list_display   = (
        "produit_nom", "marche_nom", "variation_affichee",
        "niveau", "periode_jours", "vue", "date_detection",
    )
    list_filter    = (
        ("niveau",         ChoicesDropdownFilter),
        "vue",
        ("date_detection", RangeDateTimeFilter),
    )
    search_fields  = ("produit_nom", "marche_nom", "region")
    readonly_fields = (
        "id", "date_detection",
        "prix_actuel", "prix_reference", "variation_pct",
    )
    ordering       = ("-date_detection",)
    list_per_page  = 50
    actions        = ["marquer_vues", "marquer_non_vues"]

    @admin.display(description="Variation")
    def variation_affichee(self, obj) -> str:
        sens = "↑" if obj.variation_pct > 0 else "↓"
        return f"{sens} {abs(obj.variation_pct):.1f}%"

    @admin.action(description="Marquer comme vues")
    def marquer_vues(self, request, queryset):
        nb = queryset.update(vue=True)
        self.message_user(request, f"{nb} alerte(s) marquée(s) comme vues.")

    @admin.action(description="Marquer comme non vues")
    def marquer_non_vues(self, request, queryset):
        nb = queryset.update(vue=False)
        self.message_user(request, f"{nb} alerte(s) marquée(s) comme non vues.")


class MembreCooperativeInline(admin.TabularInline):
    model = MembreCooperative
    extra = 0
    autocomplete_fields = ("utilisateur",)


@admin.register(Cooperative)
class CooperativeAdmin(ModelAdmin):
    list_display = ("nom", "localite", "code_acces", "date_creation")
    search_fields = ("nom", "code_acces")
    inlines = (MembreCooperativeInline,)


@admin.register(MembreCooperative)
class MembreCooperativeAdmin(ModelAdmin):
    list_display = ("utilisateur", "cooperative", "role", "statut", "date_adhesion")
    list_filter = ("role", "statut")
    search_fields = ("utilisateur__user__username", "cooperative__nom")
    autocomplete_fields = ("utilisateur", "cooperative")
