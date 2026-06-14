from django.db.models import Q
from django.utils import timezone

from .models import (
    Cooperative,
    Ferme,
    MembreCooperative,
    MembreFerme,
    Projet,
    ProjetProduit,
    Tache,
)


ROLE_PROPRIETAIRE = 'proprietaire'
ROLE_MANAGER = 'manager'
ROLE_TECHNICIEN = 'technicien'
ROLE_OUVRIER = 'ouvrier'
ROLE_CONSULTANT = 'consultant'
ROLE_INVITE = 'invite'

ROLES_GESTION_PROJET = {ROLE_PROPRIETAIRE, ROLE_MANAGER}
ROLES_TECHNIQUES = {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_TECHNICIEN}
ROLES_VISIBILITE_FERME = {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_TECHNICIEN, ROLE_OUVRIER, ROLE_CONSULTANT, ROLE_INVITE}
ROLES_LECTURE_FINANCE = {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_CONSULTANT}
ROLES_COMMENTAIRE = {ROLE_PROPRIETAIRE, ROLE_MANAGER, ROLE_TECHNICIEN, ROLE_CONSULTANT}

# ── Coopératives ──────────────────────────────────────────────────────────
# Force relative des rôles ferme (pour retenir le rôle effectif le plus fort).
_RANG_ROLE = {
    None: 0,
    ROLE_INVITE: 1,
    ROLE_CONSULTANT: 2,
    ROLE_OUVRIER: 3,
    ROLE_TECHNICIEN: 4,
    ROLE_MANAGER: 5,
    ROLE_PROPRIETAIRE: 6,
}

# Rôle coop -> rôle ferme effectif sur les fermes affiliées.
# Le propriétaire reste propriétaire : la coop ne dépasse jamais MANAGER
# (pas de suppression de ferme, pas de finance ROI sensible — checks dédiés).
_COOP_VERS_ROLE_FERME = {
    MembreCooperative.ROLE_ADMIN: ROLE_MANAGER,
    MembreCooperative.ROLE_GESTIONNAIRE: ROLE_MANAGER,
    MembreCooperative.ROLE_TECHNICIEN: ROLE_TECHNICIEN,
    MembreCooperative.ROLE_CONSULTANT: ROLE_CONSULTANT,
    MembreCooperative.ROLE_FERMIER_AFFILIE: None,  # aucun droit sur les fermes des autres
}
# Rôles coop qui donnent accès aux fermes de la coopérative (pour les querysets).
_ROLES_COOP_ACCES_FERMES = [
    r for r, mapped in _COOP_VERS_ROLE_FERME.items() if mapped is not None
]


def _membres_actifs_qs():
    """MembreFerme whose access has not expired."""
    now = timezone.now()
    return MembreFerme.objects.filter(
        Q(date_expiration__isnull=True) | Q(date_expiration__gt=now)
    )


def _membres_coop_actifs_qs():
    """MembreCooperative actifs et non expirés."""
    now = timezone.now()
    return MembreCooperative.objects.filter(
        statut='actif',
    ).filter(
        Q(date_expiration__isnull=True) | Q(date_expiration__gt=now)
    )


def role_dans_cooperative(profile, cooperative):
    """Rôle (actif) du profil dans une coopérative, ou None."""
    if profile is None or cooperative is None:
        return None
    membre = _membres_coop_actifs_qs().filter(
        cooperative=cooperative, utilisateur=profile,
    ).only('role').first()
    return membre.role if membre else None


def _role_coop_pour_ferme(profile, ferme):
    """Rôle ferme effectif dérivé de l'appartenance à la coopérative de la ferme."""
    coop_id = getattr(ferme, 'cooperative_id', None)
    if not coop_id or profile is None:
        return None
    membre = _membres_coop_actifs_qs().filter(
        cooperative_id=coop_id, utilisateur=profile,
    ).only('role').first()
    if membre is None:
        return None
    return _COOP_VERS_ROLE_FERME.get(membre.role)


def role_dans_ferme(profile, ferme):
    if profile is None or ferme is None:
        return None
    if ferme.proprietaire_id == profile.id:
        return ROLE_PROPRIETAIRE
    membre = _membres_actifs_qs().filter(ferme=ferme, utilisateur=profile).only('role').first()
    role_direct = membre.role if membre else None
    # Rôle dérivé de la coopérative affiliée à la ferme
    role_coop = _role_coop_pour_ferme(profile, ferme)
    # On retient le rôle le plus fort entre l'accès direct et l'accès coop.
    if _RANG_ROLE.get(role_coop, 0) > _RANG_ROLE.get(role_direct, 0):
        return role_coop
    return role_direct


def membership_dans_ferme(profile, ferme):
    if profile is None or ferme is None:
        return None
    return _membres_actifs_qs().filter(ferme=ferme, utilisateur=profile).first()


