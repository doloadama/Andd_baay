# baay/tests/test_api_mobile.py
# ── Tests DRF pour l'API mobile v1 ──────────────────────────────────────────
import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from rest_framework.test import APIClient

from baay.models import Commentaire, Ferme, Localite, Pays, Profile, Projet, Tache


def _make_user(username="testuser", password="pass1234"):
    user = User.objects.create_user(username, password=password)
    # Profile est créé par signal post_save ; s'assurer qu'il existe
    profile, _ = Profile.objects.get_or_create(user=user)
    return user, profile


def _make_localite():
    pays, _ = Pays.objects.get_or_create(nom="Sénégal", defaults={"code_iso": "SN"})
    loc, _ = Localite.objects.get_or_create(nom="Dakar", defaults={"pays": pays})
    return loc


# ══════════════════════════════════════════════════════════════════════════════
# Ferme
# ══════════════════════════════════════════════════════════════════════════════

class FermeAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, self.profile = _make_user("farmer")
        self.client.force_authenticate(user=self.user)

    def test_list_fermes_empty(self):
        response = self.client.get("/api/v1/taches/")
        # Aucune tâche — la liste doit être vide et le statut 200
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_list_fermes_mobile_empty(self):
        response = self.client.get("/api/mobile/fermes/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_create_ferme_mobile(self):
        response = self.client.post(
            "/api/mobile/fermes/",
            {"nom": "Ferme Koliabé", "superficie_totale": "10.00"},
            format="json",
        )
        self.assertIn(response.status_code, [200, 201])
        self.assertIn("nom", response.data)

    def test_unauthenticated_returns_401(self):
        anon = APIClient()
        response = anon.get("/api/mobile/fermes/")
        self.assertEqual(response.status_code, 401)


# ══════════════════════════════════════════════════════════════════════════════
# Tâches
# ══════════════════════════════════════════════════════════════════════════════

class TacheAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, self.profile = _make_user("chef")
        self.client.force_authenticate(user=self.user)
        # Créer une ferme pour les tâches
        self.ferme = Ferme(nom="Ferme Test", proprietaire=self.profile)
        self.ferme.save()

    def test_list_taches_empty(self):
        response = self.client.get("/api/v1/taches/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_create_tache(self):
        user2, profile2 = _make_user("worker")
        response = self.client.post(
            "/api/v1/taches/",
            {
                "titre": "Arroser les plants",
                "description": "Arrosage quotidien",
                "statut": "a_faire",
                "priorite": "normale",
                "ferme": str(self.ferme.id),
                "assigne_a": str(profile2.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Tache.objects.count(), 1)

    def test_create_tache_rejects_other_users_farm(self):
        other_user, other_profile = _make_user("other_owner")
        other_ferme = Ferme.objects.create(nom="Ferme Victime", proprietaire=other_profile)

        response = self.client.post(
            "/api/v1/taches/",
            {
                "titre": "Tâche injectée",
                "description": "Ne doit pas être créée",
                "statut": "a_faire",
                "priorite": "normale",
                "ferme": str(other_ferme.id),
                "assigne_a": str(self.profile.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Tache.objects.filter(ferme=other_ferme).exists())

    def test_update_tache_statut(self):
        user2, profile2 = _make_user("worker2")
        tache = Tache.objects.create(
            titre="Semis",
            ferme=self.ferme,
            assigne_a=profile2,
            assigne_par=self.profile,
            statut="a_faire",
        )
        response = self.client.patch(
            f"/api/v1/taches/{tache.id}/statut/",
            {"statut": "en_cours"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        tache.refresh_from_db()
        self.assertEqual(tache.statut, "en_cours")

    def test_list_taches_filtre_ferme(self):
        user2, profile2 = _make_user("worker3")
        Tache.objects.create(
            titre="Tâche filtrée",
            ferme=self.ferme,
            assigne_a=profile2,
            assigne_par=self.profile,
        )
        response = self.client.get(f"/api/v1/taches/?ferme={self.ferme.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


# ══════════════════════════════════════════════════════════════════════════════
# Commentaires
# ══════════════════════════════════════════════════════════════════════════════

class CommentaireAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, self.profile = _make_user("commenteur")
        self.client.force_authenticate(user=self.user)
        self.ferme = Ferme(nom="Ferme Commentaires", proprietaire=self.profile)
        self.ferme.save()

    def test_list_commentaires_ferme_empty(self):
        response = self.client.get(f"/api/v1/commentaires/ferme/{self.ferme.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_create_commentaire_ferme(self):
        response = self.client.post(
            f"/api/v1/commentaires/ferme/{self.ferme.id}/",
            {"texte": "Bonne récolte cette année !"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("texte", response.data)

    def test_commentaires_ferme_reject_other_users_farm(self):
        other_user, other_profile = _make_user("autre_ferme")
        other_ferme = Ferme.objects.create(nom="Ferme privée", proprietaire=other_profile)
        ct = ContentType.objects.get_for_model(Ferme)
        Commentaire.objects.create(
            content_type=ct,
            object_id=other_ferme.id,
            auteur=other_profile,
            texte="Commentaire privé",
        )

        get_response = self.client.get(f"/api/v1/commentaires/ferme/{other_ferme.id}/")
        post_response = self.client.post(
            f"/api/v1/commentaires/ferme/{other_ferme.id}/",
            {"texte": "Intrusion"},
            format="json",
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        self.assertEqual(Commentaire.objects.filter(object_id=other_ferme.id).count(), 1)

    def test_create_commentaire_tache(self):
        user2, profile2 = _make_user("worker_c")
        tache = Tache.objects.create(
            titre="Récolte",
            ferme=self.ferme,
            assigne_a=profile2,
            assigne_par=self.profile,
        )
        response = self.client.post(
            f"/api/v1/commentaires/tache/{tache.id}/",
            {"texte": "Récolte terminée"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_commentaire_ct_label_invalide(self):
        response = self.client.post(
            f"/api/v1/commentaires/inconnu/{self.ferme.id}/",
            {"texte": "Test"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_commentaire(self):
        anon = APIClient()
        response = anon.get(f"/api/v1/commentaires/ferme/{self.ferme.id}/")
        self.assertEqual(response.status_code, 401)


class CommentaireWebTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user, self.profile = _make_user("web_commenteur")
        self.client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")
        self.ferme = Ferme.objects.create(nom="Ferme Web", proprietaire=self.profile)

    def test_create_commentaire_ferme_web(self):
        ct = ContentType.objects.get_for_model(Ferme)

        response = self.client.post(
            f"/commentaires/{ct.pk}/{self.ferme.id}/",
            {"texte": "Commentaire ferme"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Commentaire.objects.filter(object_id=self.ferme.id).count(), 1)

    def test_create_commentaire_tache_web(self):
        ct = ContentType.objects.get_for_model(Tache)
        tache = Tache.objects.create(
            titre="Tâche web",
            ferme=self.ferme,
            assigne_a=self.profile,
            assigne_par=self.profile,
        )

        response = self.client.post(
            f"/commentaires/{ct.pk}/{tache.id}/",
            {"texte": "Commentaire tâche"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Commentaire.objects.filter(object_id=tache.id).count(), 1)


# ══════════════════════════════════════════════════════════════════════════════
# Profil & Auth endpoints
# ══════════════════════════════════════════════════════════════════════════════

class ProfileAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, self.profile = _make_user("profile_user")
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        response = self.client.get("/api/v1/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.data)

    def test_get_me(self):
        response = self.client.get("/api/mobile/auth/me/")
        self.assertEqual(response.status_code, 200)


# ══════════════════════════════════════════════════════════════════════════════
# Diagnostic async
# ══════════════════════════════════════════════════════════════════════════════

class DiagnosticAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, self.profile = _make_user("diag_user")
        self.client.force_authenticate(user=self.user)

    def test_diagnostic_result_expired(self):
        fake_id = str(uuid.uuid4())
        response = self.client.get(f"/api/v1/diagnostic/{fake_id}/")
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data["status"], "expired")

    @patch("baay.tasks.diagnostic.analyze_plant_pest_task.delay")
    def test_diagnostic_submit_no_photo(self, mock_delay):
        response = self.client.post("/api/v1/diagnostic/", {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        mock_delay.assert_not_called()
