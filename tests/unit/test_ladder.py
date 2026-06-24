"""Unit tests for the tempo ladder calculation."""
import pytest

from practice.algorithm import calculate_tempo_ladder


class TestCalculateTempoLadder:
    # --- No-op cases ---

    def test_both_none_returns_empty(self):
        assert calculate_tempo_ladder(None, None) == []

    # --- Single tempo ---

    def test_only_current_tempo_generates_ladder(self):
        result = calculate_tempo_ladder(80, None)
        assert result[0] < 80      # starts below current
        assert result[-1] > 80     # push step above current
        assert 80 in result        # current itself is included

    def test_only_desired_tempo_generates_ladder_to_goal(self):
        result = calculate_tempo_ladder(None, 120)
        assert result[0] < 120
        assert result[-1] == 120   # no push when current unknown

    # --- Start tempo rule ---

    def test_start_is_lower_of_half_desired_and_75pct_current(self):
        # current=80 (75% = 60), desired=120 (half = 60) → start = 60
        result = calculate_tempo_ladder(80, 120)
        assert result[0] == 60

    def test_start_uses_75pct_when_lower_than_half_desired(self):
        # current=100 (75% = 75), desired=200 (half = 100) → start = 75
        result = calculate_tempo_ladder(100, 200)
        assert result[0] == 75

    def test_start_uses_half_desired_when_lower_than_75pct(self):
        # current=160 (75% = 120), desired=200 (half = 100) → start = 100
        result = calculate_tempo_ladder(160, 200)
        assert result[0] == 100

    def test_start_rounds_to_nearest_5(self):
        result = calculate_tempo_ladder(83, None)
        assert result[0] % 5 == 0

    def test_start_minimum_is_20(self):
        result = calculate_tempo_ladder(25, None)
        assert result[0] >= 20

    # --- Order and structure ---

    def test_steps_are_strictly_ascending(self):
        result = calculate_tempo_ladder(80, 120)
        assert result == sorted(result)

    def test_no_duplicate_steps(self):
        result = calculate_tempo_ladder(80, 120)
        assert len(result) == len(set(result))

    def test_current_tempo_always_in_ladder(self):
        result = calculate_tempo_ladder(80, 120)
        assert 80 in result

    def test_small_range_produces_few_steps(self):
        # Very small gap → start close to target, minimal steps
        result = calculate_tempo_ladder(50, None)
        assert len(result) >= 2

    # --- Push step ---

    def test_push_step_present_when_current_tempo_set(self):
        result = calculate_tempo_ladder(80, 120)
        # Push step should be above current_tempo (80)
        assert result[-1] > 80

    def test_push_step_does_not_exceed_desired_tempo(self):
        result = calculate_tempo_ladder(115, 120)
        assert result[-1] <= 120

    def test_no_push_step_when_no_current_tempo(self):
        result = calculate_tempo_ladder(None, 120)
        # Last step is desired_tempo; nothing beyond
        assert result[-1] == 120

    def test_push_is_toward_desired_tempo(self):
        result = calculate_tempo_ladder(80, 120)
        push = result[-1]
        assert 80 < push <= 120

    # --- Typical examples ---

    def test_typical_80_to_120(self):
        result = calculate_tempo_ladder(80, 120)
        # Expect: [60, 70, 80, 90] roughly
        assert result[0] == 60
        assert 80 in result
        assert result[-1] > 80
        assert result[-1] <= 120

    def test_typical_100_to_120(self):
        result = calculate_tempo_ladder(100, 120)
        assert result[0] < 100
        assert 100 in result
        assert result[-1] > 100
        assert result[-1] <= 120
