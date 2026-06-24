from dataclasses import dataclass
from datetime import date, timedelta

# Maps the 1-4 user-facing rating to the 0-5 quality scale used by SM-2.
# Again=1 → quality 0 (failure), Hard=2 → 3, Good=3 → 4, Easy=4 → 5
RATING_TO_QUALITY = {1: 0, 2: 3, 3: 4, 4: 5}


@dataclass
class SM2State:
    ease_factor: float
    interval_days: int
    repetitions: int
    next_review_at: date | None


def apply_rating(state: SM2State, rating: int, today: date | None = None) -> SM2State:
    """Apply one SM-2 review and return the updated state.

    Args:
        state: Current SM-2 values from a TrickyBit.
        rating: 1=Again, 2=Hard, 3=Good, 4=Easy.
        today: Date of the review; defaults to date.today().

    Returns:
        New SM2State with updated ease_factor, interval_days,
        repetitions, and next_review_at.
    """
    if today is None:
        today = date.today()

    quality = RATING_TO_QUALITY[rating]

    if quality < 3:
        # Failed — reset repetitions and interval; ease is unchanged
        new_interval = 1
        new_reps = 0
        new_ease = state.ease_factor
    else:
        new_ease = state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ease = max(1.3, new_ease)

        reps = state.repetitions
        if reps == 0:
            new_interval = 1
        elif reps == 1:
            new_interval = 6
        else:
            new_interval = round(state.interval_days * state.ease_factor)

        new_reps = state.repetitions + 1

    return SM2State(
        ease_factor=new_ease,
        interval_days=new_interval,
        repetitions=new_reps,
        next_review_at=today + timedelta(days=new_interval),
    )


def calculate_tempo_ladder(
    current_tempo: int | None,
    desired_tempo: int | None,
) -> list[int]:
    """Return an ordered list of BPM targets for one practice session.

    Strategy:
    - Start at min(desired_tempo / 2, current_tempo * 0.75), rounded to 5 BPM
    - One optional midpoint when the range is at least 15 BPM
    - Final base step at current_tempo (the established speed)
    - One push step above current_tempo toward desired_tempo (only when
      current_tempo is known, so the user is building on a proven pace)

    Returns an empty list when neither tempo is set.
    """
    if current_tempo is None and desired_tempo is None:
        return []

    # The highest pace we are building toward in this session
    target: int = current_tempo or desired_tempo  # type: ignore[assignment]

    # --- Starting tempo ---
    candidates: list[float] = []
    if current_tempo:
        candidates.append(current_tempo * 0.75)
    if desired_tempo:
        candidates.append(desired_tempo * 0.5)

    start = max(20, round(min(candidates) / 5) * 5)

    # Ensure start is genuinely below target
    if start >= target:
        start = max(20, round(target * 0.75 / 5) * 5)
    if start >= target:
        start = max(20, target - 5)

    # --- Base steps: start → [midpoint] → target ---
    spread = target - start
    steps: list[int] = [int(start)]

    if spread >= 15:
        mid = round((start + target) / 2 / 5) * 5
        if start < mid < target:
            steps.append(int(mid))

    steps.append(int(target))

    # --- Push step (only when current_tempo is established) ---
    if current_tempo is not None:
        if desired_tempo and desired_tempo > current_tempo:
            # Step partway toward the goal
            gap = desired_tempo - current_tempo
            push = current_tempo + max(5, round(gap / 4 / 5) * 5)
            push = int(min(push, desired_tempo))
        else:
            # No goal set, or already at it — nudge 5% above current
            push = int(current_tempo + max(5, round(current_tempo * 0.05 / 5) * 5))

        if push > target:
            steps.append(push)

    # Deduplicate while preserving order
    seen: set[int] = set()
    result: list[int] = []
    for s in steps:
        if s not in seen:
            seen.add(s)
            result.append(s)

    return result
