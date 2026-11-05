"""Pinterest-style feed: every published card, shuffled, paged for infinite scroll.

GET /api/cards/feed/?seed=<per-visit random string>&offset=0&limit=40

The order is a stable shuffle keyed by `seed`: the same visit always gets the
same order, so paging never repeats or skips a card, and a new visit gets a
new order. There is no ranking of any kind (no likes, no counts, no recency
boost), which keeps the proposal's "nothing is at the top" principle even in
a scrolling layout. Brand-new cards arrive separately over the live socket.
"""
import hashlib
import re

from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.core.params import int_param

from .models import Card
from .serializers import CardSerializer

DEFAULT_LIMIT = 40
MAX_LIMIT = 100
SEED_RE = re.compile(r"[^A-Za-z0-9]")

def clean_seed(raw: str | None) -> str:
    return SEED_RE.sub("", raw or "")[:32] or "0"

def shuffled(seed: str):
    qs = Card.objects.filter(status=Card.Status.PUBLISHED)
    if connection.vendor == "postgresql":
        return qs.extra(
            select={"shuffle_key": "md5(cards_card.id::text || %s)"}, select_params=[seed]
        ).order_by("shuffle_key", "id")
    #SQLite (quick local tests): same idea computed in Python.
    cards = list(qs)
    cards.sort(key=lambda c: hashlib.md5(f"{c.id}{seed}".encode()).hexdigest())
    return cards

@api_view(["GET"])
def feed(request):
    seed = clean_seed(request.query_params.get("seed"))
    offset = int_param(request, "offset", default=0, lo=0, hi=1_000_000)
    limit = int_param(request, "limit", default=DEFAULT_LIMIT, lo=1, hi=MAX_LIMIT)
    page = list(shuffled(seed)[offset : offset + limit + 1])
    has_more = len(page) > limit
    return Response(
        {
            "cards": CardSerializer(page[:limit], many=True).data,
            "next_offset": offset + limit if has_more else None,
        }
    )
