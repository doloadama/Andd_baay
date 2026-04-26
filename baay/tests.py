from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from baay.models import (
    DemandeAccesFerme,
    Ferme,
    MembreFerme,
)


def _create_user(username, email='', password='pass12345'):
    # Le profil est créé automatiquement par le signal post_save sur User.
    return User.objects.create_user(username=username, email=email, password=password)


class FermeCodeAccesTests(TestCase):
    def test_code_acces_genere_a_la_creation(self):
        owner = _create_user('owner1')
        ferme = Ferme.objects.create(nom='F1', proprietaire=owner.profile)
        self.assertEqual(len(ferme.code_acces), 8)
        self.assertTrue(ferme.code_acces.isalnum())

    def test_code_acces_unique(self):
        owner = _create_user('owner_u')
        f1 = Ferme.objects.create(nom='F1', proprietaire=owner.profile)
        f2 = Ferme.objects.create(nom='F2', proprietaire=owner.profile)
        self.assertNotEqual(f1.code_acces, f2.code_acces)


class AjouterMembreFermeTests(TestCase):
    def setUp(self):
        self.owner = _create_user('owner', 'owner@x.test')
        self.member = _create_user('member', 'member@x.test')
        self.outsider = _create_user('outsider', 'outsider@x.test')
        self.ferme = Ferme.objects.create(nom='Ferme A', proprietaire=self.owner.profile)
        self.url = reverse('ajouter_membre_ferme', args=[self.ferme.id])

    def test_proprietaire_peut_ajouter_membre(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'member', 'role': 'technicien'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(MembreFerme.objects.filter(ferme=self.ferme, utilisateur=self.member.profile, role='technicien').exists())
        # Email envoyé au membre
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('member@x.test', mail.outbox[0].to)

    def test_username_inexistant_refuse(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'ghost', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "n'est pas inscrit")
        self.assertFalse(MembreFerme.objects.filter(ferme=self.ferme).exists())

    def test_proprietaire_ne_peut_pas_s_ajouter(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'owner', 'role': 'manager'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'déjà le propriétaire')

    def test_membre_existant_refuse(self):
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.member.profile, role='ouvrier')
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'member', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'déjà membre')

    def test_non_proprietaire_sans_delegation_interdit(self):
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.member.profile, role='ouvrier', peut_gerer_membres=False)
        self.client.login(username='member', password='pass12345')
        resp = self.client.post(self.url, {'username': 'outsider', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(MembreFerme.objects.filter(utilisateur=self.outsider.profile).exists())

    def test_ajout_par_email(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'member@x.test', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(MembreFerme.objects.filter(ferme=self.ferme, utilisateur=self.member.profile).exists())

    def test_ajout_par_email_casse_insensible(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'MEMBER@X.TEST', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(MembreFerme.objects.filter(utilisateur=self.member.profile).exists())

    def test_email_introuvable_refuse(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'inconnu@x.test', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Aucun utilisateur inscrit")

    def test_email_ambigu_refuse(self):
        # Deux users avec le même email
        _create_user('dup1', 'dup@x.test')
        _create_user('dup2', 'dup@x.test')
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'username': 'dup@x.test', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Plusieurs utilisateurs')

    def test_membre_delegue_peut_ajouter(self):
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.member.profile, role='manager', peut_gerer_membres=True)
        self.client.login(username='member', password='pass12345')
        resp = self.client.post(self.url, {'username': 'outsider', 'role': 'ouvrier'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(MembreFerme.objects.filter(utilisateur=self.outsider.profile).exists())


class DemanderAccesFermeTests(TestCase):
    def setUp(self):
        self.owner = _create_user('owner', 'owner@x.test')
        self.req_user = _create_user('req', 'req@x.test')
        self.ferme = Ferme.objects.create(nom='Ferme B', proprietaire=self.owner.profile)
        self.url = reverse('demander_acces_ferme')

    def test_demande_avec_code_valide(self):
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces})
        self.assertEqual(resp.status_code, 302)
        demande = DemandeAccesFerme.objects.get(ferme=self.ferme, utilisateur=self.req_user.profile)
        self.assertEqual(demande.statut, 'en_attente')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('owner@x.test', mail.outbox[0].to)

    def test_code_invalide_refuse(self):
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': 'BADCODE1'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DemandeAccesFerme.objects.exists())

    def test_code_insensible_a_la_casse(self):
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces.lower()})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(DemandeAccesFerme.objects.filter(ferme=self.ferme).exists())

    def test_proprietaire_ne_peut_demander_sa_ferme(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DemandeAccesFerme.objects.exists())

    def test_membre_ne_peut_demander(self):
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.req_user.profile, role='ouvrier')
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DemandeAccesFerme.objects.exists())

    def test_demande_en_attente_dupliquee_refusee(self):
        DemandeAccesFerme.objects.create(ferme=self.ferme, utilisateur=self.req_user.profile, code=self.ferme.code_acces)
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DemandeAccesFerme.objects.count(), 1)

    def test_redemande_apres_refus_autorisee(self):
        # Une demande refusée ne doit pas bloquer une nouvelle demande en attente
        DemandeAccesFerme.objects.create(
            ferme=self.ferme,
            utilisateur=self.req_user.profile,
            code=self.ferme.code_acces,
            statut='refusee',
            date_traitement=timezone.now(),
        )
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            DemandeAccesFerme.objects.filter(ferme=self.ferme, utilisateur=self.req_user.profile).count(),
            2,
        )

    def test_rate_limit_5_par_24h(self):
        # Préparer 5 fermes différentes pour pouvoir créer 5 demandes en attente
        for i in range(5):
            f = Ferme.objects.create(nom=f'F{i}', proprietaire=self.owner.profile)
            DemandeAccesFerme.objects.create(ferme=f, utilisateur=self.req_user.profile, code=f.code_acces)
        self.client.login(username='req', password='pass12345')
        resp = self.client.post(self.url, {'code': self.ferme.code_acces})
        # Redirige sans créer de nouvelle demande
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            DemandeAccesFerme.objects.filter(utilisateur=self.req_user.profile).count(),
            5,
        )


