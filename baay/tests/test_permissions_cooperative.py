"""Cascade des permissions coopérative (Phase 4).

Vérifie que les rôles coop donnent le bon accès aux fermes affiliées, que la
propriété est préservée (pas de suppression par la coop), et que le rôle
effectif retenu est le plus fort.
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from baay.models import (
    Cooperative,
    Ferme,
    MembreCooperative,
    MembreFerme,
    Profile,
)
from baay import permissions as perm


def _user(username):
    u = User.objects.create_user(username, password="x")
    p, _ = Profile.objects.get_or_create(user=u)
    return p


class CooperativePermissionsTest(TestCase):
    def setUp(self):
        self.owner = _user("owner")          # propriétaire de ferme_A
        self.admin = _user("coop_admin")
        self.tech = _user("coop_tech")
        self.consult = _user("coop_consult")
        self.affilie = _user("affilie")      # fermier affilié, possède ferme_B
        self.outsider = _user("outsider")

        self.coop = Cooperative.objects.create(nom="Coop Niayes")

        self.ferme_a = Ferme(nom="Ferme A", proprietaire=self.owner, cooperative=self.coop)
        self.ferme_a.save()
        self.ferme_b = Ferme(nom="Ferme B", proprietaire=self.affilie, cooperative=self.coop)
        self.ferme_b.save()
        self.ferme_hors = Ferme(nom="Ferme hors coop", proprietaire=self.owner)
        self.ferme_hors.save()

        mk = MembreCooperative.objects.create
        mk(cooperative=self.coop, utilisateur=self.admin, role=MembreCooperative.ROLE_ADMIN)
        mk(cooperative=self.coop, utilisateur=self.tech, role=MembreCooperative.ROLE_TECHNICIEN)
        mk(cooperative=self.coop, utilisateur=self.consult, role=MembreCooperative.ROLE_CONSULTANT)
        mk(cooperative=self.coop, utilisateur=self.affilie, role=MembreCooperative.ROLE_FERMIER_AFFILIE)

    # ── rôles effectifs dérivés ──────────────────────────────────────────
    def test_admin_est_manager_sur_ferme_affiliee(self):
        self.assertEqual(perm.role_dans_ferme(self.admin, self.ferme_a), perm.ROLE_MANAGER)

    def test_technicien_coop_est_technicien(self):
        self.assertEqual(perm.role_dans_ferme(self.tech, self.ferme_a), perm.ROLE_TECHNICIEN)

    def test_consultant_coop_est_consultant(self):
        self.assertEqual(perm.role_dans_ferme(self.consult, self.ferme_a), perm.ROLE_CONSULTANT)

    def test_fermier_affilie_na_pas_acces_aux_autres_fermes(self):
        # affilié = propriétaire de B, mais aucun droit sur A (ferme d'un autre)
        self.assertIsNone(perm.role_dans_ferme(self.affilie, self.ferme_a))

    def test_proprietaire_reste_proprietaire(self):
        self.assertEqual(perm.role_dans_ferme(self.owner, self.ferme_a), perm.ROLE_PROPRIETAIRE)

    def test_outsider_aucun_acces(self):
        self.assertIsNone(perm.role_dans_ferme(self.outsider, self.ferme_a))

    def test_pas_de_cascade_sur_ferme_hors_coop(self):
        self.assertIsNone(perm.role_dans_ferme(self.admin, self.ferme_hors))

    # ── garde-fou propriété ──────────────────────────────────────────────
    def test_admin_ne_peut_pas_supprimer_la_ferme(self):
        self.assertFalse(perm.peut_supprimer_ferme(self.admin, self.ferme_a))
        self.assertFalse(perm.peut_modifier_ferme(self.admin, self.ferme_a))

    def test_admin_peut_gerer_projets(self):
        self.assertTrue(perm.peut_creer_projet(self.admin, self.ferme_a))

    def test_consultant_voit_la_ferme(self):
        self.assertTrue(perm.peut_voir_ferme(self.consult, self.ferme_a))

    # ── querysets ────────────────────────────────────────────────────────
    def test_fermes_accessibles_inclut_fermes_affiliees(self):
        ids = set(perm.fermes_accessibles_qs(self.admin).values_list("id", flat=True))
        self.assertIn(self.ferme_a.id, ids)
        self.assertIn(self.ferme_b.id, ids)

    def test_fermier_affilie_ne_voit_que_sa_ferme(self):
        ids = set(perm.fermes_accessibles_qs(self.affilie).values_list("id", flat=True))
        self.assertIn(self.ferme_b.id, ids)
        self.assertNotIn(self.ferme_a.id, ids)

    # ── rôle le plus fort ────────────────────────────────────────────────
    def test_role_le_plus_fort_entre_direct_et_coop(self):
        # ouvrier direct (rang 3) + technicien coop (rang 4) -> technicien
        MembreFerme.objects.create(ferme=self.ferme_a, utilisateur=self.tech, role="ouvrier")
        self.assertEqual(perm.role_dans_ferme(self.tech, self.ferme_a), perm.ROLE_TECHNICIEN)

    # ── membre suspendu / expiré ─────────────────────────────────────────
    def test_membre_suspendu_perd_acces(self):
        m = MembreCooperative.objects.get(cooperative=self.coop, utilisateur=self.admin)
        m.statut = "suspendu"
        m.save()
        self.assertIsNone(perm.role_dans_ferme(self.admin, self.ferme_a))

    def test_membre_expire_perd_acces(self):
        m = MembreCooperative.objects.get(cooperative=self.coop, utilisateur=self.tech)
        m.date_expiration = timezone.now() - timedelta(days=1)
        m.save()
        self.assertIsNone(perm.role_dans_ferme(self.tech, self.ferme_a))
