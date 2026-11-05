from django.db import connection
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def health(request):
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return Response({"status": "ok"})

urlpatterns = [
    path("health/", health, name="health"),
]
