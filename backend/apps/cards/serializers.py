from django.conf import settings
from rest_framework import serializers

from .models import Card

LO = settings.LIGHTS_OUT

class CardSerializer(serializers.ModelSerializer):
    """Public shape of a card. Deliberately carries no identity and no
    prompt link (Table 4: answers are not labelled as replies)."""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ["id", "text", "image", "x", "y", "created_at"]

    def get_image(self, obj):
        return obj.image.url if obj.image else None

class CardCreateSerializer(serializers.Serializer):
    text = serializers.CharField(
        min_length=LO["CARD_TEXT_MIN"], max_length=LO["CARD_TEXT_MAX"], trim_whitespace=True
    )
    x = serializers.FloatField(min_value=-LO["WORLD_HALF_SIZE"], max_value=LO["WORLD_HALF_SIZE"])
    y = serializers.FloatField(min_value=-LO["WORLD_HALF_SIZE"], max_value=LO["WORLD_HALF_SIZE"])
    image = serializers.ImageField(required=False, allow_null=True)
    tz_offset = serializers.IntegerField(required=False, default=0, min_value=-14 * 60, max_value=14 * 60)

def serialize_card(card: Card) -> dict:
    data = CardSerializer(card).data
    data["id"] = str(data["id"])
    return data
