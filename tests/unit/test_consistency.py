"""Unit tests for the streak / consistency feature."""
from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Instrument, Profile
from articulation.models import ArticulationLog, ArticulationSession
from longtones.models import LongToneLog, LongToneSession
from practice.views import _get_practice_dates, build_heatmap, calculate_streaks
from scales.models import ScaleLog, ScalePractice, ScaleType
from tests.factories import PracticeLogFactory, TrickyBitFactory, PieceFactory


# ---------------------------------------------------------------------------
# calculate_streaks() — pure function
# ---------------------------------------------------------------------------

class TestCalculateStreaks:
    def test_empty_returns_zeros(self):
        result = calculate_streaks(set())
        assert result == {"current": 0, "longest": 0, "total_days": 0}

    def test_only_today(self):
        result = calculate_streaks({date.today()})
        assert result["current"] == 1
        assert result["longest"] == 1
        assert result["total_days"] == 1

    def test_only_yesterday_counts_as_current(self):
        yesterday = date.today() - timedelta(days=1)
        result = calculate_streaks({yesterday})
        assert result["current"] == 1

    def test_today_and_yesterday(self):
        today = date.today()
        result = calculate_streaks({today, today - timedelta(days=1)})
        assert result["current"] == 2
        assert result["longest"] == 2

    def test_gap_breaks_current_streak(self):
        today = date.today()
        dates = {today, today - timedelta(days=2)}  # gap on day 1
        result = calculate_streaks(dates)
        assert result["current"] == 1

    def test_two_days_ago_gives_zero_current_streak(self):
        two_days_ago = date.today() - timedelta(days=2)
        result = calculate_streaks({two_days_ago})
        assert result["current"] == 0

    def test_longest_can_exceed_current(self):
        today = date.today()
        # 5-day run 10-6 days ago; nothing since (no recent practice)
        past_run = {today - timedelta(days=d) for d in range(10, 5, -1)}
        result = calculate_streaks(past_run)
        assert result["longest"] == 5
        assert result["current"] == 0

    def test_total_days_reflects_unique_days(self):
        dates = {date.today() - timedelta(days=d) for d in range(7)}
        result = calculate_streaks(dates)
        assert result["total_days"] == 7


# ---------------------------------------------------------------------------
# build_heatmap() — pure function
# ---------------------------------------------------------------------------

class TestBuildHeatmap:
    def test_returns_correct_week_count(self):
        heatmap = build_heatmap(set(), weeks=26)
        assert len(heatmap) == 26

    def test_each_week_has_seven_days(self):
        heatmap = build_heatmap(set(), weeks=4)
        for week in heatmap:
            assert len(week) == 7

    def test_practiced_day_marked(self):
        today = date.today()
        heatmap = build_heatmap({today}, weeks=4)
        flat = [day for week in heatmap for day in week]
        today_cell = next(d for d in flat if d["date"] == today)
        assert today_cell["practiced"] is True

    def test_non_practiced_day_not_marked(self):
        today = date.today()
        heatmap = build_heatmap(set(), weeks=4)
        flat = [day for week in heatmap for day in week]
        today_cell = next(d for d in flat if d["date"] == today)
        assert today_cell["practiced"] is False

    def test_future_days_marked(self):
        heatmap = build_heatmap(set(), weeks=2)
        flat = [day for week in heatmap for day in week]
        future_cells = [d for d in flat if d["date"] > date.today()]
        # For any future days in the grid, they should be marked future=True
        for cell in future_cells:
            assert cell["future"] is True

    def test_starts_on_monday(self):
        heatmap = build_heatmap(set(), weeks=4)
        first_day = heatmap[0][0]["date"]
        assert first_day.weekday() == 0  # Monday


# ---------------------------------------------------------------------------
# _get_practice_dates() — integration (needs DB)
# ---------------------------------------------------------------------------

def _make_profile(db):
    user = User.objects.create_user(f"consistency_user_{id(db)}", password="test")
    instrument = Instrument.objects.create(
        slug="flute-c", name="Flute", midi_low=60, midi_high=96
    )
    return Profile.objects.create(user=user, name="P", instrument=instrument)


@pytest.mark.django_db
class TestGetPracticeDates:
    def test_collects_practice_log_date(self, db):
        profile = _make_profile(db)
        piece = PieceFactory(profile=profile, is_active=True)
        bit = TrickyBitFactory(piece=piece)
        PracticeLogFactory(tricky_bit=bit)
        dates = _get_practice_dates(profile)
        assert len(dates) >= 1

    def test_collects_scale_log_date(self, db):
        profile = _make_profile(db)
        scale_type = ScaleType.objects.create(
            slug="major-cst", name="Major", category="Diatonic",
            intervals=[0, 2, 4, 5, 7, 9, 11],
        )
        sp = ScalePractice.objects.create(profile=profile, root=0, scale_type=scale_type)
        ScaleLog.objects.create(scale_practice=sp, rating=3)
        dates = _get_practice_dates(profile)
        assert date.today() in dates

    def test_collects_longtone_log_date(self, db):
        profile = _make_profile(db)
        session_obj = LongToneSession.objects.create(profile=profile, date=date.today(), focus="tone")
        LongToneLog.objects.create(session=session_obj, midi=60, note_name="C4", rating=4)
        dates = _get_practice_dates(profile)
        assert date.today() in dates

    def test_collects_articulation_log_date(self, db):
        profile = _make_profile(db)
        session_obj = ArticulationSession.objects.create(profile=profile, date=date.today(), track="classical")
        ArticulationLog.objects.create(session=session_obj, exercise_id=1, rating=3)
        dates = _get_practice_dates(profile)
        assert date.today() in dates

    def test_returns_empty_for_profile_with_no_logs(self, db):
        profile = _make_profile(db)
        dates = _get_practice_dates(profile)
        assert len(dates) == 0

    def test_does_not_include_other_profiles_data(self, db):
        profile_a = _make_profile(db)
        user_b = User.objects.create_user("other_user_cst", password="test")
        profile_b = Profile.objects.create(user=user_b, name="B")
        piece = PieceFactory(profile=profile_b, is_active=True)
        bit = TrickyBitFactory(piece=piece)
        PracticeLogFactory(tricky_bit=bit)
        dates = _get_practice_dates(profile_a)
        assert len(dates) == 0


# ---------------------------------------------------------------------------
# consistency_view — view test
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConsistencyView:
    def test_returns_200(self, logged_in_client):
        response = logged_in_client.get(reverse("practice:consistency"))
        assert response.status_code == 200

    def test_renders_streak_stats(self, logged_in_client):
        response = logged_in_client.get(reverse("practice:consistency"))
        assert b"day streak" in response.content
        assert b"longest streak" in response.content

    def test_renders_heatmap(self, logged_in_client):
        response = logged_in_client.get(reverse("practice:consistency"))
        assert b"Last 26 weeks" in response.content

    def test_requires_login(self, client):
        response = client.get(reverse("practice:consistency"))
        assert response.status_code == 302
        assert "login" in response["Location"]
