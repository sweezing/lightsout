"""Feature 1 - Anonymous Card Posting. One test per row of Table 2 where it
can be checked automatically."""
import io
import uuid

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.cards.models import Card, RateLimitEvent

URL = "/api/cards/"

def token():
    return uuid.uuid4().hex

def jpeg_with_exif(size=(64, 48)):
    img = Image.new("RGB", size, (20, 30, 60))
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker" #make
    exif[0x0132] = "2026:10:31 02:14:00"  #datetime
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()

@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class PostingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tok = token()

    def post(self, data, tok=None, fmt="json"):
        return self.client.post(URL, data, format=fmt, HTTP_X_SESSION_TOKEN=tok or self.tok)

    def test_publishes_without_account(self):
        r = self.post({"text": "still awake", "x": 10, "y": -5})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["status"], "published")
        self.assertEqual(Card.objects.get().status, Card.Status.PUBLISHED)

    def test_text_length_1_to_280(self):
        self.assertEqual(self.post({"text": "", "x": 0, "y": 0}).status_code, 400)
        self.assertEqual(self.post({"text": "a" * 281, "x": 0, "y": 0}).status_code, 400)
        self.assertEqual(self.post({"text": "a" * 280, "x": 0, "y": 0}).status_code, 201)
        self.assertEqual(self.post({"text": "a", "x": 0, "y": 0}).status_code, 201)

    def test_session_token_required(self):
        r = self.client.post(URL, {"text": "hi", "x": 0, "y": 0}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_rate_limit_five_per_hour(self):
        for i in range(5):
            self.assertEqual(self.post({"text": f"card {i}", "x": i, "y": 0}).status_code, 201)
        r = self.post({"text": "one too many", "x": 0, "y": 0})
        self.assertEqual(r.status_code, 429)
        #a different session is unaffected.
        self.assertEqual(self.post({"text": "other", "x": 0, "y": 0}, tok=token()).status_code, 201)

    def test_no_identity_stored_on_card(self):
        self.post({"text": "anonymous", "x": 0, "y": 0})
        field_names = {f.name for f in Card._meta.get_fields()}
        for forbidden in ("user", "username", "email", "ip", "ip_address", "session", "session_hash"):
            self.assertNotIn(forbidden, field_names)
        #the token itself is never stored, only a keyed hash in a separate table.
        self.assertNotEqual(RateLimitEvent.objects.get().session_hash, self.tok)

    def test_public_shape_has_no_identity_or_prompt(self):
        card = self.post({"text": "shape", "x": 0, "y": 0}).json()["card"]
        self.assertEqual(set(card), {"id", "text", "image", "x", "y", "created_at"})

    def test_image_exif_is_stripped(self):
        upload = SimpleUploadedFile("IMG_0001.jpg", jpeg_with_exif(), content_type="image/jpeg")
        r = self.post({"text": "with photo", "x": 0, "y": 0, "image": upload}, fmt="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        card = Card.objects.get()
        self.assertNotIn("IMG_0001", card.image.name)
        with card.image.open("rb") as f:
            self.assertEqual(len(Image.open(f).getexif()), 0)
        card.image.delete(save=False)

    def test_rejects_non_jpeg_png(self):
        buf = io.BytesIO()
        Image.new("RGB", (8, 8)).save(buf, format="GIF")
        upload = SimpleUploadedFile("a.gif", buf.getvalue(), content_type="image/gif")
        r = self.post({"text": "gif", "x": 0, "y": 0, "image": upload}, fmt="multipart")
        self.assertEqual(r.status_code, 400)

    @override_settings(LIGHTS_OUT={**settings.LIGHTS_OUT, "IMAGE_MAX_BYTES": 100})
    def test_rejects_images_over_limit(self):
        upload = SimpleUploadedFile("big.jpg", jpeg_with_exif((200, 200)), content_type="image/jpeg")
        r = self.post({"text": "big", "x": 0, "y": 0, "image": upload}, fmt="multipart")
        self.assertEqual(r.status_code, 400)

    def test_coordinates_bounded(self):
        self.assertEqual(self.post({"text": "far", "x": 10**9, "y": 0}).status_code, 400)
