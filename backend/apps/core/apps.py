from django.apps import AppConfig

class CoreConfig(AppConfig):
    """Shared helpers, health check and operational commands."""

    name = "apps.core"
    verbose_name = "Core"
