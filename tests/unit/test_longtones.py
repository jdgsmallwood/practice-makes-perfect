"""Unit tests for the long tones practice section."""
from datetime import date

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Profile
from longtones.models import LongToneLog, LongToneSession
from longtones.utils import (
    FOCUS_CHOICES,
    FOCUS_PROMPTS,
    FOCUS_QUESTION,
    MIDI_NAMES,
    midi_to_hz,
    session_notes_for_date,
)


@pytest.fixture
def lt_client(db):
    """Test client authenticated as a user with an active flute profile."""
    user = User.objects.create_user("ltuser", password="test")
    profile = Profile.objects.create(user=user, name="LT Flutist", instrument="flute")
    c = Client()
    c.force_login(user)
    session = c.session
    session["active_profile_id"] = profile.pk
    session.save()
    return c, profile


# --- Utils ---

class TestUtils:
    def test_session_notes_returns_list_of_ints(self):
        notes = session_notes_for_date(date(2026, 1, 1))
        assert isinstance(notes, list)
        assert all(isinstance(n, int) for n in notes)

    def test_notes_within_flute_range(self):
        for offset in range(12):
            d = date.fromordinal(date(2026, 1, 1).toordinal() + offset)
            notes = session_notes_for_date(d)
            assert all(60 <= n <= 96 for n in notes), f"Out of range on offset {offset}: {notes}"

    def test_notes_spaced_7_semitones(self):
        notes = session_notes_for_date(date(2026, 1, 1))
        for a, b in zip(notes, notes[1:]):
            assert b - a == 7

    def test_session_notes_rotates_daily(self):
        d1 = date(2026, 6, 1)
        d2 = date(2026, 6, 2)
        assert session_notes_for_date(d1) != session_notes_for_date(d2)

    def test_session_notes_defaults_to_today(self):
        notes = session_notes_for_date()
        assert len(notes) > 0

    def test_midi_to_hz_a4_is_440(self):
        assert abs(midi_to_hz(69) - 440.0) < 0.01

    def test_midi_to_hz_a5_is_880(self):
        assert abs(midi_to_hz(81) - 880.0) < 0.01

    def test_midi_names_covers_full_flute_range(self):
        for midi in range(60, 97):
            assert midi in MIDI_NAMES, f"MIDI {midi} missing from MIDI_NAMES"

    def test_focus_choices_prompts_questions_are_consistent(self):
        focus_keys = {k for k, _ in FOCUS_CHOICES}
        assert focus_keys == set(FOCUS_PROMPTS.keys())
        assert focus_keys == set(FOCUS_QUESTION.keys())

    def test_focus_prompts_are_non_empty_strings(self):
        for k, v in FOCUS_PROMPTS.items():
            assert isinstance(v, str) and len(v) > 10, k

    def test_focus_questions_are_non_empty_strings(self):
        for k, v in FOCUS_QUESTION.items():
            assert isinstance(v, str) and len(v) > 3, k


# --- Home view ---

