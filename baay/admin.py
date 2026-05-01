from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User
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
    list_display = ("nom", "proprietaire", "pays", "localite", "code_acces", "date_creation")
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
    list_display = ("nom", "saison", "prix_par_kg", "quantite_disponible", "etat")
    search_fields = ("nom", "saison")
    list_filter = [
        ("etat", ChoicesDropdownFilter),
    ]
    ordering = ("nom",)
    list_per_page = 25
    list_filter_submit = True


@admin.register(PhotoProduitAgricole)
class PhotoProduitAgricoleAdmin(ModelAdmin):
    list_display = ("produit", "description", "date_ajout")
    search_fields = ("produit__nom",)
    ordering = ("-date_ajout",)
    list_per_page = 25
    list_select_related = ("produit",)


@admin.register(Projet)
class ProjetAdmin(ModelAdmin):
    list_display = ("nom", "ferme", "statut", "culture", "superficie", "date_lancement")
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
    list_display = ("nom", "pays", "type_sol", "pluviometrie_moyenne")
    list_filter = [
        ("pays", AutocompleteSelectFilter),
        ("type_sol", ChoicesDropdownFilter),
    ]
    search_fields = ("nom",)
    ordering = ("nom",)
    list_filter_submit = True


@admin.register(Investissement)
class InvestissementAdmin(ModelAdmin):
    list_display = ("projet", "cout_par_hectare", "autres_frais", "date_investissement")
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
    list_display = ("utilisateur", "ferme", "code", "statut", "date_demande")
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
    list_display = ("produit", "projet", "date_semis", "superficie_allouee", "rendement_final")
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
    list_display = (
        "projet",
        "rendement_estime_min",
        "rendement_estime_max",
        "indice_confiance",
        "date_recolte_prevue",
        "date_prediction",
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
    list_display = ("conversation", "expediteur", "date_envoi", "contenu")
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
    list_display = ("message", "utilisateur", "emoji", "date_ajout")
    search_fields = ("emoji", "utilisateur__user__username")
    ordering = ("-date_ajout",)
    list_select_related = ("message", "utilisateur__user")
    list_filter_submit = True


@admin.register(Tache)
class TacheAdmin(ModelAdmin):
    list_display = ("titre", "ferme", "projet", "assigne_a", "statut", "priorite", "date_echeance")
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
