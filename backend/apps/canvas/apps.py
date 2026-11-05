from django.apps import AppConfig

class CanvasConfig(AppConfig):
    """Feature 2 - Shared Spatial Canvas (owner: Rustem Imangazin).

    Owns the viewport (bounding-box) query. Cards themselves live in apps.cards.
    """

    name = "apps.canvas"
    verbose_name = "Canvas"
