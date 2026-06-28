"""Unit tests for scales view logic."""
import pytest
from django.urls import reverse

from scales.models import ScaleLog, ScalePractice
from scales.views import (
    DEFAULT_SCALE_WEIGHTS,
    _compute_rotation_weights,
    get_scale_weights,
)
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


@pytest.mark.django_db
class TestRotationLog:
    def _post(self, client, sp, achieved_tempo="", rating=""):
        session = client.session
        session["scales_rotation_order"] = [sp.pk]
        session.save()
        return client.post(
            reverse("scales:rotation_log"),
            {"sp_id": sp.pk, "achieved_tempo": achieved_tempo, "rating": rating},
        )

    def test_stores_rating_in_log(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, current_tempo=80)
        self._post(client, sp, achieved_tempo="88", rating="3")
        log = ScaleLog.objects.get(scale_practice=sp)
        assert log.rating == 3

    def test_rating_without_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True)
        self._post(client, sp, rating="2")
        log = ScaleLog.objects.get(scale_practice=sp)
        assert log.rating == 2
        assert log.achieved_tempo is None

    def test_no_rating_creates_log_without_rating(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True)
        self._post(client, sp, achieved_tempo="80")
        log = ScaleLog.objects.get(scale_practice=sp)
        assert log.rating is None

    def test_invalid_rating_ignored(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True)
        self._post(client, sp, rating="99")
        log = ScaleLog.objects.get(scale_practice=sp)
        assert log.rating is None

    def test_rotation_session_shows_rating_buttons(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, current_tempo=80, desired_tempo=120)
        session = client.session
        session["scales_rotation_order"] = [sp.pk]
        session.save()
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.status_code == 200
        assert b"Again" in resp.content
        assert b"Good" in resp.content


