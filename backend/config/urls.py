from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Lights Out moderation"
admin.site.site_title = "Lights Out"
admin.site.index_title = "Review queue and content"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/cards/", include("apps.cards.urls")),
    path("api/canvas/", include("apps.canvas.urls")),
    path("api/prompt/", include("apps.prompts.urls")),
    path("api/moderation/", include("apps.moderation.urls")),
]
