"""Viewport queries for the shared canvas (Table 3).

On PostgreSQL the query uses the GiST index on point(x, y) created in
cards migration 0002:  point(x, y) <@ box(point(minX, minY), point(maxX, maxY)).
That is the "spatial indexing in PostgreSQL" from the proposal, done with the
built-in geometric types so the stack does not need PostGIS.

On SQLite (local unit tests without Postgres) it falls back to range filters.
"""
from dataclasses import dataclass

from django.conf import settings
from django.db import connection

from apps.cards.models import Card

@dataclass(frozen=True)
class BBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def normalized(self) -> "BBox":
        return BBox(
            min(self.min_x, self.max_x),
            min(self.min_y, self.max_y),
            max(self.min_x, self.max_x),
            max(self.min_y, self.max_y),
        )

def cards_in_bbox(bbox: BBox, limit: int | None = None):
    b = bbox.normalized()
    limit = min(limit or settings.LIGHTS_OUT["VIEWPORT_MAX_CARDS"], settings.LIGHTS_OUT["VIEWPORT_MAX_CARDS"])
    qs = Card.objects.filter(status=Card.Status.PUBLISHED)
    if connection.vendor == "postgresql":
        qs = qs.extra(
            where=["point(x, y) <@ box(point(%s, %s), point(%s, %s))"],
            params=[b.min_x, b.min_y, b.max_x, b.max_y],
        )
    else:
        qs = qs.filter(x__gte=b.min_x, x__lte=b.max_x, y__gte=b.min_y, y__lte=b.max_y)
    #newest first, so a crowded region shows what is happening tonight.
    return qs.order_by("-created_at")[:limit]
