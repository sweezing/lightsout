"""Feature 4 - Live Card Delivery (Table 5)."""
import uuid

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.realtime.tiles import ALL_GROUP, groups_for_card, groups_for_viewport
from config.asgi import application

LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

class TileTests(TransactionTestCase):
    def test_card_goes_to_its_tile_and_all(self):
        self.assertEqual(groups_for_card(10, 10), ["canvas.tile.0.0", ALL_GROUP])
        self.assertEqual(groups_for_card(-10, 10)[0], "canvas.tile.m1.0")

    def test_viewport_subscribes_to_overlapping_tiles(self):
        self.assertEqual(len(groups_for_viewport(-100, -100, 100, 100)), 4)

    def test_huge_viewport_falls_back_to_all(self):
        self.assertEqual(groups_for_viewport(-40000, -40000, 40000, 40000), [ALL_GROUP])

@override_settings(CHANNEL_LAYERS=LAYER)
class LiveDeliveryTests(TransactionTestCase):
    async def connect(self, bbox):
        ws = WebsocketCommunicator(application, "/ws/canvas/")
        ok, _ = await ws.connect()
        self.assertTrue(ok)
        await ws.send_json_to({"type": "viewport", **bbox})
        msg = await ws.receive_json_from(timeout=2)
        self.assertEqual(msg["type"], "subscribed")
        return ws

    async def post(self, text, x, y):
        def _post():
            return APIClient().post(
                "/api/cards/", {"text": text, "x": x, "y": y}, format="json",
                HTTP_X_SESSION_TOKEN=uuid.uuid4().hex,
            )
        r = await sync_to_async(_post)()
        self.assertEqual(r.status_code, 201, r.content)

    async def test_card_reaches_reader_in_same_region_within_3s(self):
        ws = await self.connect({"min_x": -500, "min_y": -500, "max_x": 500, "max_y": 500})
        await self.post("hello from the dark", 50, 50)
        msg = await ws.receive_json_from(timeout=3)
        self.assertEqual(msg["type"], "card.created")
        self.assertEqual(msg["card"]["text"], "hello from the dark")
        await ws.disconnect()

    async def test_reader_elsewhere_gets_nothing(self):
        ws = await self.connect({"min_x": 20000, "min_y": 20000, "max_x": 20500, "max_y": 20500})
        await self.post("far away", 0, 0)
        self.assertTrue(await ws.receive_nothing(timeout=0.5))
        await ws.disconnect()

    async def test_ping(self):
        ws = await self.connect({"min_x": 0, "min_y": 0, "max_x": 1, "max_y": 1})
        await ws.send_json_to({"type": "ping"})
        self.assertEqual((await ws.receive_json_from(timeout=2))["type"], "pong")
        await ws.disconnect()

    async def test_bad_viewport_is_ignored(self):
        ws = WebsocketCommunicator(application, "/ws/canvas/")
        await ws.connect()
        await ws.send_json_to({"type": "viewport", "min_x": "nan?"})
        self.assertTrue(await ws.receive_nothing(timeout=0.3))
        await ws.disconnect()
