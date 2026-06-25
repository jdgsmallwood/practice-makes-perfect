"""Unit tests for the practice session planner."""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Profile
from planner.models import PracticeSession
from planner.views import CATEGORY_CONFIG, allocate_time


# ---------------------------------------------------------------------------
# allocate_time() — pure function tests
# ---------------------------------------------------------------------------

class TestAllocateTime:
    def _counts(self, **kwargs):
        base = {cat: 0 for cat in CATEGORY_CONFIG}
        base.update(kwargs)
        return base

    def test_single_category_gets_all_time_clamped_to_max(self):
        result = allocate_time(60, ["trickybit"], self._counts(trickybit=5))
        assert len(result) == 1
        cfg = CATEGORY_CONFIG["trickybit"]
        assert result[0]["minutes"] <= cfg["max_minutes"]

    def test_two_equal_weight_categories_split_evenly(self):
        result = allocate_time(30, ["longtones", "articulation"], self._counts())
        minutes = [s["minutes"] for s in result]
        assert abs(minutes[0] - minutes[1]) <= 1

    def test_sm2_category_with_more_due_gets_more_time(self):
        result = allocate_time(60, ["trickybit", "scales_sm2"], self._counts(trickybit=10, scales_sm2=1))
        trickybit_mins = next(s["minutes"] for s in result if s["category"] == "trickybit")
        scales_mins = next(s["minutes"] for s in result if s["category"] == "scales_sm2")
        assert trickybit_mins >= scales_mins

    def test_min_minutes_enforced(self):
        result = allocate_time(6, ["trickybit", "longtones"], self._counts())
        for section in result:
            cfg = CATEGORY_CONFIG[section["category"]]
            assert section["minutes"] >= cfg["min_minutes"]

    def test_max_minutes_enforced(self):
        result = allocate_time(180, ["trickybit"], self._counts(trickybit=100))
        cfg = CATEGORY_CONFIG["trickybit"]
        assert result[0]["minutes"] <= cfg["max_minutes"]

    def test_returns_sections_in_requested_order(self):
        order = ["longtones", "scales_rotation", "articulation"]
        result = allocate_time(60, order, self._counts(scales_rotation=5))
        assert [s["category"] for s in result] == order

    def test_item_count_reflected_in_sections(self):
        result = allocate_time(30, ["trickybit"], self._counts(trickybit=7))
        assert result[0]["item_count"] == 7

    def test_empty_categories_returns_empty(self):
        result = allocate_time(45, [], self._counts())
        assert result == []


# ---------------------------------------------------------------------------
# Planner view tests
# ---------------------------------------------------------------------------

def _make_client_with_profile(db):
    user = User.objects.create_user("planner_user", password="test")
    profile = Profile.objects.create(user=user, name="P")
    c = Client()
    c.force_login(user)
    session = c.session
    session["active_profile_id"] = profile.pk
    session.save()
    return c, profile


def _planner_state(session_id=1, sections=None, total_minutes=30):
    if sections is None:
        sections = [
            {"category": "longtones", "label": "Long Tones", "minutes": 15,
             "start_url": "/long-tones/", "item_count": 0, "completed_at": None},
            {"category": "articulation", "label": "Articulation", "minutes": 15,
             "start_url": "/articulation/", "item_count": 0, "completed_at": None},
        ]
    return {"session_id": session_id, "total_minutes": total_minutes, "sections": sections}


@pytest.mark.django_db
class TestPlanSetupView:
    def test_get_renders_form(self, logged_in_client):
        response = logged_in_client.get(reverse("planner:setup"))
        assert response.status_code == 200
        assert b"Plan a Session" in response.content

    def test_post_creates_practice_session(self, db):
        c, _ = _make_client_with_profile(db)
        before = PracticeSession.objects.count()
        c.post(reverse("planner:setup"), {"total_minutes": "30", "cat_longtones": "1"})
        assert PracticeSession.objects.count() == before + 1

    def test_post_writes_planner_state_to_session(self, db):
        c, _ = _make_client_with_profile(db)
        c.post(reverse("planner:setup"), {"total_minutes": "30", "cat_longtones": "1"})
        session = c.session
        assert "planner_state" in session

    def test_post_redirects_to_overview(self, db):
        c, _ = _make_client_with_profile(db)
        response = c.post(reverse("planner:setup"), {"total_minutes": "30", "cat_longtones": "1"})
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:overview")

    def test_post_requires_at_least_one_category(self, db):
        c, _ = _make_client_with_profile(db)
        response = c.post(reverse("planner:setup"), {"total_minutes": "30"})
        assert response.status_code == 200
        assert b"at least one" in response.content.lower()

    def test_post_rejects_minutes_below_minimum(self, db):
        c, _ = _make_client_with_profile(db)
        before = PracticeSession.objects.count()
        response = c.post(reverse("planner:setup"), {"total_minutes": "2", "cat_longtones": "1"})
        assert response.status_code == 200
        assert PracticeSession.objects.count() == before

    def test_post_rejects_minutes_above_maximum(self, db):
        c, _ = _make_client_with_profile(db)
        before = PracticeSession.objects.count()
        response = c.post(reverse("planner:setup"), {"total_minutes": "999", "cat_longtones": "1"})
        assert response.status_code == 200
        assert PracticeSession.objects.count() == before