@pytest.mark.django_db
class TestPracticeRedirect:
    def test_redirects_to_rotation_session(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        resp = client.get(reverse("scales:practice"))
        assert resp.status_code == 302
        assert resp["Location"] == reverse("scales:rotation_session")


@pytest.mark.django_db
class TestBulkSetTempo:
    def test_sets_desired_tempo_on_all_enabled(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp1 = ScalePracticeFactory(profile=profile, enabled=True, desired_tempo=80)
        sp2 = ScalePracticeFactory(profile=profile, enabled=True, desired_tempo=100)
        client.post(reverse("scales:bulk_set_tempo"), {"desired_tempo": "120"})
        sp1.refresh_from_db()
        sp2.refresh_from_db()
        assert sp1.desired_tempo == 120
        assert sp2.desired_tempo == 120

    def test_does_not_affect_disabled_scales(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=False, desired_tempo=80)
        client.post(reverse("scales:bulk_set_tempo"), {"desired_tempo": "120"})
        sp.refresh_from_db()
        assert sp.desired_tempo == 80

    def test_ignores_out_of_range_tempo(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, desired_tempo=80)
        client.post(reverse("scales:bulk_set_tempo"), {"desired_tempo": "10"})
        sp.refresh_from_db()
        assert sp.desired_tempo == 80

    def test_redirects_to_settings(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        resp = client.post(reverse("scales:bulk_set_tempo"), {"desired_tempo": "120"})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("scales:settings")


@pytest.mark.django_db
class TestTechniqueIndex:
    def test_rotation_session_passes_technique_index(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=5)
        session = client.session
        session["scales_rotation_order"] = [sp.pk]
        session["scales_technique_index"] = 3
        session.save()
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.status_code == 200
        # technique_index=3 → tip index 3 → long-short dotted
        assert b"3" in resp.content

    def test_low_repetitions_forces_even_quavers(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=1)
        session = client.session
        session["scales_rotation_order"] = [sp.pk]
        session["scales_technique_index"] = 5
        session.save()
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.status_code == 200
        # repetitions < 2 forces index 0 regardless of session counter
        assert b"tips[0 % tips.length]" in resp.content

    def test_rotation_log_increments_technique_index(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True)
        session = client.session
        session["scales_rotation_order"] = [sp.pk]
        session["scales_technique_index"] = 2
        session.save()
        client.post(
            reverse("scales:rotation_log"),
            {"sp_id": sp.pk, "achieved_tempo": "80", "rating": "3"},
        )
        assert client.session.get("scales_technique_index") == 3


@pytest.mark.django_db
class TestSettingsStaleness:
    def test_settings_page_shows_active_scales_summary(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        ScalePracticeFactory(profile=profile, enabled=True, current_tempo=80, desired_tempo=120)
        resp = client.get(reverse("scales:settings"))
        assert resp.status_code == 200
        assert b"What I'm working on" in resp.content

    def test_settings_page_no_summary_when_nothing_enabled(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        resp = client.get(reverse("scales:settings"))
        assert resp.status_code == 200
        assert b"What I'm working on" not in resp.content

    def test_bulk_tempo_form_shown_when_scales_enabled(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        ScalePracticeFactory(profile=profile, enabled=True)
        resp = client.get(reverse("scales:settings"))
        assert b"Set goal BPM" in resp.content


@pytest.mark.django_db
class TestRotationProgressCounts:
    def test_remaining_counts_distinct_scales_not_queue_length(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp1 = ScalePracticeFactory(profile=profile, enabled=True)
        sp2 = ScalePracticeFactory(profile=profile, enabled=True)
        sp3 = ScalePracticeFactory(profile=profile, enabled=True)
        session = client.session
        # sp1 weighted x3 in the queue, but it's still one distinct scale.
        session["scales_rotation_order"] = [sp1.pk, sp1.pk, sp1.pk, sp2.pk, sp3.pk]
        session.save()
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.context["remaining"] == 3
        assert resp.context["total"] == 3
        assert resp.context["progress_pct"] == 0

    def test_progress_pct_reflects_completed_distinct_scales(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp1 = ScalePracticeFactory(profile=profile, enabled=True)
        sp2 = ScalePracticeFactory(profile=profile, enabled=True)
        sp3 = ScalePracticeFactory(profile=profile, enabled=True)
        session = client.session
        # sp1 fully done (no copies left): 1 of 3 complete -> 33%.
        session["scales_rotation_order"] = [sp2.pk, sp3.pk]
        session.save()
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.context["remaining"] == 2
        assert resp.context["total"] == 3
        assert resp.context["progress_pct"] == 33


@pytest.mark.django_db
class TestRotationUpNext:
    def test_up_next_shown_when_multiple_scales_queued(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp1 = ScalePracticeFactory(profile=profile, enabled=True)
        sp2 = ScalePracticeFactory(profile=profile, enabled=True)
        session = client.session
        session["scales_rotation_order"] = [sp1.pk, sp2.pk]
        session.save()
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.status_code == 200
        assert b"Up next" in resp.content


@pytest.mark.django_db
class TestComputeRotationWeights:
    def test_new_scale_gets_high_weight(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=0,
                                  desired_tempo=120, current_tempo=None)
        weights = _compute_rotation_weights([sp], DEFAULT_SCALE_WEIGHTS)
        assert weights[sp.pk] == 3

    def test_at_goal_with_easy_ratings_gets_weight_1(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=10,
                                  desired_tempo=120, current_tempo=120)
        ScaleLog.objects.create(scale_practice=sp, rating=4)
        ScaleLog.objects.create(scale_practice=sp, rating=4)
        ScaleLog.objects.create(scale_practice=sp, rating=4)
        weights = _compute_rotation_weights([sp], DEFAULT_SCALE_WEIGHTS)
        assert weights[sp.pk] == 1

    def test_struggling_scale_gets_weight_3(self, logged_in_client_with_profile):
        # Goal set but never measured (td=0.8) + all "Again" ratings (sd=1.0)
        # raw = 0.6×0.8 + 0.1×1.0 = 0.58 → weight 3
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=5,
                                  desired_tempo=120, current_tempo=None)
        ScaleLog.objects.create(scale_practice=sp, rating=1)
        ScaleLog.objects.create(scale_practice=sp, rating=1)
        ScaleLog.objects.create(scale_practice=sp, rating=1)
        weights = _compute_rotation_weights([sp], DEFAULT_SCALE_WEIGHTS)
        assert weights[sp.pk] == 3

    def test_no_logs_gets_mid_weight(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=3,
                                  desired_tempo=120, current_tempo=None)
        weights = _compute_rotation_weights([sp], DEFAULT_SCALE_WEIGHTS)
        # desired_tempo set but no current → td=0.8 → raw=0.48 → weight 2
        assert weights[sp.pk] == 2

    def test_no_tempo_no_logs_gets_mid_weight(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=3,
                                  desired_tempo=None, current_tempo=None)
        weights = _compute_rotation_weights([sp], DEFAULT_SCALE_WEIGHTS)
        # td=0.5 → raw≈0.33 → weight 2
        assert weights[sp.pk] == 2

    def test_bottom_quartile_peer_increases_weight(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        scale_type = ScaleTypeFactory()
        # 4 scales, same type, different roots — first one is far behind
        sp_low = ScalePracticeFactory(profile=profile, scale_type=scale_type, root=0,
                                      enabled=True, repetitions=5,
                                      desired_tempo=120, current_tempo=40)
        sp_hi1 = ScalePracticeFactory(profile=profile, scale_type=scale_type, root=1,
                                      enabled=True, repetitions=5,
                                      desired_tempo=120, current_tempo=115)
        sp_hi2 = ScalePracticeFactory(profile=profile, scale_type=scale_type, root=2,
                                      enabled=True, repetitions=5,
                                      desired_tempo=120, current_tempo=118)
        sp_hi3 = ScalePracticeFactory(profile=profile, scale_type=scale_type, root=3,
                                      enabled=True, repetitions=5,
                                      desired_tempo=120, current_tempo=119)
        # Give all "Easy" ratings so smoothness doesn't interfere
        for sp in [sp_low, sp_hi1, sp_hi2, sp_hi3]:
            for _ in range(3):
                ScaleLog.objects.create(scale_practice=sp, rating=4)
        weights = _compute_rotation_weights([sp_low, sp_hi1, sp_hi2, sp_hi3], DEFAULT_SCALE_WEIGHTS)
        assert weights[sp_low.pk] > weights[sp_hi1.pk]

    def test_single_scale_no_peer_comparison_crash(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=5,
                                  desired_tempo=120, current_tempo=100)
        weights = _compute_rotation_weights([sp], DEFAULT_SCALE_WEIGHTS)
        assert sp.pk in weights

    def test_empty_list_returns_empty(self, logged_in_client_with_profile):
        weights = _compute_rotation_weights([], DEFAULT_SCALE_WEIGHTS)
        assert weights == {}

    def test_rotation_log_increments_repetitions(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=0)
        session = client.session
        session["scales_rotation_order"] = [sp.pk]
        session.save()
        client.post(
            reverse("scales:rotation_log"),
            {"sp_id": sp.pk, "achieved_tempo": "80", "rating": "3"},
        )
        sp.refresh_from_db()
        assert sp.repetitions == 1

    def test_weighted_queue_contains_repeated_pks_for_struggling_scale(
        self, logged_in_client_with_profile
    ):
        client, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=0,
                                  desired_tempo=120, current_tempo=None)
        resp = client.get(reverse("scales:rotation_session"))
        assert resp.status_code == 200
        order = client.session.get("scales_rotation_order", [])
        assert order.count(sp.pk) > 1


@pytest.mark.django_db
class TestGetScaleWeights:
    def test_none_profile_returns_defaults(self):
        assert get_scale_weights(None) == DEFAULT_SCALE_WEIGHTS

    def test_empty_dict_returns_defaults(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        assert get_scale_weights(profile) == DEFAULT_SCALE_WEIGHTS

    def test_merges_partial_over_defaults(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        profile.scale_weights = {"tempo": 9}
        profile.save(update_fields=["scale_weights"])
        w = get_scale_weights(profile)
        assert w["tempo"] == 9
        assert w["peer"] == DEFAULT_SCALE_WEIGHTS["peer"]

    def test_clamps_out_of_range(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        profile.scale_weights = {"tempo": 99, "peer": -4}
        profile.save(update_fields=["scale_weights"])
        w = get_scale_weights(profile)
        assert w["tempo"] == 10
        assert w["peer"] == 0

    def test_ignores_junk_values(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        profile.scale_weights = {"tempo": "abc", "bogus": 5}
        profile.save(update_fields=["scale_weights"])
        w = get_scale_weights(profile)
        assert w["tempo"] == DEFAULT_SCALE_WEIGHTS["tempo"]
        assert "bogus" not in w


@pytest.mark.django_db
class TestCustomWeights:
    def test_tempo_heavy_pushes_slow_smooth_scale_up(self, logged_in_client_with_profile):
        # A slow scale (big tempo gap) that's rated Easy (very smooth).
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=5,
                                  desired_tempo=120, current_tempo=50)
        for _ in range(3):
            ScaleLog.objects.create(scale_practice=sp, rating=4)
        tempo_heavy = {"tempo": 10, "peer": 0, "smoothness": 0, "new_boost": 0}
        fluency_heavy = {"tempo": 0, "peer": 0, "smoothness": 10, "new_boost": 0}
        w_tempo = _compute_rotation_weights([sp], tempo_heavy)
        w_fluency = _compute_rotation_weights([sp], fluency_heavy)
        assert w_tempo[sp.pk] > w_fluency[sp.pk]

    def test_fluency_heavy_pushes_rough_fast_scale_up(self, logged_in_client_with_profile):
        # A fast scale (at goal) that's rated Again (very rough).
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=5,
                                  desired_tempo=120, current_tempo=120)
        for _ in range(3):
            ScaleLog.objects.create(scale_practice=sp, rating=1)
        tempo_heavy = {"tempo": 10, "peer": 0, "smoothness": 0, "new_boost": 0}
        fluency_heavy = {"tempo": 0, "peer": 0, "smoothness": 10, "new_boost": 0}
        w_tempo = _compute_rotation_weights([sp], tempo_heavy)
        w_fluency = _compute_rotation_weights([sp], fluency_heavy)
        assert w_fluency[sp.pk] > w_tempo[sp.pk]

    def test_zero_signal_weights_fall_back(self, logged_in_client_with_profile):
        _, profile = logged_in_client_with_profile
        sp = ScalePracticeFactory(profile=profile, enabled=True, repetitions=5,
                                  desired_tempo=120, current_tempo=50)
        zeroed = {"tempo": 0, "peer": 0, "smoothness": 0, "new_boost": 0}
        fallback = {"tempo": 6, "peer": 3, "smoothness": 1, "new_boost": 0}
        # Zeroed signal budget falls back to the 6/3/1 default split
        assert _compute_rotation_weights([sp], zeroed) == _compute_rotation_weights([sp], fallback)


@pytest.mark.django_db
class TestSaveScaleWeights:
    def test_persists_clamped_values(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        client.post(reverse("scales:save_weights"),
                    {"tempo": "7", "peer": "2", "new_boost": "9"})
        profile.refresh_from_db()
        assert profile.scale_weights["tempo"] == 7
        assert profile.scale_weights["peer"] == 2
        assert profile.scale_weights["new_boost"] == 9

    def test_smoothness_is_remainder(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        client.post(reverse("scales:save_weights"),
                    {"tempo": "6", "peer": "3", "new_boost": "5"})
        profile.refresh_from_db()
        w = profile.scale_weights
        assert w["tempo"] + w["peer"] + w["smoothness"] == 10
        assert w["smoothness"] == 1

    def test_tempo_plus_peer_capped_at_10(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        client.post(reverse("scales:save_weights"),
                    {"tempo": "8", "peer": "7", "new_boost": "5"})
        profile.refresh_from_db()
        w = profile.scale_weights
        assert w["tempo"] + w["peer"] + w["smoothness"] == 10
        assert w["peer"] == 2  # capped to 10 - tempo
        assert w["smoothness"] == 0

    def test_clears_rotation_order(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        session = client.session
        session["scales_rotation_order"] = [1, 2, 3]
        session.save()
        client.post(reverse("scales:save_weights"),
                    {"tempo": "6", "peer": "3", "new_boost": "5"})
        assert "scales_rotation_order" not in client.session

    def test_redirects_to_settings(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        resp = client.post(reverse("scales:save_weights"),
                           {"tempo": "6", "peer": "3", "new_boost": "5"})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("scales:settings")

    def test_get_is_noop_redirect(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        resp = client.get(reverse("scales:save_weights"))
        assert resp.status_code == 302
        profile.refresh_from_db()
        assert profile.scale_weights == {}

    def test_invalid_values_use_defaults(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        client.post(reverse("scales:save_weights"),
                    {"tempo": "abc", "peer": "", "new_boost": "xyz"})
        profile.refresh_from_db()
        w = profile.scale_weights
        assert w["tempo"] == DEFAULT_SCALE_WEIGHTS["tempo"]
        assert w["tempo"] + w["peer"] + w["smoothness"] == 10


@pytest.mark.django_db
class TestSettingsFocus:
    def test_context_includes_scale_weights(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        ScalePracticeFactory(profile=profile, enabled=True)
        resp = client.get(reverse("scales:settings"))
        assert resp.context["scale_weights"] == DEFAULT_SCALE_WEIGHTS

    def test_active_scales_have_focus_level(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        ScalePracticeFactory(profile=profile, enabled=True, desired_tempo=120, current_tempo=60)
        resp = client.get(reverse("scales:settings"))
        active = resp.context["active_scales"]
        assert active
        assert all(s["focus"] in (1, 2, 3) for s in active)

    def test_focus_panel_rendered_when_scales_enabled(self, logged_in_client_with_profile):
        client, profile = logged_in_client_with_profile
        ScalePracticeFactory(profile=profile, enabled=True)
        resp = client.get(reverse("scales:settings"))
        assert b"Practice focus" in resp.content
