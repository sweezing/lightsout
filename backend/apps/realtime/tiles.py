"""Canvas regions for broadcasting.

The canvas is cut into square tiles. A reader subscribes to the tiles their
viewport overlaps, and a new card is broadcast only to its own tile, so a
reader is not sent cards from the far side of the canvas (Table 5:
"broadcast by canvas region").

When a reader zooms far out and would need more than LIVE_MAX_TILES tiles,
they join the "all" group instead.
"""
import math

from django.conf import settings

ALL_GROUP = "canvas.all"

def tile_size() -> int:
    return settings.LIGHTS_OUT["LIVE_TILE_SIZE"]

def tile_of(x: float, y: float) -> tuple[int, int]:
    s = tile_size()
    return math.floor(x / s), math.floor(y / s)

def group_name(tx: int, ty: int) -> str:
    #Channels group names: ASCII alphanumerics, hyphens, underscores, periods.
    return f"canvas.tile.{tx}.{ty}".replace("-", "m")

def groups_for_card(x: float, y: float) -> list[str]:
    return [group_name(*tile_of(x, y)), ALL_GROUP]

def groups_for_viewport(min_x: float, min_y: float, max_x: float, max_y: float) -> list[str]:
    tx0, ty0 = tile_of(min(min_x, max_x), min(min_y, max_y))
    tx1, ty1 = tile_of(max(min_x, max_x), max(min_y, max_y))
    count = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
    if count > settings.LIGHTS_OUT["LIVE_MAX_TILES"]:
        return [ALL_GROUP]
    return [group_name(tx, ty) for tx in range(tx0, tx1 + 1) for ty in range(ty0, ty1 + 1)]