@pytest.mark.django_db
class TestHomeView:
    def test_get_returns_200(self, lt_client):
        client, _ = lt_client
        resp = client.get(reverse("longtones:home"))
        assert resp.status_code == 200

    def test_get_requires_login(self, db):
        resp = Client().get(reverse("longtones:home"))
        assert resp.status_code == 302
        assert "/login/" in resp["Location"]

    def test_get_context_has_today_notes(self, lt_client):
        client, _ = lt_client
        resp = client.get(reverse("longtones:home"))
        assert "today_notes" in resp.context
        assert len(resp.context["today_notes"]) > 0

    def test_get_context_has_focus_items(self, lt_client):
        client, _ = lt_client
        resp = client.get(reverse("longtones:home"))
        assert len(resp.context["focus_items"]) == len(FOCUS_CHOICES)

    def test_post_invalid_focus_redirects_home(self, lt_client):
        client, _ = lt_client
        resp = client.post(reverse("longtones:home"), {"focus": "bogus"})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("longtones:home")

    def test_post_valid_focus_creates_session_and_redirects(self, lt_client):
        client, profile = lt_client
        resp = client.post(reverse("longtones:home"), {"focus": "steadiness"})
        assert resp.status_code == 302
        assert resp["Location"] == reverse("longtones:session")
        assert LongToneSession.objects.filter(profile=profile, focus="steadiness").exists()

    def test_post_stores_queue_in_django_session(self, lt_client):
        client, _ = lt_client
        client.post(reverse("longtones:home"), {"focus": "intonation"})
        lt = client.session["lt_session"]
        expected_queue = session_notes_for_date()
        assert lt["queue"] == expected_queue
        assert lt["total"] == len(expected_queue)

    def test_post_use_drone_on_sets_flag(self, lt_client):
        client, profile = lt_client
        client.post(reverse("longtones:home"), {"focus": "steadiness", "use_drone": "on"})
        session_obj = LongToneSession.objects.get(profile=profile)
        assert session_obj.use_drone is True

    def test_post_without_use_drone_unsets_flag(self, lt_client):
        client, profile = lt_client
        client.post(reverse("longtones:home"), {"focus": "steadiness"})
        session_obj = LongToneSession.objects.get(profile=profile)
        assert session_obj.use_drone is False


# --- Session view ---

@pytest.mark.django_db
class TestSessionView:
    def _start(self, client, focus="steadiness", use_drone=False):
        data = {"focus": focus}
        if use_drone:
            data["use_drone"] = "on"
        client.post(reverse("longtones:home"), data)
        return client.session["lt_session"]

    def test_no_active_session_redirects_home(self, lt_client):
        client, _ = lt_client
        resp = client.get(reverse("longtones:session"))
        assert resp.status_code == 302
        assert resp["Location"] == reverse("longtones:home")

    def test_shows_note_name(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        resp = client.get(reverse("longtones:session"))
        assert resp.status_code == 200
        first_midi = lt["queue"][0]
        assert MIDI_NAMES[first_midi].encode() in resp.content

    def test_context_has_hz(self, lt_client):
        client, _ = lt_client
        self._start(client)
        resp = client.get(reverse("longtones:session"))
        assert "hz" in resp.context
        assert resp.context["hz"] > 0

    def test_context_has_focus_prompt(self, lt_client):
        client, _ = lt_client
        self._start(client, focus="intonation")
        resp = client.get(reverse("longtones:session"))
        assert resp.context["focus_prompt"] == FOCUS_PROMPTS["intonation"]

    def test_progress_starts_at_total(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        resp = client.get(reverse("longtones:session"))
        assert resp.context["remaining"] == lt["total"]
        assert resp.context["total"] == lt["total"]


# --- Log note view ---

@pytest.mark.django_db
class TestLogNoteView:
    def _start(self, client, focus="steadiness"):
        client.post(reverse("longtones:home"), {"focus": focus})
        return client.session["lt_session"]

    def test_get_redirects(self, lt_client):
        client, _ = lt_client
        resp = client.get(reverse("longtones:log_note"))
        assert resp.status_code == 302

    def test_valid_rating_creates_log(self, lt_client):
        client, profile = lt_client
        lt = self._start(client)
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])
        first_midi = lt["queue"][0]
        client.post(reverse("longtones:log_note"), {
            "session_id": session_obj.pk,
            "midi": first_midi,
            "rating": 4,
        })
        assert LongToneLog.objects.filter(
            session=session_obj, midi=first_midi, rating=4
        ).exists()

    def test_rating_advances_queue(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])
        first_midi = lt["queue"][0]
        second_midi = lt["queue"][1]
        client.post(reverse("longtones:log_note"), {
            "session_id": session_obj.pk,
            "midi": first_midi,
            "rating": 3,
        })
        lt_after = client.session["lt_session"]
        assert lt_after["queue"][0] == second_midi

    def test_rating_out_of_range_does_not_log(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])
        client.post(reverse("longtones:log_note"), {
            "session_id": session_obj.pk,
            "midi": lt["queue"][0],
            "rating": 99,
        })
        assert LongToneLog.objects.filter(session=session_obj).count() == 0

    def test_last_note_marks_session_complete(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])

        queue = list(lt["queue"])
        for midi in queue[:-1]:
            client.post(reverse("longtones:log_note"), {
                "session_id": session_obj.pk, "midi": midi, "rating": 4,
            })

        resp = client.post(reverse("longtones:log_note"), {
            "session_id": session_obj.pk, "midi": queue[-1], "rating": 4,
        })
        assert resp["Location"] == reverse("longtones:complete")
        session_obj.refresh_from_db()
        assert session_obj.completed_at is not None

    def test_log_stores_note_name(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])
        first_midi = lt["queue"][0]
        client.post(reverse("longtones:log_note"), {
            "session_id": session_obj.pk, "midi": first_midi, "rating": 3,
        })
        log = LongToneLog.objects.get(session=session_obj)
        assert log.note_name == MIDI_NAMES[first_midi]


