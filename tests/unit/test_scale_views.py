"""Unit tests for scales view logic."""
import pytest
from django.urls import reverse

from scales.models import ScaleLog
from tests.factories import ScalePracticeFactory, ScaleTypeFactory


@pytest.mark.django_db
class TestLogFromDetail:
    def _log(self, client, sp, achieved_tempo=""):
        return client.post(
            reverse("scales:log_from_detail", args=[sp.pk]),
            {"achieved_tempo": achieved_tempo},
        )

    def test_updates_current_and_fastest_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=80, fastest_tempo=80)
        self._log(client, sp, "95")
        sp.refresh_from_db()
        assert sp.current_tempo == 95
        assert sp.fastest_tempo == 95

    def test_updates_fastest_when_higher_than_existing(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=100, fastest_tempo=120)
        self._log(client, sp, "130")
        sp.refresh_from_db()
        assert sp.fastest_tempo == 130

    def test_does_not_lower_fastest_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=100, fastest_tempo=120)
        self._log(client, sp, "90")
        sp.refresh_from_db()
        assert sp.fastest_tempo == 120
        assert sp.current_tempo == 90

    def test_creates_scale_log_with_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=80)
        self._log(client, sp, "95")
        log = ScaleLog.objects.get(scale_practice=sp)
        assert log.achieved_tempo == 95

    def test_creates_scale_log_with_no_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=80)
        self._log(client, sp, "")
        log = ScaleLog.objects.get(scale_practice=sp)
        assert log.achieved_tempo is None
        sp.refresh_from_db()
        assert sp.current_tempo == 80  # unchanged

    def test_ignores_out_of_range_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=80)
        self._log(client, sp, "10")  # below minimum
        sp.refresh_from_db()
        assert sp.current_tempo == 80

    def test_get_redirects_without_logging(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile)
        resp = client.get(reverse("scales:log_from_detail", args=[sp.pk]))
        assert resp.status_code == 302
        assert ScaleLog.objects.filter(scale_practice=sp).count() == 0

    def test_redirects_to_detail_after_post(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=80)
        resp = self._log(client, sp, "90")
        assert resp.status_code == 302
        assert resp["Location"] == reverse("scales:detail", args=[sp.pk])

    def test_detail_page_renders_with_metronome_and_ladder(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, current_tempo=80, desired_tempo=120)
        resp = client.get(reverse("scales:detail", args=[sp.pk]))
        assert resp.status_code == 200
        assert b"metronome" in resp.content.lower()
        assert b"ladder" in resp.content.lower()
        assert b"Got it" in resp.content
