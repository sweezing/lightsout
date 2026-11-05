from django.urls import path

from apps.moderation.views import report_card

from . import views
from .feed import feed

urlpatterns = [
    path("", views.cards, name="cards"),
    path("feed/", feed, name="cards-feed"),
    path("<uuid:card_id>/report/", report_card, name="card-report"),
]