# --- Skip view ---

@pytest.mark.django_db
class TestSkipView:
    def _start(self, client):
        client.post(reverse("longtones:home"), {"focus": "steadiness"})
        return client.session["lt_session"]

    def test_skip_defers_note_to_end(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        first_midi = lt["queue"][0]
        second_midi = lt["queue"][1]
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])

        client.post(reverse("longtones:skip"), {"session_id": session_obj.pk})

        lt_after = client.session["lt_session"]
        assert lt_after["queue"][0] == second_midi
        assert lt_after["queue"][-1] == first_midi

    def test_skip_does_not_create_log(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])

        client.post(reverse("longtones:skip"), {"session_id": session_obj.pk})

        assert LongToneLog.objects.filter(session=session_obj).count() == 0

    def test_skip_single_item_queue_unchanged(self, lt_client):
        client, _ = lt_client
        lt = self._start(client)
        last_midi = lt["queue"][-1]
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])

        s = client.session
        s["lt_session"]["queue"] = [last_midi]
        s.save()

        client.post(reverse("longtones:skip"), {"session_id": session_obj.pk})
        assert client.session["lt_session"]["queue"] == [last_midi]


# --- Complete view ---

@pytest.mark.django_db
class TestCompleteView:
    def test_complete_page_loads(self, lt_client):
        client, _ = lt_client
        resp = client.get(reverse("longtones:complete"))
        assert resp.status_code == 200

    def test_complete_clears_lt_session(self, lt_client):
        client, _ = lt_client
        client.post(reverse("longtones:home"), {"focus": "steadiness"})
        client.get(reverse("longtones:complete"))
        assert "lt_session" not in client.session

    def test_complete_shows_avg_rating_after_full_session(self, lt_client):
        client, _ = lt_client
        client.post(reverse("longtones:home"), {"focus": "crescendo"})
        lt = client.session["lt_session"]
        session_obj = LongToneSession.objects.get(pk=lt["session_id"])

        for midi in lt["queue"]:
            client.post(reverse("longtones:log_note"), {
                "session_id": session_obj.pk, "midi": midi, "rating": 5,
            })

        resp = client.get(reverse("longtones:complete"))
        assert resp.context["avg_rating"] == 5.0

    def test_complete_shows_most_recent_completed_session(self, lt_client):
        client, profile = lt_client
        # Run two sessions; complete page should show the second
        for focus in ["steadiness", "intonation"]:
            client.post(reverse("longtones:home"), {"focus": focus})
            lt = client.session["lt_session"]
            session_obj = LongToneSession.objects.get(pk=lt["session_id"])
            for midi in lt["queue"]:
                client.post(reverse("longtones:log_note"), {
                    "session_id": session_obj.pk, "midi": midi, "rating": 3,
                })

        resp = client.get(reverse("longtones:complete"))
        assert resp.context["session_obj"].focus == "intonation"
