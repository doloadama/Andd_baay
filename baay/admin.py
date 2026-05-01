from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User
from django.utils.text import Truncator
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from .models import (
    Conversation,
    DemandeAccesFerme,
    Ferme,
    Investissement,
    Localite,
    Message,
    MessageReaction,
    Pays,
    PhotoProduitAgricole,
    PrevisionRecolte,
    ProduitAgricole,
    Profile,
    Projet,
    ProjetProduit,
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


@admin.register(Pays)
class PaysAdmin(ModelAdmin):
    list_display = ("nom", "code_iso")
    search_fields = ("nom", "code_iso")
    ordering = ("nom",)
    list_per_page = 50


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ("user", "phone_number")
    search_fields = ("user__username", "user__email", "phone_number")
    ordering = ("user__username",)
    list_filter_submit = True


@admin.register(Ferme)
class FermeAdmin(ModelAdmin):
    # Colonnes réduites : pays / localité restent filtrables sans encombrer la grille
    list_display = ("nom", "proprietaire", "code_acces", "date_creation")
    list_filter = [
        ("pays", AutocompleteSelectFilter),
        ("localite", AutocompleteSelectFilter),
    ]
    search_fields = ("nom", "code_acces", "proprietaire__user__username")
    ordering = ("-date_creation",)
    list_select_related = ("proprietaire__user", "pays", "localite")
    list_filter_submit = True


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
class ProjetAdmin(ModelAdmin):
    list_display = ("nom", "ferme", "statut", "date_lancement")
    list_filter = [
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


@admin.register(Localite)
class LocaliteAdmin(ModelAdmin):
    list_display = ("nom", "pays", "type_sol")
    list_filter = [
        ("pays", AutocompleteSelectFilter),
        ("type_sol", ChoicesDropdownFilter),
    ]
    search_fields = ("nom",)
    ordering = ("nom",)
    list_filter_submit = True


@admin.register(Investissement)
class InvestissementAdmin(ModelAdmin):
    list_display = ("projet", "cout_par_hectare", "date_investissement")
    list_filter = [
        ("date_investissement", RangeDateFilter),
        ("projet", AutocompleteSelectFilter),
    ]
    search_fields = ("projet__nom", "description")
    ordering = ("-date_investissement",)
    list_select_related = ("projet", "projet__ferme")
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
    list_display = ("produit", "projet", "superficie_allouee")
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
class PrevisionRecolteAdmin(ModelAdmin):
    @admin.display(description="Rendement (min – max)")
    def rendement_fourchette(self, obj):
        return f"{obj.rendement_estime_min} – {obj.rendement_estime_max}"

    list_display = (
        "projet",
        "rendement_fourchette",
        "indice_confiance",
        "date_recolte_prevue",
    )
    list_filter = [
        ("projet", AutocompleteSelectFilter),
        ("date_prediction", RangeDateTimeFilter),
    ]
    search_fields = ("projet__nom",)
    ordering = ("-date_prediction",)
    list_select_related = ("projet",)
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
class TacheAdmin(ModelAdmin):
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