@pytest.mark.django_db
class TestPlanOverviewView:
    def test_no_state_redirects_to_setup(self, logged_in_client):
        response = logged_in_client.get(reverse("planner:overview"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:setup")

    def test_renders_section_labels(self, db):
        c, _ = _make_client_with_profile(db)
        session = c.session
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        response = c.get(reverse("planner:overview"))
        assert response.status_code == 200
        assert b"Long Tones" in response.content

    def test_all_done_redirects_to_complete(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        sections = [
            {"category": "longtones", "label": "Long Tones", "minutes": 30,
             "start_url": "/long-tones/", "item_count": 0,
             "completed_at": "2026-06-25T10:00:00+00:00"},
        ]
        session = c.session
        session["planner_state"] = {"session_id": ps.pk, "total_minutes": 30, "sections": sections}
        session.save()
        response = c.get(reverse("planner:overview"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:complete")


@pytest.mark.django_db
class TestPlanSectionDoneView:
    def test_marks_first_incomplete_section_and_redirects(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones", "articulation"], sections_json=[]
        )
        session = c.session
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        response = c.get(reverse("planner:section_done"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:overview")
        updated_state = c.session["planner_state"]
        assert updated_state["sections"][0]["completed_at"] is not None
        assert updated_state["sections"][1]["completed_at"] is None

    def test_skips_already_completed_section(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones", "articulation"], sections_json=[]
        )
        sections = [
            {"category": "longtones", "label": "Long Tones", "minutes": 15,
             "start_url": "/long-tones/", "item_count": 0,
             "completed_at": "2026-06-25T10:00:00+00:00"},
            {"category": "articulation", "label": "Articulation", "minutes": 15,
             "start_url": "/articulation/", "item_count": 0, "completed_at": None},
        ]
        session = c.session
        session["planner_state"] = {"session_id": ps.pk, "total_minutes": 30, "sections": sections}
        session.save()
        c.get(reverse("planner:section_done"))
        updated_state = c.session["planner_state"]
        assert updated_state["sections"][1]["completed_at"] is not None

    def test_no_state_redirects_to_overview(self, logged_in_client):
        response = logged_in_client.get(reverse("planner:section_done"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:overview")

    def test_updates_db_sections_json(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        session = c.session
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        c.get(reverse("planner:section_done"))
        ps.refresh_from_db()
        assert ps.sections_json[0]["completed_at"] is not None


@pytest.mark.django_db
class TestPlanCompleteView:
    def test_stamps_finished_at_on_db_record(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        session = c.session
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        c.get(reverse("planner:complete"))
        ps.refresh_from_db()
        assert ps.finished_at is not None

    def test_clears_planner_state_from_session(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        session = c.session
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        c.get(reverse("planner:complete"))
        assert "planner_state" not in c.session

    def test_renders_summary(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        session = c.session
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        response = c.get(reverse("planner:complete"))
        assert response.status_code == 200
        assert b"Session Complete" in response.content


@pytest.mark.django_db
class TestPlanAbandonView:
    def test_clears_session_and_redirects_to_dashboard(self, db):
        c, _ = _make_client_with_profile(db)
        ps = PracticeSession.objects.create(
            total_minutes_planned=30, categories_json=["longtones"], sections_json=[]
        )
        session = c.session
        session["planner_state"] = _planner_state(session_id=ps.pk)
        session.save()
        response = c.post(reverse("planner:abandon"))
        assert response.status_code == 302
        assert "planner_state" not in c.session

    def test_get_redirects_to_overview(self, logged_in_client):
        response = logged_in_client.get(reverse("planner:abandon"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:overview")


# ---------------------------------------------------------------------------
# Guard hooks in existing completion views
# ---------------------------------------------------------------------------

def _set_planner_state(client, session_id=99):
    session = client.session
    session["planner_state"] = _planner_state(session_id=session_id)
    session.save()


@pytest.mark.django_db
class TestExistingViewGuards:
    def test_practice_complete_redirects_when_planner_active(self, logged_in_client):
        _set_planner_state(logged_in_client)
        response = logged_in_client.get(reverse("practice:complete"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:section_done")

    def test_longtones_complete_redirects_when_planner_active(self, logged_in_client):
        _set_planner_state(logged_in_client)
        response = logged_in_client.get(reverse("longtones:complete"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:section_done")

    def test_articulation_complete_redirects_when_planner_active(self, logged_in_client):
        _set_planner_state(logged_in_client)
        response = logged_in_client.get(reverse("articulation:complete"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:section_done")

    def test_scales_sm2_complete_redirects_when_planner_active(self, logged_in_client):
        _set_planner_state(logged_in_client)
        response = logged_in_client.get(reverse("scales:sm2_complete"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:section_done")

    def test_scales_rotation_complete_redirects_when_planner_active(self, logged_in_client):
        _set_planner_state(logged_in_client)
        response = logged_in_client.get(reverse("scales:rotation_complete"))
        assert response.status_code == 302
        assert response["Location"] == reverse("planner:section_done")

    def test_practice_complete_normal_without_planner_state(self, logged_in_client):
        response = logged_in_client.get(reverse("practice:complete"))
        assert response.status_code == 200

    def test_longtones_complete_normal_without_planner_state(self, logged_in_client):
        response = logged_in_client.get(reverse("longtones:complete"))
        assert response.status_code == 200

    def test_articulation_complete_normal_without_planner_state(self, logged_in_client):
        response = logged_in_client.get(reverse("articulation:complete"))
        assert response.status_code == 200
