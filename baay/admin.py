from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from .models import (
    PhotoProduitAgricole,
    Projet,
    ProduitAgricole,
    Localite,
    Investissement,
    ProjetProduit,
)


@admin.register(ProduitAgricole)
class ProduitAgricoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'saison', 'prix_par_kg', 'quantite_disponible', 'etat')
    search_fields = ('nom', 'saison')
    list_filter = ('etat',)
    ordering = ('nom',)
    list_per_page = 10

@admin.register(PhotoProduitAgricole)
class PhotoProduitAgricoleAdmin(admin.ModelAdmin):
    list_display = ('produit', 'description', 'date_ajout')
    search_fields = ('produit__nom',)
    ordering = ('-date_ajout',)
    list_per_page = 10

# Register other models
admin.site.register(Projet)
admin.site.register(Localite)
admin.site.register(Investissement)
admin.site.register(ProjetProduit)
