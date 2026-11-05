from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.cards.serializers import CardSerializer
from apps.core.params import float_param, int_param

from .spatial import BBox, cards_in_bbox

@api_view(["GET"])
def viewport(request):
    """GET /api/canvas/viewport/?min_x=&min_y=&max_x=&max_y=[&limit=]

    Returns at most 200 published cards inside the bounding box (Table 3).
    """
    w = settings.LIGHTS_OUT["WORLD_HALF_SIZE"]
    cap = settings.LIGHTS_OUT["VIEWPORT_MAX_CARDS"]
    bbox = BBox(
        float_param(request, "min_x", lo=-w, hi=w),
        float_param(request, "min_y", lo=-w, hi=w),
        float_param(request, "max_x", lo=-w, hi=w),
        float_param(request, "max_y", lo=-w, hi=w),
    )
    limit = int_param(request, "limit", default=cap, lo=1, hi=cap)
    cards = cards_in_bbox(bbox, limit)
    return Response({"bbox": bbox.normalized().__dict__, "cards": CardSerializer(cards, many=True).data})
