from django.db.models import Q

from .models import Ferme, MembreFerme, Projet, ProjetProduit, Tache


ROLE_PROPRIETAIRE = 'proprietaire'
ROLE_MANAGER = 'manager'
ROLE_TECHNICIEN = 'technicien'
ROLE_OUVRIER = 'ouvrier'

ROLES_GESTION_PROJET = {ROLE_PROPRIETAIRE, ROLE_MANAGER}
ROLES_TECHNIQUES = {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_TECHNICIEN}
ROLES_VISIBILITE_FERME = {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_TECHNICIEN, ROLE_OUVRIER}


def role_dans_ferme(profile, ferme):
    if profile is None or ferme is None:
        return None
    if ferme.proprietaire_id == profile.id:
        return ROLE_PROPRIETAIRE
    membre = ferme.membres.filter(utilisateur=profile).only('role').first()
    return membre.role if membre else None


def membership_dans_ferme(profile, ferme):
    if profile is None or ferme is None:
        return None
    return ferme.membres.filter(utilisateur=profile).first()


def fermes_accessibles_qs(profile):
    if profile is None:
        return Ferme.objects.none()
    return Ferme.objects.filter(
        Q(proprietaire=profile) | Q(membres__utilisateur=profile)
    ).distinct()


def projets_accessibles_qs(profile):
    if profile is None:
        return Projet.objects.none()
    return Projet.objects.filter(
        Q(ferme__proprietaire=profile) | Q(ferme__membres__utilisateur=profile)
    ).distinct()


def peut_voir_ferme(profile, ferme):
    return role_dans_ferme(profile, ferme) in ROLES_VISIBILITE_FERME


def peut_modifier_ferme(profile, ferme):
    return role_dans_ferme(profile, ferme) == ROLE_PROPRIETAIRE


def peut_supprimer_ferme(profile, ferme):
    return peut_modifier_ferme(profile, ferme)


def peut_gerer_membres(profile, ferme):
    role = role_dans_ferme(profile, ferme)
    if role == ROLE_PROPRIETAIRE:
        return True
    membre = membership_dans_ferme(profile, ferme)
    return bool(membre and membre.peut_gerer_membres)


def peut_retirer_membres(profile, ferme):
    return role_dans_ferme(profile, ferme) == ROLE_PROPRIETAIRE


def peut_traiter_demandes_acces(profile, ferme):
    return role_dans_ferme(profile, ferme) == ROLE_PROPRIETAIRE


def peut_voir_projet(profile, projet):
    if projet is None:
        return False
    return peut_voir_ferme(profile, projet.ferme)


def peut_creer_projet(profile, ferme):
    return role_dans_ferme(profile, ferme) in ROLES_GESTION_PROJET


def peut_modifier_projet(profile, projet):
    if projet is None:
        return False
    return role_dans_ferme(profile, projet.ferme) in ROLES_GESTION_PROJET


def peut_supprimer_projet(profile, projet):
    if projet is None:
        return False
    return role_dans_ferme(profile, projet.ferme) == ROLE_PROPRIETAIRE


def peut_modifier_semis(profile, projet_produit):
    if projet_produit is None:
        return False
    return role_dans_ferme(profile, projet_produit.projet.ferme) in ROLES_TECHNIQUES


def peut_voir_semis(profile, projet_produit):
    if projet_produit is None:
        return False
    return peut_voir_projet(profile, projet_produit.projet)


def roles_assignables_par(role):
    return {
        ROLE_PROPRIETAIRE: [ROLE_MANAGER, ROLE_TECHNICIEN, ROLE_OUVRIER],
        ROLE_MANAGER: [ROLE_TECHNICIEN, ROLE_OUVRIER],
        ROLE_TECHNICIEN: [ROLE_OUVRIER],
        ROLE_OUVRIER: [],
        None: [],
    }.get(role, [])


def peut_creer_tache(profile, ferme):
    return bool(roles_assignables_par(role_dans_ferme(profile, ferme)))


def peut_voir_tache(profile, tache):
    if profile is None or tache is None:
        return False
    role = role_dans_ferme(profile, tache.ferme)
    if role in {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_TECHNICIEN}:
        return True
    if role == ROLE_OUVRIER:
        return tache.assigne_a_id == profile.id
    return False


def peut_changer_statut_tache(profile, tache):
    if profile is None or tache is None:
        return False
    return tache.assigne_a_id == profile.id or peut_modifier_tache(profile, tache)


def peut_modifier_tache(profile, tache):
    if profile is None or tache is None:
        return False
    role = role_dans_ferme(profile, tache.ferme)
    if role == ROLE_PROPRIETAIRE:
        return True
    if role == ROLE_MANAGER:
        return True
    if role == ROLE_TECHNICIEN:
        return True
    return tache.assigne_par_id == profile.id


def peut_supprimer_tache(profile, tache):
    if profile is None or tache is None:
        return False
    role = role_dans_ferme(profile, tache.ferme)
    if role == ROLE_PROPRIETAIRE:
        return True
    if role == ROLE_MANAGER:
        return True
    return tache.assigne_par_id == profile.id


def peut_supprimer_semis(profile, projet_produit):
    if projet_produit is None:
        return False
    return role_dans_ferme(profile, projet_produit.projet.ferme) == ROLE_PROPRIETAIRE