def _coop_ids_acces_fermes(profile):
    """IDs des coopératives où le profil a un rôle donnant accès aux fermes."""
    if profile is None:
        return []
    return list(
        _membres_coop_actifs_qs()
        .filter(utilisateur=profile, role__in=_ROLES_COOP_ACCES_FERMES)
        .values_list('cooperative_id', flat=True)
    )


def fermes_accessibles_qs(profile):
    if profile is None:
        return Ferme.objects.none()
    now = timezone.now()
    coop_ids = _coop_ids_acces_fermes(profile)
    return Ferme.objects.filter(
        Q(proprietaire=profile)
        | Q(
            membres__utilisateur=profile,
            membres__date_expiration__isnull=True,
        )
        | Q(
            membres__utilisateur=profile,
            membres__date_expiration__gt=now,
        )
        | Q(cooperative_id__in=coop_ids)
    ).distinct()


def projets_accessibles_qs(profile):
    if profile is None:
        return Projet.objects.none()
    coop_ids = _coop_ids_acces_fermes(profile)
    return Projet.objects.filter(
        Q(ferme__proprietaire=profile)
        | Q(ferme__membres__utilisateur=profile)
        | Q(ferme__cooperative_id__in=coop_ids)
    ).distinct()


def cooperatives_accessibles_qs(profile):
    """Coopératives dont le profil est membre (actif)."""
    if profile is None:
        return Cooperative.objects.none()
    coop_ids = _membres_coop_actifs_qs().filter(
        utilisateur=profile,
    ).values_list('cooperative_id', flat=True)
    return Cooperative.objects.filter(id__in=coop_ids).distinct()


def roles_coop_assignables_par(role):
    """Qui peut assigner quels rôles dans une coopérative."""
    return {
        MembreCooperative.ROLE_ADMIN: [
            MembreCooperative.ROLE_GESTIONNAIRE,
            MembreCooperative.ROLE_TECHNICIEN,
            MembreCooperative.ROLE_CONSULTANT,
            MembreCooperative.ROLE_FERMIER_AFFILIE,
        ],
        MembreCooperative.ROLE_GESTIONNAIRE: [
            MembreCooperative.ROLE_TECHNICIEN,
            MembreCooperative.ROLE_CONSULTANT,
            MembreCooperative.ROLE_FERMIER_AFFILIE,
        ],
        MembreCooperative.ROLE_TECHNICIEN: [],
        MembreCooperative.ROLE_CONSULTANT: [],
        MembreCooperative.ROLE_FERMIER_AFFILIE: [],
        None: [],
    }.get(role, [])


def peut_gerer_cooperative(profile, cooperative):
    """Gérer membres / fermes de la coop : admin (ou gestionnaire si autorisé)."""
    return role_dans_cooperative(profile, cooperative) == MembreCooperative.ROLE_ADMIN


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
        ROLE_PROPRIETAIRE: [ROLE_MANAGER, ROLE_TECHNICIEN, ROLE_OUVRIER, ROLE_CONSULTANT, ROLE_INVITE],
        ROLE_MANAGER: [ROLE_TECHNICIEN, ROLE_OUVRIER, ROLE_CONSULTANT, ROLE_INVITE],
        ROLE_TECHNICIEN: [ROLE_OUVRIER],
        ROLE_OUVRIER: [],
        ROLE_CONSULTANT: [],
        ROLE_INVITE: [],
        None: [],
    }.get(role, [])


def peut_acceder_menu_finance(profile):
    """
    Menu « Finance » et alertes budgétaires côté site : propriétaire
    de n'importe quelle ferme ou membre manager.
    """
    if profile is None:
        return False
    if Ferme.objects.filter(proprietaire=profile).exists():
        return True
    return _membres_actifs_qs().filter(
        utilisateur=profile,
        role=ROLE_MANAGER,
    ).exists()


def peut_voir_investissements(profile, ferme):
    return role_dans_ferme(profile, ferme) in ROLES_GESTION_PROJET


def projets_avec_vue_depenses_qs(profile):
    """Projets pour lesquels l'utilisateur peut consulter les investissements."""
    if profile is None:
        return Projet.objects.none()
    from django.db.models import Exists, OuterRef
    from .models import MembreFerme

    ferme_ids_prop = Ferme.objects.filter(proprietaire=profile).values_list(
        "pk", flat=True
    )
    mem_ok = MembreFerme.objects.filter(
        ferme_id=OuterRef("pk"),
        utilisateur=profile,
        role=ROLE_MANAGER,
    )
    ferme_ids_mem = (
        Ferme.objects.filter(Exists(mem_ok)).values_list("pk", flat=True)
    )
    return (
        Projet.objects.filter(Q(ferme_id__in=ferme_ids_prop) | Q(ferme_id__in=ferme_ids_mem))
        .select_related("ferme")
        .distinct()
        .order_by("nom")
    )


