import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import Instrument, Profile
from accounts.utils import SESSION_KEY as PROFILE_SESSION_KEY
from planner.models import PracticeSession
from transitions.models import TransitionLog, TransitionPractice, TransitionSession
from transitions.utils import DRILL_ORDER, DRILLS, build_session_queue, normalize_pair, selectable_notes


@pytest.fixture
def transition_client(db):
    user = User.objects.create_user("transitionuser", password="test")
    flute, _ = Instrument.objects.get_or_create(
        slug="flute",
        defaults={"name": "Flute", "midi_low": 60, "midi_high": 96},
    )
    profile = Profile.objects.create(user=user, name="Transition Flutist", instrument=flute)
    client = Client()
    client.force_login(user)
    session = client.session
    session[PROFILE_SESSION_KEY] = profile.pk
    session.save()
    return client, profile


def make_transition(profile, low, high, status=TransitionPractice.STATUS_ACTIVE, position=1):
    return TransitionPractice.objects.create(
        profile=profile,
        note_low=low,
        note_high=high,
        status=status,
        position=position,
    )


class TestTransitionUtils:
    def test_build_session_queue_length_and_ordering(self, db):
        user = User.objects.create_user("queueuser")
        profile = Profile.objects.create(user=user, name="Queue")
        first = make_transition(profile, 61, 62, position=1)
        second = make_transition(profile, 72, 74, position=2)

        queue = build_session_queue([first, second])

        assert len(queue) == 6
        assert queue[:3] == [
            {"transition_id": first.pk, "exercise_id": "SLUR"},
            {"transition_id": first.pk, "exercise_id": "APPOG"},
            {"transition_id": first.pk, "exercise_id": "ECON"},
        ]
        assert queue[3]["transition_id"] == second.pk

    def test_selectable_notes_are_octave_aware_and_in_range(self):
        notes = selectable_notes(61, 74)
        assert notes[0] == (61, "C#4")
        assert notes[-1] == (74, "D5")
        assert (73, "C#5") in notes

    def test_normalize_pair_sorts(self):
        assert normalize_pair("74", "61") == (61, 74)

    def test_drill_order_integrity(self):
        assert DRILL_ORDER == ["SLUR", "APPOG", "ECON"]
        assert set(DRILL_ORDER) == set(DRILLS.keys())
        assert DRILLS["ECON"]["prompts_tempo"] is True


@pytest.mark.django_db
class TestTransitionModels:
    def test_str_uses_octave_aware_names(self, transition_client):
        _, profile = transition_client
        transition = make_transition(profile, 61, 62)
        assert str(transition) == "C#4 -> D4"

    def test_interval_semitones(self, transition_client):
        _, profile = transition_client
        transition = make_transition(profile, 73, 74)
        assert transition.interval_semitones == 1

    def test_octave_aware_transitions_are_distinct(self, transition_client):
        _, profile = transition_client
        make_transition(profile, 60, 72)
        make_transition(profile, 72, 84, position=2)
        assert TransitionPractice.objects.filter(profile=profile).count() == 2

    def test_duplicate_same_octave_pair_rejected(self, transition_client):
        _, profile = transition_client
        make_transition(profile, 61, 62)
        with pytest.raises(IntegrityError):
            make_transition(profile, 61, 62, position=2)


