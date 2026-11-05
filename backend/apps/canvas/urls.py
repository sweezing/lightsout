from django.urls import path

from . import views

urlpatterns = [
    path("viewport/", views.viewport, name="canvas-viewport"),
]
