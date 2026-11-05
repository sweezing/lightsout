from django.urls import path

from .consumers import CanvasConsumer

websocket_urlpatterns = [
    path("ws/canvas/", CanvasConsumer.as_asgi()),
]
