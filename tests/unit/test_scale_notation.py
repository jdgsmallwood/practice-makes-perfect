"""Unit tests for instrument-aware scale notation."""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Instrument, Profile
from scales.models import ScalePractice, ScaleType


@pytest.fixture
def scale_type(db):
    return ScaleType.objects.create(
        slug="major-test",
        name="Major",
        category="Diatonic",
        intervals=[0, 2, 4, 5, 7, 9, 11],
    )


def _make_client(db, midi_low=None):
    """Return (client, profile) logged in as a fresh user with instrument midi_low."""
    user = User.objects.create_user(f"user_{midi_low}", password="test")
    if midi_low is not None:
        instrument = Instrument.objects.create(
            slug=f"inst-{midi_low}", name="Test", midi_low=midi_low, midi_high=96
        )
        profile = Profile.objects.create(user=user, name="P", instrument=instrument)
    else:
        profile = Profile.objects.create(user=user, name="P")
    c = Client()
    c.force_login(user)
    session = c.session
    session["active_profile_id"] = profile.pk
    session.save()
    return c, profile


@pytest.mark.django_db
class TestScaleDetailMidiLow:
    def _sp(self, profile, scale_type, root=0):
        return ScalePractice.objects.create(
            profile=profile, scale_type=scale_type, root=root, enabled=True
        )

    def test_instrument_midi_low_injected(self, db, scale_type):
        client, profile = _make_client(db, midi_low=54)
        resp = client.get(reverse("scales:detail", args=[self._sp(profile, scale_type).pk]))
        assert resp.status_code == 200
        assert b", 54)" in resp.content

    def test_no_instrument_defaults_to_60(self, db, scale_type):
        client, profile = _make_client(db, midi_low=None)
        resp = client.get(reverse("scales:detail", args=[self._sp(profile, scale_type).pk]))
        assert resp.status_code == 200
        assert b", 60)" in resp.content

    def test_different_midi_low_injected(self, db, scale_type):
        client, profile = _make_client(db, midi_low=48)
        resp = client.get(reverse("scales:detail", args=[self._sp(profile, scale_type).pk]))
        assert b", 48)" in resp.content


@pytest.mark.django_db
class TestScaleRotationMidiLow:
    def test_instrument_midi_low_in_rotation(self, db, scale_type):
        client, profile = _make_client(db, midi_low=54)
        ScalePractice.objects.create(
            profile=profile, scale_type=scale_type, root=0, enabled=True
        )
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.status_code == 200
        assert b", 54)" in resp.content
