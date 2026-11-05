from django.urls import path

from . import views

urlpatterns = [
    path("resources/", views.resources, name="moderation-resources"),
    path("report-reasons/", views.report_reasons, name="moderation-report-reasons"),
]