class TraiterDemandeAccesTests(TestCase):
    def setUp(self):
        self.owner = _create_user('owner', 'owner@x.test')
        self.req_user = _create_user('req', 'req@x.test')
        self.other = _create_user('other', 'other@x.test')
        self.ferme = Ferme.objects.create(nom='Ferme C', proprietaire=self.owner.profile)
        self.demande = DemandeAccesFerme.objects.create(
            ferme=self.ferme,
            utilisateur=self.req_user.profile,
            code=self.ferme.code_acces,
        )

    def _url(self, action):
        return reverse('traiter_demande_acces_ferme', args=[self.ferme.id, self.demande.id, action])

    def test_get_interdit_require_post(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.get(self._url('approuver'))
        self.assertEqual(resp.status_code, 405)

    def test_approuver_avec_role_choisi(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self._url('approuver'), {'role': 'manager', 'peut_gerer_membres': 'on'})
        self.assertEqual(resp.status_code, 302)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'approuvee')
        self.assertIsNotNone(self.demande.date_traitement)
        membre = MembreFerme.objects.get(ferme=self.ferme, utilisateur=self.req_user.profile)
        self.assertEqual(membre.role, 'manager')
        self.assertTrue(membre.peut_gerer_membres)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('req@x.test', mail.outbox[0].to)

    def test_approuver_role_invalide_fallback_ouvrier(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self._url('approuver'), {'role': 'admin'})
        self.assertEqual(resp.status_code, 302)
        membre = MembreFerme.objects.get(ferme=self.ferme, utilisateur=self.req_user.profile)
        self.assertEqual(membre.role, 'ouvrier')
        self.assertFalse(membre.peut_gerer_membres)

    def test_refuser(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self._url('refuser'))
        self.assertEqual(resp.status_code, 302)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'refusee')
        self.assertFalse(MembreFerme.objects.filter(ferme=self.ferme, utilisateur=self.req_user.profile).exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_action_invalide(self):
        self.client.login(username='owner', password='pass12345')
        resp = self.client.post(self._url('autre'))
        self.assertEqual(resp.status_code, 302)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'en_attente')

    def test_non_proprietaire_interdit(self):
        self.client.login(username='other', password='pass12345')
        resp = self.client.post(self._url('approuver'))
        self.assertEqual(resp.status_code, 404)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'en_attente')
