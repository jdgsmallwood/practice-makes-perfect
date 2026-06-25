from datetime import date, timedelta

import pytest

from pieces.models import TrickyBit


class TestTrickyBitIsDue:
    def test_never_reviewed_is_due(self):
        bit = TrickyBit(next_review_at=None)
        assert bit.is_due() is True

    def test_due_today_is_due(self):
        bit = TrickyBit(next_review_at=date.today())
        assert bit.is_due() is True

    def test_yesterday_is_due(self):
        bit = TrickyBit(next_review_at=date.today() - timedelta(days=1))
        assert bit.is_due() is True

    def test_tomorrow_is_not_due(self):
        bit = TrickyBit(next_review_at=date.today() + timedelta(days=1))
        assert bit.is_due() is False

    def test_far_future_is_not_due(self):
        bit = TrickyBit(next_review_at=date.today() + timedelta(days=30))
        assert bit.is_due() is False


class TestTrickyBitTagList:
    def test_empty_string_returns_empty_list(self):
        assert TrickyBit(tags="").tag_list() == []

    def test_single_tag(self):
        assert TrickyBit(tags="legato").tag_list() == ["legato"]

    def test_multiple_comma_separated_tags(self):
        assert TrickyBit(tags="legato,thirds,high-register").tag_list() == [
            "legato", "thirds", "high-register"
        ]

    def test_strips_surrounding_whitespace(self):
        assert TrickyBit(tags=" legato , thirds ").tag_list() == ["legato", "thirds"]

    def test_ignores_empty_segments(self):
        assert TrickyBit(tags="legato,,thirds").tag_list() == ["legato", "thirds"]

    def test_ignores_whitespace_only_segments(self):
        assert TrickyBit(tags="legato, ,thirds").tag_list() == ["legato", "thirds"]


class TestTrickyBitKeySignature:
    def test_defaults_to_empty(self):
        assert TrickyBit().key_signature == ""

    def test_empty_is_falsy(self):
        assert not TrickyBit().key_signature

    def test_get_display_for_major_key(self):
        bit = TrickyBit(key_signature="G")
        assert bit.get_key_signature_display() == "G major (1♯)"

    def test_get_display_for_flat_key(self):
        bit = TrickyBit(key_signature="Bb")
        assert bit.get_key_signature_display() == "B♭ major (2♭)"

    def test_get_display_for_minor_key(self):
        bit = TrickyBit(key_signature="Am")
        assert bit.get_key_signature_display() == "A minor"

    def test_get_display_for_sharp_minor_key(self):
        bit = TrickyBit(key_signature="F#m")
        assert bit.get_key_signature_display() == "F♯ minor (3♯)"
