"""Unit tests for view-level helpers."""
import base64
import io

import pytest
from django.test import Client
from django.urls import reverse
from PIL import Image as PilImage

from tests.factories import PieceFactory

# Minimal 1x1 white PNG as bytes (for building test files)
def _make_png_bytes():
    buf = io.BytesIO()
    PilImage.new("RGB", (1, 1), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_png_file(name="test.png"):
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, _make_png_bytes(), content_type="image/png")


@pytest.mark.django_db
class TestUploadImageAjax:
    def test_rejects_get(self):
        c = Client()
        resp = c.get(reverse("pieces:upload_image"))
        assert resp.status_code == 405

    def test_rejects_missing_file(self):
        c = Client()
        resp = c.post(reverse("pieces:upload_image"), {})
        assert resp.status_code == 400

    def test_saves_png_and_returns_path(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        settings.DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
        c = Client()
        resp = c.post(
            reverse("pieces:upload_image"),
            {"image": _make_png_file()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "path" in data
        assert data["path"].endswith(".png")
        assert (tmp_path / data["path"]).exists()

    def test_converts_non_png_to_png(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Create a BMP image (not natively served by browsers)
        buf = io.BytesIO()
        PilImage.new("RGB", (2, 2)).save(buf, format="BMP")
        bmp_file = SimpleUploadedFile("shot.bmp", buf.getvalue(), content_type="image/bmp")

        c = Client()
        resp = c.post(reverse("pieces:upload_image"), {"image": bmp_file})
        assert resp.status_code == 200
        assert resp.json()["path"].endswith(".png")

    def test_attach_uploaded_image_sets_field(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        piece = PieceFactory()
        c = Client()

        # Upload the image first
        upload_resp = c.post(
            reverse("pieces:upload_image"),
            {"image": _make_png_file()},
        )
        assert upload_resp.status_code == 200
        uploaded_path = upload_resp.json()["path"]

        # Submit the add-passage form referencing the uploaded path
        add_resp = c.post(
            reverse("pieces:trickybit_add", args=[piece.pk]),
            {
                "label": "Test passage",
                "difficulty": "3",
                "uploaded_image_path": uploaded_path,
            },
        )
        # Should redirect to piece detail (302)
        assert add_resp.status_code == 302

        piece.refresh_from_db()
        bit = piece.tricky_bits.first()
        assert bit is not None
        assert bit.image.name == uploaded_path
