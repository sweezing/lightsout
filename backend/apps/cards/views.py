"""Feature 1 endpoints.

POST /api/cards/            create a card (2 steps in the UI: write, then place)
GET  /api/cards/            latest published cards (no bounding box)
POST /api/cards/<id>/report/  one-tap report (Feature 5)
"""
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.moderation import pipeline
from apps.moderation.resources import support_resources
from apps.prompts.schedule import active_prompt
from apps.realtime.broadcast import broadcast_card_created

from . import ratelimit
from .images import clean_image
from .models import Card
from .serializers import CardCreateSerializer, CardSerializer, serialize_card

@api_view(["GET", "POST"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@throttle_classes([])
def cards(request):
    if request.method == "GET":
        qs = Card.objects.filter(status=Card.Status.PUBLISHED)[: settings.LIGHTS_OUT["VIEWPORT_MAX_CARDS"]]
        return Response(CardSerializer(qs, many=True).data)
    return create_card(request)

def create_card(request):
    h = ratelimit.session_hash(request)
    if h is None:
        return Response(
            {"detail": "Missing or invalid X-Session-Token header."}, status=status.HTTP_400_BAD_REQUEST
        )
    if ratelimit.is_limited(h):
        return Response(
            {"status": "rate_limited", "detail": "That's enough for this hour. The canvas will still be here."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    ser = CardCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    image = clean_image(data["image"]) if data.get("image") else None

    #feature 5: screening runs BEFORE anything is published.
    verdict = pipeline.screen(data["text"])

    with transaction.atomic():
        prompt = active_prompt(data["tz_offset"])
        card = Card.objects.create(
            text=data["text"],
            x=data["x"],
            y=data["y"],
            image=image,
            status=verdict.card_status,
            prompt=prompt.prompt if prompt.in_window else None,
        )
        pipeline.log_auto_decision(card, verdict)
        ratelimit.record(h)

    if verdict.card_status == Card.Status.PUBLISHED:
        transaction.on_commit(lambda: broadcast_card_created(card))
        return Response({"status": "published", "card": serialize_card(card)}, status=status.HTTP_201_CREATED)

    if verdict.card_status == Card.Status.WITHHELD:
        #crisis indicator: card is held back, the poster sees support resources.
        return Response(
            {
                "status": "withheld",
                "detail": "Your card was not posted. It sounds like tonight is heavy. You don't have to carry it alone.",
                "resources": support_resources(),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response(
        {"status": "rejected", "detail": "This card can't be posted because it breaks the canvas rules."},
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
