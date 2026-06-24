from datetime import date, timedelta

import pytest

from practice.algorithm import SM2State, apply_rating

TODAY = date(2025, 6, 1)


def fresh_state() -> SM2State:
    return SM2State(ease_factor=2.5, interval_days=0, repetitions=0, next_review_at=None)


def state_after_n_good_reps(n: int) -> SM2State:
    """Helper: simulate n successive 'Good' ratings from a fresh state."""
    s = fresh_state()
    for _ in range(n):
        s = apply_rating(s, rating=3, today=TODAY)
    return s


class TestFailureRating:
    def test_again_resets_interval_to_1(self):
        s = SM2State(ease_factor=2.5, interval_days=15, repetitions=4, next_review_at=None)
        result = apply_rating(s, rating=1, today=TODAY)
        assert result.interval_days == 1

    def test_again_resets_repetitions_to_0(self):
        s = SM2State(ease_factor=2.5, interval_days=15, repetitions=4, next_review_at=None)
        result = apply_rating(s, rating=1, today=TODAY)
        assert result.repetitions == 0

    def test_again_does_not_change_ease_factor(self):
        s = SM2State(ease_factor=2.5, interval_days=15, repetitions=4, next_review_at=None)
        result = apply_rating(s, rating=1, today=TODAY)
        assert result.ease_factor == 2.5

    def test_again_sets_next_review_to_tomorrow(self):
        s = fresh_state()
        result = apply_rating(s, rating=1, today=TODAY)
        assert result.next_review_at == TODAY + timedelta(days=1)


class TestIntervalProgression:
    def test_first_rep_any_passing_rating_gives_interval_1(self):
        for rating in (2, 3, 4):
            result = apply_rating(fresh_state(), rating=rating, today=TODAY)
            assert result.interval_days == 1, f"rating={rating}"

    def test_second_rep_any_passing_rating_gives_interval_6(self):
        state_after_first = state_after_n_good_reps(1)
        for rating in (2, 3, 4):
            result = apply_rating(state_after_first, rating=rating, today=TODAY)
            assert result.interval_days == 6, f"rating={rating}"

    def test_third_rep_uses_ease_factor(self):
        state = state_after_n_good_reps(2)  # interval_days=6, ease_factor=2.6 after 2 goods
        result = apply_rating(state, rating=3, today=TODAY)
        expected = round(state.interval_days * state.ease_factor)
        assert result.interval_days == expected

    def test_repetitions_increment_on_pass(self):
        result = apply_rating(fresh_state(), rating=3, today=TODAY)
        assert result.repetitions == 1


class TestEaseFactor:
    def test_easy_rating_increases_ease(self):
        result = apply_rating(fresh_state(), rating=4, today=TODAY)
        assert result.ease_factor > 2.5

    def test_good_rating_slightly_increases_ease(self):
        # Good → quality=4: delta = 0.1 - (5-4)*(0.08 + (5-4)*0.02) = 0.1 - 0.1 = 0.0
        # So ease is unchanged for Good
        result = apply_rating(fresh_state(), rating=3, today=TODAY)
        assert abs(result.ease_factor - 2.5) < 1e-9

    def test_hard_rating_decreases_ease(self):
        result = apply_rating(fresh_state(), rating=2, today=TODAY)
        assert result.ease_factor < 2.5

    def test_ease_factor_clamped_at_1_3(self):
        state = SM2State(ease_factor=1.3, interval_days=6, repetitions=2, next_review_at=None)
        result = apply_rating(state, rating=2, today=TODAY)
        assert result.ease_factor >= 1.3

    def test_ease_factor_never_below_minimum(self):
        # Many Hard ratings should never push ease below 1.3
        s = fresh_state()
        for _ in range(20):
            s = apply_rating(s, rating=2, today=TODAY)
        assert s.ease_factor >= 1.3


class TestNextReviewDate:
    def test_next_review_always_set(self):
        for rating in (1, 2, 3, 4):
            result = apply_rating(fresh_state(), rating=rating, today=TODAY)
            assert result.next_review_at is not None

    def test_next_review_is_interval_days_after_today(self):
        result = apply_rating(fresh_state(), rating=3, today=TODAY)
        assert result.next_review_at == TODAY + timedelta(days=result.interval_days)

    def test_defaults_to_actual_today(self):
        result = apply_rating(fresh_state(), rating=3)
        assert result.next_review_at == date.today() + timedelta(days=result.interval_days)
