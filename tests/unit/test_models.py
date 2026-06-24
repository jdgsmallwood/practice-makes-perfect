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
