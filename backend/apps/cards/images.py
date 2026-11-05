"""Image handling for Feature 1: JPEG/PNG only, <= 5 MB, metadata stripped.

Re-encoding the pixels into a fresh image drops EXIF (GPS, camera serial,
timestamps) and any other embedded metadata.
"""
import io
import uuid

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

MAX_SIDE = 2048

def clean_image(upload):
    lo = settings.LIGHTS_OUT
    if upload.size > lo["IMAGE_MAX_BYTES"]:
        raise ValidationError({"image": "Image must be 5 MB or smaller."})
    try:
        src = Image.open(upload)
        fmt = src.format
        src.load()
    except (UnidentifiedImageError, OSError):
        raise ValidationError({"image": "File is not a valid image."})
    if fmt not in lo["IMAGE_FORMATS"]:
        raise ValidationError({"image": "Only JPEG and PNG are accepted."})

    #apply the orientation tag before we throw the tags away.
    img = ImageOps.exif_transpose(src)
    img.thumbnail((MAX_SIDE, MAX_SIDE))

    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    if img.mode == "P" and img.getpalette():
        clean.putpalette(img.getpalette())

    out = io.BytesIO()
    if fmt == "JPEG":
        clean.convert("RGB").save(out, format="JPEG", quality=85, optimize=True)
        ext, ctype = "jpg", "image/jpeg"
    else:
        clean.save(out, format="PNG", optimize=True)
        ext, ctype = "png", "image/png"
    out.seek(0)
    return InMemoryUploadedFile(out, "image", f"{uuid.uuid4().hex}.{ext}", ctype, out.getbuffer().nbytes, None)