@pytest.mark.django_db
class TestTransitionViews:
    def test_home_loads(self, transition_client):
        client, _ = transition_client
        resp = client.get(reverse("transitions:home"))
        assert resp.status_code == 200
        assert b"Transitions" in resp.content

    def test_add_valid_transition_becomes_active(self, transition_client):
        client, profile = transition_client
        resp = client.post(reverse("transitions:add_transition"), {"note_a": "61", "note_b": "62"})
        assert resp.status_code == 302
        transition = TransitionPractice.objects.get(profile=profile, note_low=61, note_high=62)
        assert transition.status == TransitionPractice.STATUS_ACTIVE

    def test_duplicate_rejected(self, transition_client):
        client, profile = transition_client
        make_transition(profile, 61, 62)
        client.post(reverse("transitions:add_transition"), {"note_a": "62", "note_b": "61"})
        assert TransitionPractice.objects.filter(profile=profile, note_low=61, note_high=62).count() == 1

    def test_out_of_range_rejected(self, transition_client):
        client, profile = transition_client
        client.post(reverse("transitions:add_transition"), {"note_a": "59", "note_b": "62"})
        assert TransitionPractice.objects.filter(profile=profile).count() == 0

    def test_same_note_rejected(self, transition_client):
        client, profile = transition_client
        client.post(reverse("transitions:add_transition"), {"note_a": "61", "note_b": "61"})
        assert TransitionPractice.objects.filter(profile=profile).count() == 0

    def test_fourth_transition_goes_to_queue(self, transition_client):
        client, profile = transition_client
        for low, high in [(60, 61), (62, 63), (64, 65), (66, 67)]:
            client.post(reverse("transitions:add_transition"), {"note_a": str(low), "note_b": str(high)})

        assert TransitionPractice.objects.filter(profile=profile, status=TransitionPractice.STATUS_ACTIVE).count() == 3
        queued = TransitionPractice.objects.get(profile=profile, status=TransitionPractice.STATUS_QUEUED)
        assert (queued.note_low, queued.note_high) == (66, 67)

    def test_retire_promotes_next_queued(self, transition_client):
        client, profile = transition_client
        active = make_transition(profile, 60, 61, position=1)
        make_transition(profile, 62, 63, position=2)
        queued = make_transition(profile, 64, 65, status=TransitionPractice.STATUS_QUEUED, position=1)

        client.post(reverse("transitions:retire_transition"), {"transition_id": active.pk})

        active.refresh_from_db()
        queued.refresh_from_db()
        assert active.status == TransitionPractice.STATUS_RETIRED
        assert queued.status == TransitionPractice.STATUS_ACTIVE

    def test_start_session_builds_queue(self, transition_client):
        client, profile = transition_client
        make_transition(profile, 61, 62)
        make_transition(profile, 73, 74, position=2)

        resp = client.post(reverse("transitions:home"))

        assert resp["Location"] == reverse("transitions:session")
        state = client.session["transition_session"]
        assert state["total"] == 6
        assert state["queue"][0]["exercise_id"] == "SLUR"

    def test_session_page_renders_current_transition(self, transition_client):
        client, profile = transition_client
        transition = make_transition(profile, 61, 62)
        session_obj = TransitionSession.objects.create(profile=profile, date="2026-06-29")
        session = client.session
        session["transition_session"] = {
            "session_id": session_obj.pk,
            "queue": [{"transition_id": transition.pk, "exercise_id": "SLUR"}],
            "total": 1,
        }
        session.save()

        resp = client.get(reverse("transitions:session"))

        assert resp.status_code == 200
        assert b"C#4" in resp.content
        assert b"D4" in resp.content
        assert b"Slow Slur" in resp.content

    def test_log_transition_creates_log_advances_and_updates_fastest(self, transition_client):
        client, profile = transition_client
        transition = make_transition(profile, 61, 62)
        session_obj = TransitionSession.objects.create(profile=profile, date="2026-06-29")
        session = client.session
        session["transition_session"] = {
            "session_id": session_obj.pk,
            "queue": [{"transition_id": transition.pk, "exercise_id": "ECON"}],
            "total": 1,
        }
        session.save()

        resp = client.post(reverse("transitions:log_transition"), {
            "session_id": session_obj.pk,
            "transition_id": transition.pk,
            "exercise_id": "ECON",
            "rating": "4",
            "achieved_tempo": "92",
        })

        assert resp["Location"] == reverse("transitions:complete")
        assert TransitionLog.objects.filter(
            session=session_obj,
            transition_practice=transition,
            exercise_id="ECON",
            rating=4,
            achieved_tempo=92,
        ).exists()
        transition.refresh_from_db()
        assert transition.current_tempo == 92
        assert transition.fastest_tempo == 92
        session_obj.refresh_from_db()
        assert session_obj.completed_at is not None

    def test_complete_redirects_to_planner_section_done(self, transition_client):
        client, profile = transition_client
        planner_session = PracticeSession.objects.create(
            profile=profile,
            total_minutes_planned=10,
            categories_json=["transitions"],
            sections_json=[{
                "category": "transitions",
                "label": "Transitions",
                "minutes": 5,
                "start_url": reverse("transitions:home"),
                "item_count": 1,
                "completed_at": None,
            }],
        )
        session = client.session
        session["planner_state"] = {
            "session_id": planner_session.pk,
            "total_minutes": 10,
            "sections": planner_session.sections_json,
        }
        session.save()

        resp = client.get(reverse("transitions:complete"))

        assert resp.status_code == 302
        assert resp["Location"] == reverse("planner:section_done")
