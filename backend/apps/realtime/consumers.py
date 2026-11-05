"""WebSocket protocol for /ws/canvas/

client -> server
    {"type": "viewport", "min_x": .., "min_y": .., "max_x": .., "max_y": ..}
        (re)subscribe to the regions the reader can see; sent on connect,
        after every pan/zoom (debounced) and after a reconnect.
    {"type": "ping"}

server -> client
    {"type": "subscribed", "groups": n}
    {"type": "card.created", "card": {...}}    new published card in view
    {"type": "card.hidden", "id": "..."}       card taken down by moderation
    {"type": "pong"}
"""
import math

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from .tiles import groups_for_viewport

class CanvasConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.groups_joined: set[str] = set()
        await self.accept()

    async def disconnect(self, code):
        for g in self.groups_joined:
            await self.channel_layer.group_discard(g, self.channel_name)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        if kind == "ping":
            await self.send_json({"type": "pong"})
        elif kind == "viewport":
            await self._subscribe(content)

    async def _subscribe(self, c):
        w = settings.LIGHTS_OUT["WORLD_HALF_SIZE"]
        try:
            box = [max(-w, min(w, float(c[k]))) for k in ("min_x", "min_y", "max_x", "max_y")]
        except (KeyError, TypeError, ValueError):
            return
        if not all(math.isfinite(v) for v in box):
            return
        wanted = set(groups_for_viewport(*box))
        for g in self.groups_joined - wanted:
            await self.channel_layer.group_discard(g, self.channel_name)
        for g in wanted - self.groups_joined:
            await self.channel_layer.group_add(g, self.channel_name)
        self.groups_joined = wanted
        await self.send_json({"type": "subscribed", "groups": len(wanted)})

    #a reader is in either tile groups or the "all" group, never both, so each
    #card arrives once. the client still de-duplicates by id after reconnects.
    async def card_created(self, event):
        await self.send_json({"type": "card.created", "card": event["card"]})

    async def card_hidden(self, event):
        await self.send_json({"type": "card.hidden", "id": event["id"]})
