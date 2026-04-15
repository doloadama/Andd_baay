from django.apps import AppConfig


class BaayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'baay'

    def ready(self):
        import baay.signals


