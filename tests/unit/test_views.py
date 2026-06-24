"""Unit tests for view-level helpers."""
import base64

import pytest

from pieces.views import _apply_pasted_image
from tests.factories import PieceFactory, TrickyBitFactory

# Minimal 1x1 white PNG encoded as base64
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
)
_PNG_DATA_URL = f"data:image/png;base64,{_PNG_B64}"


@pytest.mark.django_db
class TestApplyPastedImage:
    def test_saves_image_from_valid_base64(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        bit.image = None  # simulate no file upload

        _apply_pasted_image(bit, {"image_data": _PNG_DATA_URL})
        bit.save()

        bit.refresh_from_db()
        assert bool(bit.image)
        assert bit.image.name.endswith(".png")

    def test_ignores_empty_image_data(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        bit.image = None

        _apply_pasted_image(bit, {"image_data": ""})
        bit.save()

        bit.refresh_from_db()
        assert not bit.image

    def test_ignores_malformed_data_url(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        bit.image = None

        _apply_pasted_image(bit, {"image_data": "data:image/png;base64,NOT_VALID_B64!!!"})
        bit.save()

        bit.refresh_from_db()
        assert not bit.image

    def test_ignores_non_image_data_url(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        bit.image = None

        _apply_pasted_image(bit, {"image_data": "data:text/plain;base64,aGVsbG8="})
        bit.save()

        bit.refresh_from_db()
        assert not bit.image
