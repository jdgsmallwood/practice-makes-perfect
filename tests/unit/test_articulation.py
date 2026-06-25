"""Unit tests for the articulation practice section."""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Instrument, Profile
from articulation.models import ArticulationLog, ArticulationSession
from articulation.utils import EXERCISES, queue_for_track


@pytest.fixture
def art_client(db):
    """Test client authenticated as a user with an active flute profile."""
    user = User.objects.create_user("artuser", password="test")
    flute, _ = Instrument.objects.get_or_create(
        slug="flute", defaults={"name": "Flute", "midi_low": 60, "midi_high": 96}
    )
    profile = Profile.objects.create(user=user, name="Art Flutist", instrument=flute)
    c = Client()
    c.force_login(user)
    session = c.session
    session["active_profile_id"] = profile.pk
    session.save()
    return c, profile


# --- Utils ---

class TestUtils:
    def test_single_queue_has_5_exercises(self):
        q = queue_for_track("single")
        assert len(q) == 5
        assert q[0] == "ST_1"
        assert q[-1] == "ST_5"

    def test_double_queue_has_4_exercises(self):
        q = queue_for_track("double")
        assert len(q) == 4
        assert q[0] == "DT_1"
        assert q[-1] == "DT_4"

    def test_full_queue_has_9_exercises_in_order(self):
        q = queue_for_track("full")
        assert len(q) == 9
        assert q[:5] == queue_for_track("single")
        assert q[5:] == queue_for_track("double")

    def test_queue_for_track_returns_fresh_list(self):
        q1 = queue_for_track("single")
        q2 = queue_for_track("single")
        q1.pop()
        assert len(q2) == 5

    def test_all_exercises_have_required_fields(self):
        required = {"id", "name", "track", "cue", "bpm_default", "bpm_label", "subdivision", "rating_question"}
        for ex_id, ex in EXERCISES.items():
            assert not (required - ex.keys()), f"{ex_id} missing fields"

    def test_bpm_defaults_are_positive_integers(self):
        for ex_id, ex in EXERCISES.items():
            assert isinstance(ex["bpm_default"], int) and ex["bpm_default"] > 0, ex_id

    def test_subdivisions_are_valid(self):
        for ex_id, ex in EXERCISES.items():
            assert ex["subdivision"] in (1, 2, 4), ex_id

    def test_exercise_ids_match_dict_keys(self):
        for ex_id, ex in EXERCISES.items():
            assert ex["id"] == ex_id


# --- Home view ---

@pytest.mark.django_db
class TestHomeView:
    def test_get_returns_200(self, art_client):
        client, _ = art_client
        resp = client.get(reverse("articulation:home"))
        assert resp.status_code == 200

    def test_get_requires_login(self, db):
        resp = Client().get(reverse("articulation:home"))
        assert resp.status_code == 302
        assert "/login/" in resp["Location"]

    def test_post_invalid_track_redirects_home(self, art_client):
        client, _ = art_client
        resp = client.post(reverse("articulation:home"), {"track": "bogus"})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("articulation:home")

    def test_post_valid_track_creates_session_and_redirects(self, art_client):
        client, profile = art_client
        resp = client.post(reverse("articulation:home"), {"track": "single"})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("articulation:session")
        assert ArticulationSession.objects.filter(profile=profile, track="single").exists()

    def test_post_stores_queue_in_django_session(self, art_client):
        client, _ = art_client
        client.post(reverse("articulation:home"), {"track": "double"})
        art = client.session["art_session"]
        assert art["queue"] == ["DT_1", "DT_2", "DT_3", "DT_4"]
        assert art["total"] == 4

    def test_post_full_track_stores_9_exercise_queue(self, art_client):
        client, _ = art_client
        client.post(reverse("articulation:home"), {"track": "full"})
        art = client.session["art_session"]
        assert art["total"] == 9


# --- Session view ---

@pytest.mark.django_db
class TestSessionView:
    def test_no_active_session_redirects_home(self, art_client):
        client, _ = art_client
        resp = client.get(reverse("articulation:session"))
        assert resp.status_code == 302
        assert resp["Location"] == reverse("articulation:home")

    def test_shows_first_exercise(self, art_client):
        client, _ = art_client
        client.post(reverse("articulation:home"), {"track": "single"})
        resp = client.get(reverse("articulation:session"))
        assert resp.status_code == 200
        assert b"Air Only" in resp.content

    def test_progress_counts_correctly(self, art_client):
        client, _ = art_client
        client.post(reverse("articulation:home"), {"track": "double"})
        resp = client.get(reverse("articulation:session"))
        assert resp.context["remaining"] == 4
        assert resp.context["total"] == 4
        assert resp.context["pct"] == 25  # (4-4+1)/4 * 100 = 25%


# --- Log exercise view ---

