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
