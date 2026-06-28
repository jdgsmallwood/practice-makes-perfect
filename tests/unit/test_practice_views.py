"""Unit tests for practice session view logic."""
import pytest
from django.test import Client
from django.urls import reverse

from pieces.models import TrickyBit
from practice.views import PRACTICE_WEIGHTS, _compute_practice_weights
from tests.factories import PieceFactory, PracticeLogFactory, TrickyBitFactory


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


@pytest.mark.django_db
class TestComputePracticeWeights:
    def test_new_bit_gets_high_weight(self):
        bit = TrickyBitFactory(repetitions=0, desired_tempo=120, current_tempo=None)
        weights = _compute_practice_weights([bit], PRACTICE_WEIGHTS)
        assert weights[bit.pk] == 3

    def test_tempo_deficit_raises_weight_above_at_goal(self):
        # Same ratings; the bit far below its goal tempo outranks the one at goal.
        far = TrickyBitFactory(repetitions=5, desired_tempo=120, current_tempo=40)
        at_goal = TrickyBitFactory(repetitions=5, desired_tempo=120, current_tempo=120)
        for bit in (far, at_goal):
            for _ in range(3):
                PracticeLogFactory(tricky_bit=bit, rating=3)
        weights = _compute_practice_weights([far, at_goal], PRACTICE_WEIGHTS)
        assert weights[far.pk] > weights[at_goal.pk]

    def test_at_goal_with_easy_ratings_gets_low_weight(self):
        bit = TrickyBitFactory(repetitions=10, desired_tempo=120, current_tempo=120)
        for _ in range(3):
            PracticeLogFactory(tricky_bit=bit, rating=4)
        weights = _compute_practice_weights([bit], PRACTICE_WEIGHTS)
        assert weights[bit.pk] == 1

    def test_no_tempo_no_logs_gets_mid_weight(self):
        bit = TrickyBitFactory(repetitions=3, desired_tempo=None, current_tempo=None)
        weights = _compute_practice_weights([bit], PRACTICE_WEIGHTS)
        # td=0.5 neutral, sd=0.5 default → raw=0.35 → weight 2
        assert weights[bit.pk] == 2

    def test_empty_returns_empty(self):
        assert _compute_practice_weights([], PRACTICE_WEIGHTS) == {}
