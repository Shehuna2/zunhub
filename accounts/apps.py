from django.apps import AppConfig
import os


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals  # Import signals to register them

    def ready(self):
        if os.environ.get("AUTO_SUPERUSER", "").lower() == "true":
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(username=os.environ["DJANGO_SUPERUSER_USERNAME"]).exists():
                User.objects.create_superuser(
                    username=os.environ["DJANGO_SUPERUSER_USERNAME"],
                    email=os.environ["DJANGO_SUPERUSER_EMAIL"],
                    password=os.environ["DJANGO_SUPERUSER_PASSWORD"]
                )
