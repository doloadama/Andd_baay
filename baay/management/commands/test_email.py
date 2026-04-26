"""
Commande de diagnostic pour vérifier la configuration email.

Usage:
    python manage.py test_email destinataire@example.com
    python manage.py test_email destinataire@example.com --subject "Hello"

Affiche la configuration courante (backend, host, port, user, TLS/SSL,
from), tente l'envoi, et rapporte précisément l'erreur SMTP en cas d'échec.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Envoie un email de test pour valider la configuration SMTP."

    def add_arguments(self, parser):
        parser.add_argument('to', help="Adresse email de destination.")
        parser.add_argument(
            '--subject',
            default='[Andd Baay] Test de configuration email',
            help="Sujet personnalisé (optionnel).",
        )

    def handle(self, *args, **options):
        to = options['to']
        subject = options['subject']

        self.stdout.write(self.style.MIGRATE_HEADING("Configuration courante :"))
        self.stdout.write(f"  EMAIL_BACKEND     = {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  EMAIL_HOST        = {settings.EMAIL_HOST}")
        self.stdout.write(f"  EMAIL_PORT        = {settings.EMAIL_PORT}")
        self.stdout.write(f"  EMAIL_HOST_USER   = {settings.EMAIL_HOST_USER or '(vide)'}")
        self.stdout.write(
            f"  EMAIL_HOST_PASSWORD = {'***' if settings.EMAIL_HOST_PASSWORD else '(vide)'}"
        )
        self.stdout.write(f"  EMAIL_USE_TLS     = {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  EMAIL_USE_SSL     = {getattr(settings, 'EMAIL_USE_SSL', False)}")
        self.stdout.write(f"  DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write("")

        body = (
            "Ceci est un email de test envoye depuis Andd Baay.\n\n"
            "Si vous le recevez, votre configuration SMTP est operationnelle.\n"
        )

        self.stdout.write(f"Envoi a {to}...")
        try:
            sent = send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f"Echec d'envoi : {type(exc).__name__}: {exc}")

        if sent:
            self.stdout.write(self.style.SUCCESS(f"OK : {sent} email(s) accepte(s) par le serveur."))
        else:
            self.stdout.write(self.style.WARNING("Aucun email envoye (le backend a renvoye 0)."))
