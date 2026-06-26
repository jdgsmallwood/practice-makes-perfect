"""Unit tests for practice session view logic."""
import pytest
from django.test import Client
from django.urls import reverse

from pieces.models import TrickyBit
from tests.factories import PieceFactory, TrickyBitFactory


@pytest.mark.django_db
class TestRateBitAchievedTempo:
    def _rate(self, client, bit, rating, achieved_tempo=""):
        return client.post(
            reverse("practice:rate"),
            {"bit_id": bit.pk, "rating": rating, "achieved_tempo": achieved_tempo},
        )

    def test_updates_current_tempo_when_provided(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=80)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="95")
        bit.refresh_from_db()
        assert bit.current_tempo == 95

    def test_leaves_current_tempo_unchanged_when_blank(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=80)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="")
        bit.refresh_from_db()
        assert bit.current_tempo == 80

    def test_ignores_tempo_below_minimum(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=80)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="10")
        bit.refresh_from_db()
        assert bit.current_tempo == 80

    def test_ignores_tempo_above_maximum(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=80)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="999")
        bit.refresh_from_db()
        assert bit.current_tempo == 80

    def test_ignores_non_numeric_tempo(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=80)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="fast")
        bit.refresh_from_db()
        assert bit.current_tempo == 80

    def test_still_updates_sm2_when_tempo_provided(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=80)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="95")
        bit.refresh_from_db()
        assert bit.repetitions == 1
        assert bit.current_tempo == 95

    def test_can_set_tempo_on_bit_with_no_previous_tempo(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), current_tempo=None)
        self._rate(logged_in_client, bit, rating=3, achieved_tempo="72")
        bit.refresh_from_db()
        assert bit.current_tempo == 72


@pytest.mark.django_db
class TestPracticeSessionKeySignature:
    def test_session_shows_key_signature_chip(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), key_signature="G")
        resp = logged_in_client.get(reverse("practice:session"))
        assert resp.status_code == 200
        assert b"Key:" in resp.content

    def test_session_shows_key_notation_toggle(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), key_signature="Bb")
        resp = logged_in_client.get(reverse("practice:session"))
        assert resp.status_code == 200
        assert b"key signature" in resp.content.lower()

    def test_session_no_key_signature_hides_chip(self, logged_in_client):
        bit = TrickyBitFactory(piece=PieceFactory(is_active=True), key_signature="")
        resp = logged_in_client.get(reverse("practice:session"))
        assert resp.status_code == 200
        assert b"Key:" not in resp.content
