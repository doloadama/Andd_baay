from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from baay.models import (
    Conversation,
    DemandeAccesFerme,
    Ferme,
    Localite,
    MembreFerme,
    Pays,
    ProduitAgricole,
    Projet,
    Message,
    ParticipationConversation,
    Tache,
)
from baay.permissions import (
    peut_creer_projet,
    peut_supprimer_projet,
    role_dans_ferme,
    roles_assignables_par,
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
        self.assertTrue(
            MembreFerme.objects.filter(
                ferme=ferme, utilisateur=owner.profile, role='proprietaire'
            ).exists()
        )

    def test_regenerer_code_proprietaire_change_code(self):
        owner = _create_user('ownreg', 'ownreg@x.test')
        self.client.login(username='ownreg', password='pass12345')
        ferme = Ferme.objects.create(nom='Freg', proprietaire=owner.profile)
        old = ferme.code_acces
        url = reverse('regenerer_code_acces_ferme', args=[ferme.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        ferme.refresh_from_db()
        self.assertNotEqual(ferme.code_acces, old)

    def test_regenerer_code_non_proprietaire_404(self):
        owner = _create_user('own2', 'o2@x.test')
        other = _create_user('oth2', 'oth2@x.test')
        ferme = Ferme.objects.create(nom='Fx', proprietaire=owner.profile)
        self.client.login(username='oth2', password='pass12345')
        url = reverse('regenerer_code_acces_ferme', args=[ferme.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)

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
        self.assertEqual(MembreFerme.objects.filter(ferme=self.ferme).count(), 1)
        self.assertTrue(
            MembreFerme.objects.filter(
                ferme=self.ferme, utilisateur=self.owner.profile, role='proprietaire'
            ).exists()
        )

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


class TacheTests(TestCase):
    """Hiérarchie d'attribution + permissions des tâches."""

    def setUp(self):
        self.owner = _create_user('t_owner', 'owner@t.test')
        self.manager = _create_user('t_manager', 'mgr@t.test')
        self.tech = _create_user('t_tech', 'tech@t.test')
        self.ouvrier = _create_user('t_ouvrier', 'ouv@t.test')
        self.outsider = _create_user('t_outsider', 'out@t.test')

        self.ferme = Ferme.objects.create(nom='F-Tache', proprietaire=self.owner.profile)
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.manager.profile, role='manager')
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.tech.profile, role='technicien')
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.ouvrier.profile, role='ouvrier')

    # --- Hiérarchie : qui peut assigner à qui ---

    def test_owner_peut_assigner_a_manager(self):
        self.client.login(username='t_owner', password='pass12345')
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'T1', 'description': '', 'priorite': 'normale',
            'assigne_a': self.manager.profile.id,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Tache.objects.filter(titre='T1', assigne_a=self.manager.profile).exists())

    def test_manager_peut_assigner_a_ouvrier(self):
        self.client.login(username='t_manager', password='pass12345')
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'T2', 'description': '', 'priorite': 'normale',
            'assigne_a': self.ouvrier.profile.id,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Tache.objects.filter(titre='T2').exists())

    def test_manager_ne_peut_pas_assigner_a_owner_ni_manager(self):
        self.client.login(username='t_manager', password='pass12345')
        # Le formulaire restreint le queryset → la valeur sera invalide
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'NOPE', 'description': '', 'priorite': 'normale',
            'assigne_a': self.owner.profile.id,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Tache.objects.filter(titre='NOPE').exists())

    def test_technicien_peut_assigner_a_ouvrier(self):
        self.client.login(username='t_tech', password='pass12345')
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'T3', 'description': '', 'priorite': 'haute',
            'assigne_a': self.ouvrier.profile.id,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Tache.objects.filter(titre='T3').exists())

    def test_technicien_ne_peut_pas_assigner_a_manager(self):
        self.client.login(username='t_tech', password='pass12345')
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'NOPE2', 'description': '', 'priorite': 'normale',
            'assigne_a': self.manager.profile.id,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Tache.objects.filter(titre='NOPE2').exists())

    def test_ouvrier_ne_peut_pas_creer_tache(self):
        self.client.login(username='t_ouvrier', password='pass12345')
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'NOPE3', 'description': '', 'priorite': 'normale',
            'assigne_a': self.ouvrier.profile.id,
        })
        self.assertEqual(resp.status_code, 302)  # redirigé vers liste avec message
        self.assertFalse(Tache.objects.filter(titre='NOPE3').exists())

    def test_outsider_ne_peut_pas_creer_tache(self):
        self.client.login(username='t_outsider', password='pass12345')
        # outsider n'est membre d'aucune ferme → page 404 sur creer_tache_ferme
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'NOPE4', 'description': '', 'priorite': 'normale',
            'assigne_a': self.ouvrier.profile.id,
        })
        self.assertIn(resp.status_code, (302, 404))
        self.assertFalse(Tache.objects.filter(titre='NOPE4').exists())

    # --- Email à la création ---

    def test_email_envoye_a_lassigne(self):
        self.client.login(username='t_owner', password='pass12345')
        mail.outbox = []
        self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'T-mail', 'description': 'desc', 'priorite': 'normale',
            'assigne_a': self.ouvrier.profile.id,
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ouv@t.test', mail.outbox[0].to)
        self.assertIn('T-mail', mail.outbox[0].subject)

    # --- Liste filtrée par rôle ---

    def test_ouvrier_voit_uniquement_ses_taches(self):
        Tache.objects.create(ferme=self.ferme, titre='Pour ouvrier',
                             assigne_a=self.ouvrier.profile, assigne_par=self.manager.profile)
        Tache.objects.create(ferme=self.ferme, titre='Pour manager',
                             assigne_a=self.manager.profile, assigne_par=self.owner.profile)
        self.client.login(username='t_ouvrier', password='pass12345')
        resp = self.client.get(reverse('taches_liste'))
        self.assertContains(resp, 'Pour ouvrier')
        self.assertNotContains(resp, 'Pour manager')

    def test_manager_voit_taches_de_la_ferme(self):
        Tache.objects.create(ferme=self.ferme, titre='X1',
                             assigne_a=self.ouvrier.profile, assigne_par=self.tech.profile)
        self.client.login(username='t_manager', password='pass12345')
        resp = self.client.get(reverse('taches_liste'))
        self.assertContains(resp, 'X1')

    # --- Changement de statut ---

    def test_assigne_peut_changer_statut(self):
        tache = Tache.objects.create(ferme=self.ferme, titre='C1',
                                     assigne_a=self.ouvrier.profile, assigne_par=self.manager.profile)
        self.client.login(username='t_ouvrier', password='pass12345')
        resp = self.client.post(reverse('tache_detail', args=[tache.id]), {
            'action': 'changer_statut',
            'statut': 'terminee',
            'commentaire_retour': 'fait',
        })
        self.assertEqual(resp.status_code, 302)
        tache.refresh_from_db()
        self.assertEqual(tache.statut, 'terminee')
        self.assertIsNotNone(tache.date_terminee)
        self.assertEqual(tache.commentaire_retour, 'fait')

    def test_non_assigne_ne_peut_pas_changer_statut(self):
        tache = Tache.objects.create(ferme=self.ferme, titre='C2',
                                     assigne_a=self.ouvrier.profile, assigne_par=self.manager.profile)
        self.client.login(username='t_tech', password='pass12345')
        # Le technicien n'est ni créateur ni assigné → action refusée
        self.client.post(reverse('tache_detail', args=[tache.id]), {
            'action': 'changer_statut',
            'statut': 'terminee',
        })
        tache.refresh_from_db()
        self.assertEqual(tache.statut, 'a_faire')

    def test_email_envoye_au_createur_a_la_completion(self):
        tache = Tache.objects.create(ferme=self.ferme, titre='C3',
                                     assigne_a=self.ouvrier.profile, assigne_par=self.manager.profile)
        self.client.login(username='t_ouvrier', password='pass12345')
        mail.outbox = []
        self.client.post(reverse('tache_detail', args=[tache.id]), {
            'action': 'changer_statut', 'statut': 'terminee',
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('mgr@t.test', mail.outbox[0].to)

    # --- Suppression ---

    def test_createur_peut_supprimer(self):
        tache = Tache.objects.create(ferme=self.ferme, titre='S1',
                                     assigne_a=self.ouvrier.profile, assigne_par=self.manager.profile)
        self.client.login(username='t_manager', password='pass12345')
        resp = self.client.post(reverse('tache_detail', args=[tache.id]), {'action': 'supprimer'})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Tache.objects.filter(id=tache.id).exists())

    def test_assigne_ne_peut_pas_supprimer(self):
        tache = Tache.objects.create(ferme=self.ferme, titre='S2',
                                     assigne_a=self.ouvrier.profile, assigne_par=self.manager.profile)
        self.client.login(username='t_ouvrier', password='pass12345')
        self.client.post(reverse('tache_detail', args=[tache.id]), {'action': 'supprimer'})
        self.assertTrue(Tache.objects.filter(id=tache.id).exists())

    # --- Validation date ---

    def test_echeance_dans_le_passe_refusee(self):
        from datetime import date, timedelta
        passe = (date.today() - timedelta(days=2)).isoformat()
        self.client.login(username='t_owner', password='pass12345')
        resp = self.client.post(reverse('creer_tache_ferme', args=[self.ferme.id]), {
            'titre': 'Past', 'description': '', 'priorite': 'normale',
            'assigne_a': self.ouvrier.profile.id, 'date_echeance': passe,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Tache.objects.filter(titre='Past').exists())


class PermissionsRoleTests(TestCase):
    """Tests de permissions centralisées par rôle."""

    def setUp(self):
        self.owner = _create_user('owner_p', 'owner@p.test')
        self.manager = _create_user('mgr_p', 'mgr@p.test')
        self.tech = _create_user('tech_p', 'tech@p.test')
        self.ouvrier = _create_user('ouv_p', 'ouv@p.test')
        self.outsider = _create_user('out_p', 'out@p.test')

        self.ferme = Ferme.objects.create(nom='F-Perm', proprietaire=self.owner.profile)
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.manager.profile, role='manager')
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.tech.profile, role='technicien')
        MembreFerme.objects.create(ferme=self.ferme, utilisateur=self.ouvrier.profile, role='ouvrier')

        self.pays = Pays.objects.create(nom='Sénégal', code_iso='SN')
        self.localite = Localite.objects.create(nom='Dakar', pays=self.pays)
        self.produit = ProduitAgricole.objects.create(nom='Mil')
        self.projet = Projet.objects.create(
            nom='Projet Test',
            ferme=self.ferme,
            utilisateur=self.owner.profile,
            localite=self.localite,
            superficie=10,
            date_lancement=timezone.now().date(),
        )

    # --- Projets visibility ---

    def test_manager_voit_projet_cree_par_proprietaire(self):
        self.client.login(username='mgr_p', password='pass12345')
        resp = self.client.get(reverse('detail_projet', args=[self.projet.id]))
        self.assertEqual(resp.status_code, 200)

    def test_technicien_voit_projet_cree_par_proprietaire(self):
        self.client.login(username='tech_p', password='pass12345')
        resp = self.client.get(reverse('detail_projet', args=[self.projet.id]))
        self.assertEqual(resp.status_code, 200)

    def test_ouvrier_ne_peut_pas_modifier_projet(self):
        self.client.login(username='ouv_p', password='pass12345')
        resp = self.client.post(reverse('modifier_projet', args=[self.projet.id]), {
            'nom': 'Hack',
            'superficie': 1,
            'date_lancement': timezone.now().date(),
        })
        self.assertEqual(resp.status_code, 302)
        self.projet.refresh_from_db()
        self.assertEqual(self.projet.nom, 'Projet Test')

    # --- Tâches : ouvrier ne voit que ses tâches ---

    def test_ouvrier_ne_peut_pas_voir_tache_d_un_autre(self):
        tache_autre = Tache.objects.create(
            ferme=self.ferme, titre='Tache autre',
            assigne_a=self.manager.profile, assigne_par=self.owner.profile
        )
        self.client.login(username='ouv_p', password='pass12345')
        resp = self.client.get(reverse('tache_detail', args=[tache_autre.id]))
        self.assertEqual(resp.status_code, 302)

    # --- Fermes : manager ne peut pas supprimer ---

    def test_manager_ne_peut_pas_supprimer_ferme(self):
        self.client.login(username='mgr_p', password='pass12345')
        resp = self.client.post(reverse('supprimer_ferme', args=[self.ferme.id]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Ferme.objects.filter(id=self.ferme.id).exists())

    # --- Projets : manager peut créer ---

    def test_manager_peut_creer_projet_dans_sa_ferme(self):
        self.client.login(username='mgr_p', password='pass12345')
        url = reverse('creer_projet') + f'?ferme={self.ferme.id}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url, {
            'nom': 'Projet Manager',
            'superficie': 5,
            'date_lancement': timezone.now().date(),
            'ferme': self.ferme.id,
            'localite': self.localite.id,
            'statut': 'en_cours',
            'produits_selection': [self.produit.id],
            'type_irrigation': 'Aucune',
            'type_engrais': 'Aucun',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Projet.objects.filter(nom='Projet Manager').exists())

    # --- Semis : technicien peut modifier mais pas supprimer projet ---

    def test_technicien_peut_modifier_semis(self):
        from baay.models import ProjetProduit
        pp = ProjetProduit.objects.create(projet=self.projet, produit=self.produit, superficie_allouee=2)
        self.client.login(username='tech_p', password='pass12345')
        resp = self.client.get(reverse('modifier_semis', args=[pp.id]))
        self.assertEqual(resp.status_code, 200)

    def test_technicien_ne_peut_pas_supprimer_projet(self):
        self.client.login(username='tech_p', password='pass12345')
        resp = self.client.post(reverse('supprimer_projet', args=[self.projet.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Projet.objects.filter(id=self.projet.id).exists())

    def test_budget_investissement_requiert_membre_manager_ou_proprietaire(self):
        from baay.permissions import peut_modifier_investissement

        self.assertTrue(peut_modifier_investissement(self.manager.profile, self.projet))
        self.assertTrue(peut_modifier_investissement(self.owner.profile, self.projet))
        self.assertFalse(peut_modifier_investissement(self.tech.profile, self.projet))
        self.assertFalse(peut_modifier_investissement(self.ouvrier.profile, self.projet))

    def test_proprietaire_sans_ligne_membreferme_ne_peut_pas_modifier_budget(self):
        from baay.permissions import peut_modifier_investissement

        owner_orphan = _create_user('owner_orphan', 'oo@test')
        ferme_orphan = Ferme.objects.create(nom='F-Orphan', proprietaire=owner_orphan.profile)
        MembreFerme.objects.filter(ferme=ferme_orphan, utilisateur=owner_orphan.profile).delete()
        projet_orphan = Projet.objects.create(
            nom='P-Orphan',
            ferme=ferme_orphan,
            utilisateur=owner_orphan.profile,
            localite=self.localite,
            superficie=1,
            date_lancement=timezone.now().date(),
        )
        self.assertFalse(peut_modifier_investissement(owner_orphan.profile, projet_orphan))

    def test_permission_policy_role_resolution(self):
        self.assertEqual(role_dans_ferme(self.owner.profile, self.ferme), 'proprietaire')
        self.assertEqual(role_dans_ferme(self.manager.profile, self.ferme), 'manager')
        self.assertEqual(role_dans_ferme(self.tech.profile, self.ferme), 'technicien')
        self.assertEqual(role_dans_ferme(self.ouvrier.profile, self.ferme), 'ouvrier')

    def test_permission_policy_assignable_roles(self):
        self.assertEqual(roles_assignables_par('proprietaire'), ['manager', 'technicien', 'ouvrier'])
        self.assertEqual(roles_assignables_par('manager'), ['technicien', 'ouvrier'])
        self.assertEqual(roles_assignables_par('technicien'), ['ouvrier'])
        self.assertEqual(roles_assignables_par('ouvrier'), [])

    def test_permission_policy_create_delete_project(self):
        self.assertTrue(peut_creer_projet(self.owner.profile, self.ferme))
        self.assertTrue(peut_creer_projet(self.manager.profile, self.ferme))
        self.assertFalse(peut_creer_projet(self.tech.profile, self.ferme))
        self.assertFalse(peut_creer_projet(self.ouvrier.profile, self.ferme))
        self.assertTrue(peut_supprimer_projet(self.owner.profile, self.projet))
        self.assertFalse(peut_supprimer_projet(self.manager.profile, self.projet))


class MessagerieReliabilityTests(TestCase):
    def setUp(self):
        self.sender = _create_user('msg_sender', 'sender@x.test')
        self.receiver = _create_user('msg_receiver', 'receiver@x.test')
        self.conversation = Conversation.objects.create(sujet='Reliability')
        self.conversation.participants.add(self.sender.profile, self.receiver.profile)
        self.url = reverse('conversation_detail', args=[self.conversation.id])

    def test_idempotent_send_with_client_message_id(self):
        self.client.login(username='msg_sender', password='pass12345')
        client_id = '11111111-1111-1111-1111-111111111111'
        payload = {
            'contenu': 'hello-idempotent',
            'client_message_id': client_id,
        }
        resp1 = self.client.post(self.url, payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_ACCEPT='application/json')
        self.assertEqual(resp1.status_code, 200)
        resp2 = self.client.post(self.url, payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_ACCEPT='application/json')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(
            Message.objects.filter(conversation=self.conversation, expediteur=self.sender.profile, client_message_id=client_id).count(),
            1,
        )

    def test_sync_endpoint_returns_messages_since_timestamp(self):
        m1 = Message.objects.create(conversation=self.conversation, expediteur=self.sender.profile, contenu='m1')
        m2 = Message.objects.create(conversation=self.conversation, expediteur=self.receiver.profile, contenu='m2')
        self.client.login(username='msg_sender', password='pass12345')
        sync_url = reverse('api_conversation_sync', args=[self.conversation.id])
        resp = self.client.get(sync_url, {'since': m1.date_envoi.isoformat()})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('type'), 'chat_sync_v1')
        returned_ids = [item['message_id'] for item in data.get('messages', [])]
        self.assertIn(str(m2.id), returned_ids)
        self.assertNotIn(str(m1.id), returned_ids)

    def test_read_receipt_persisted_on_open(self):
        msg = Message.objects.create(conversation=self.conversation, expediteur=self.sender.profile, contenu='to-read')
        self.client.login(username='msg_receiver', password='pass12345')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        msg.refresh_from_db()
        self.assertTrue(msg.lu_par.filter(id=self.receiver.profile.id).exists())

    def test_participation_last_read_bumped_on_open(self):
        Message.objects.create(conversation=self.conversation, expediteur=self.sender.profile, contenu='ping')
        pc = ParticipationConversation.objects.get(
            profile=self.receiver.profile,
            conversation=self.conversation,
        )
        self.assertIsNone(pc.last_read_at)
        self.client.login(username='msg_receiver', password='pass12345')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        pc.refresh_from_db()
        self.assertIsNotNone(pc.last_read_at)

    def test_messages_older_endpoint_loads_previous_chunk(self):
        from datetime import timedelta

        base = timezone.now() - timedelta(hours=1)
        ids_ordered = []
        for i in range(55):
            m = Message.objects.create(
                conversation=self.conversation,
                expediteur=self.sender.profile,
                contenu=f'm-{i}',
            )
            Message.objects.filter(pk=m.pk).update(date_envoi=base + timedelta(seconds=i))
            ids_ordered.append(m.id)
        self.client.login(username='msg_sender', password='pass12345')
        resp_page = self.client.get(self.url)
        self.assertEqual(resp_page.status_code, 200)
        oldest_shown = ids_ordered[55 - 50]
        older_url = reverse('conversation_messages_older', args=[self.conversation.id])
        resp = self.client.get(older_url, {'before': str(oldest_shown)})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'm-4')
        self.assertNotContains(resp, 'm-6')
