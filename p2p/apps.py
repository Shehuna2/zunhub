from django.apps import AppConfig

class P2PConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "p2p"

    def ready(self):
        import p2p.signals  # Import signals when the app is ready
