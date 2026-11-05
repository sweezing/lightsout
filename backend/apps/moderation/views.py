from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.cards.models import Card

from . import pipeline
from .models import Report
from .resources import support_resources

class ReportSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=Report.Reason.choices, default=Report.Reason.OTHER)

@api_view(["POST"])
def report_card(request, card_id):
    """POST /api/cards/<id>/report/  - one tap, no account, reason optional."""
    card = get_object_or_404(Card, id=card_id, status=Card.Status.PUBLISHED)
    ser = ReportSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    pipeline.register_report(card, ser.validated_data["reason"])
    return Response({"status": "received"}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
def resources(request):
    """GET /api/moderation/resources/ - support resources (also linked in the UI footer)."""
    return Response({"resources": support_resources()})

@api_view(["GET"])
def report_reasons(request):
    return Response({"reasons": [{"value": v, "label": l} for v, l in Report.Reason.choices]})