def projets_modifiables_depenses_qs(profile):
    """Projets où l'utilisateur peut saisir des dépenses (Propriétaire / Manager)."""
    if profile is None:
        return Projet.objects.none()
    ferme_ids_prop = Ferme.objects.filter(proprietaire=profile).values_list(
        "pk", flat=True
    )
    ferme_ids_mgr = MembreFerme.objects.filter(
        utilisateur=profile, role=ROLE_MANAGER
    ).values_list("ferme_id", flat=True)
    return (
        Projet.objects.filter(
            Q(ferme_id__in=ferme_ids_prop) | Q(ferme_id__in=ferme_ids_mgr)
        )
        .exclude(statut=Projet.STATUT_CLOTURE)
        .select_related("ferme")
        .distinct()
        .order_by("nom")
    )


def peut_personnaliser_taux_avancement_projet(profile, projet) -> bool:
    """
    Personnaliser le % d'avancement du projet : manager (MembreFerme) de la ferme,
    utilisateur staff / superuser (admin Django).
    """
    if profile is None or projet is None:
        return False
    user = getattr(profile, "user", None)
    if user is not None and user.is_superuser:
        return True
    if user is not None and user.is_staff:
        return True
    ferme_id = getattr(projet, "ferme_id", None)
    if not ferme_id:
        return False
    try:
        ferme = projet.ferme
    except Projet.ferme.RelatedObjectDoesNotExist:
        return False
    return role_dans_ferme(profile, ferme) == ROLE_MANAGER


def peut_modifier_budget_ferme(profile, ferme):
    """
    Modifier le budget (lignes Investissement) : propriétaire de la ferme
    ou membre avec rôle manager.
    """
    if profile is None or ferme is None:
        return False
    if ferme.proprietaire_id == profile.id:
        return True
    return _membres_actifs_qs().filter(
        ferme=ferme,
        utilisateur=profile,
        role=ROLE_MANAGER,
    ).exists()


def peut_modifier_investissement(profile, projet):
    """
    Création / modification des lignes Investissement : propriétaire de la ferme
    du projet ou membre manager.
    """
    if projet is None:
        return False
    return peut_modifier_budget_ferme(profile, projet.ferme)

def peut_voir_investissements_any(profile):
    if profile is None:
        return False
    now = timezone.now()
    return Ferme.objects.filter(
        Q(proprietaire=profile)
        | Q(
            membres__utilisateur=profile,
            membres__role=ROLE_MANAGER,
            membres__date_expiration__isnull=True,
        )
        | Q(
            membres__utilisateur=profile,
            membres__role=ROLE_MANAGER,
            membres__date_expiration__gt=now,
        )
    ).exists()


def peut_voir_kpi_roi_projet(profile, projet) -> bool:
    """
    Données sensibles ROI / coûts complets : superuser ou staff Django, sinon propriétaire
    de la ferme du projet (PAS manager invité hors propriété).

    Cf. cloisonnement type « need-to-know » sur indicateurs financiers consolidés.
    """
    if profile is None or projet is None:
        return False
    user = getattr(profile, "user", None)
    if user is not None and (user.is_superuser or user.is_staff):
        return True
    ferme_id = getattr(projet, "ferme_id", None)
    if not ferme_id:
        return False
    return Ferme.objects.filter(pk=ferme_id, proprietaire=profile).exists()


def projets_accessibles_kpi_roi_qs(profile, projets_qs):
    """Sous-ensemble de projets autorisés pour agrégats finance (ROI, total investissement)."""
    if profile is None:
        return Projet.objects.none()
    user = getattr(profile, "user", None)
    if user is not None and (user.is_superuser or user.is_staff):
        return projets_qs
    return projets_qs.filter(ferme__proprietaire=profile)


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
    # Changement de statut réservé à:
    # - l'assigné
    # - le créateur/assigneur
    # - le propriétaire / manager de la ferme
    if tache.assigne_a_id == profile.id:
        return True
    if tache.assigne_par_id == profile.id:
        return True
    role = role_dans_ferme(profile, tache.ferme)
    return role in {ROLE_PROPRIETAIRE, ROLE_MANAGER}


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


def peut_voir_inventaire(profile, ferme):
    """
    Consulter l'inventaire d'une ferme : tous les rôles ayant visibilité sur la ferme.
    """
    if profile is None or ferme is None:
        return False
    return role_dans_ferme(profile, ferme) in ROLES_VISIBILITE_FERME


def peut_modifier_inventaire(profile, ferme):
    """
    Modifier les stocks (ajout, ajustement, suppression) : propriétaire ou manager.
    """
    if profile is None or ferme is None:
        return False
    return role_dans_ferme(profile, ferme) in {ROLE_PROPRIETAIRE, ROLE_MANAGER}


def peut_creer_note_agronomique(profile, projet):
    """
    Créer une note agronomique sur un projet : consultant + rôles de gestion.
    """
    if profile is None or projet is None:
        return False
    return role_dans_ferme(profile, projet.ferme) in ROLES_COMMENTAIRE


def peut_voir_notes_agronomiques(profile, projet):
    """
    Voir les notes agronomiques d'un projet : tous ceux qui voient le projet.
    """
    if profile is None or projet is None:
        return False
    return peut_voir_projet(profile, projet)