@pytest.mark.django_db
class TestLogExerciseView:
    def _start(self, client, track="single"):
        client.post(reverse("articulation:home"), {"track": track})
        return client.session["art_session"]

    def test_get_redirects(self, art_client):
        client, _ = art_client
        resp = client.get(reverse("articulation:log_exercise"))
        assert resp.status_code == 302

    def test_valid_rating_creates_log(self, art_client):
        client, profile = art_client
        art = self._start(client)
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])
        client.post(reverse("articulation:log_exercise"), {
            "session_id": session_obj.pk,
            "exercise_id": "ST_1",
            "rating": 4,
        })
        assert ArticulationLog.objects.filter(
            session=session_obj, exercise_id="ST_1", rating=4
        ).exists()

    def test_rating_advances_queue(self, art_client):
        client, _ = art_client
        art = self._start(client)
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])
        client.post(reverse("articulation:log_exercise"), {
            "session_id": session_obj.pk, "exercise_id": "ST_1", "rating": 3,
        })
        art_after = client.session["art_session"]
        assert art_after["queue"][0] == "ST_2"
        assert len(art_after["queue"]) == 4

    def test_invalid_exercise_id_does_not_log(self, art_client):
        client, _ = art_client
        art = self._start(client)
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])
        client.post(reverse("articulation:log_exercise"), {
            "session_id": session_obj.pk, "exercise_id": "INVALID", "rating": 3,
        })
        assert ArticulationLog.objects.filter(session=session_obj).count() == 0

    def test_rating_out_of_range_does_not_log(self, art_client):
        client, _ = art_client
        art = self._start(client)
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])
        client.post(reverse("articulation:log_exercise"), {
            "session_id": session_obj.pk, "exercise_id": "ST_1", "rating": 99,
        })
        assert ArticulationLog.objects.filter(session=session_obj).count() == 0

    def test_last_exercise_marks_complete_and_redirects(self, art_client):
        client, _ = art_client
        self._start(client, track="double")
        art = client.session["art_session"]
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])

        for ex_id in ["DT_1", "DT_2", "DT_3"]:
            client.post(reverse("articulation:log_exercise"), {
                "session_id": session_obj.pk, "exercise_id": ex_id, "rating": 4,
            })

        resp = client.post(reverse("articulation:log_exercise"), {
            "session_id": session_obj.pk, "exercise_id": "DT_4", "rating": 4,
        })
        assert resp["Location"] == reverse("articulation:complete")
        session_obj.refresh_from_db()
        assert session_obj.completed_at is not None


# --- Skip view ---

@pytest.mark.django_db
class TestSkipView:
    def _start(self, client, track="single"):
        client.post(reverse("articulation:home"), {"track": track})
        return client.session["art_session"]

    def test_skip_defers_exercise_to_end(self, art_client):
        client, _ = art_client
        art = self._start(client)
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])

        client.post(reverse("articulation:skip"), {"session_id": session_obj.pk})

        art_after = client.session["art_session"]
        assert art_after["queue"][0] == "ST_2"
        assert art_after["queue"][-1] == "ST_1"

    def test_skip_does_not_create_log(self, art_client):
        client, _ = art_client
        art = self._start(client)
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])

        client.post(reverse("articulation:skip"), {"session_id": session_obj.pk})

        assert ArticulationLog.objects.filter(session=session_obj).count() == 0

    def test_skip_single_item_queue_unchanged(self, art_client):
        client, _ = art_client
        self._start(client)
        art = client.session["art_session"]
        # Manually drain to one exercise
        s = client.session
        s["art_session"]["queue"] = ["ST_5"]
        s.save()

        session_obj = ArticulationSession.objects.get(pk=art["session_id"])
        client.post(reverse("articulation:skip"), {"session_id": session_obj.pk})

        art_after = client.session["art_session"]
        assert art_after["queue"] == ["ST_5"]


# --- Complete view ---

@pytest.mark.django_db
class TestCompleteView:
    def test_complete_page_loads_empty(self, art_client):
        client, _ = art_client
        resp = client.get(reverse("articulation:complete"))
        assert resp.status_code == 200

    def test_complete_shows_avg_rating(self, art_client):
        client, _ = art_client
        client.post(reverse("articulation:home"), {"track": "double"})
        art = client.session["art_session"]
        session_obj = ArticulationSession.objects.get(pk=art["session_id"])

        for ex_id in ["DT_1", "DT_2", "DT_3", "DT_4"]:
            client.post(reverse("articulation:log_exercise"), {
                "session_id": session_obj.pk, "exercise_id": ex_id, "rating": 4,
            })

        resp = client.get(reverse("articulation:complete"))
        assert resp.context["avg_rating"] == 4.0

    def test_complete_clears_art_session(self, art_client):
        client, _ = art_client
        client.post(reverse("articulation:home"), {"track": "double"})
        client.get(reverse("articulation:complete"))
        assert "art_session" not in client.session
