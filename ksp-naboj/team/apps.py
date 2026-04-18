from django.apps import AppConfig


class TeamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ksp-naboj.team"
    label = "ksp_naboj_team"

    def ready(self):
        from . import signals
