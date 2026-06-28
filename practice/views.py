import json
import random
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Min, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.utils import get_active_profile
from articulation.models import ArticulationLog
from longtones.models import LongToneLog
from pieces.models import PracticeLog, TrickyBit
from scales.models import ScaleLog
from .algorithm import SM2State, apply_rating, calculate_tempo_ladder


# Priority signal weights for ordering due bits within a session. tempo + peer +
# smoothness form a budget; new_boost is an additive bonus for never-reviewed bits.
# Mirrors the scales rotation weighting (see scales.views.DEFAULT_SCALE_WEIGHTS).
PRACTICE_WEIGHTS = {"tempo": 6, "peer": 3, "smoothness": 1, "new_boost": 7}


def _get_due_bits(profile):
    today = timezone.localdate()
    return (
        TrickyBit.objects.filter(piece__is_active=True, piece__profile=profile)
        .filter(Q(next_review_at__lte=today) | Q(next_review_at__isnull=True))
        .select_related("piece")
    )


def _compute_practice_weights(due_bits: list, weights: dict = PRACTICE_WEIGHTS) -> dict:
    """Return {pk: weight 1-3} controlling how early a bit appears in the session.

    Mirrors the scales rotation weighting. Signals (each 0..1, scaled by the
    tempo/peer/smoothness budget), plus an additive new-bit bonus:
      1. Tempo deficit vs the bit's goal tempo
      2. Peer lag — bottom quartile of progress within the same piece
      3. Smoothness — inverted average of the last 3 ratings
    Never-reviewed bits (repetitions == 0) get a bonus for early introduction.
    """
    if not due_bits:
        return {}

    wt, wp, ws = weights["tempo"], weights["peer"], weights["smoothness"]
    total = wt + wp + ws
    if total <= 0:                       # malformed → fall back to defaults
        wt, wp, ws, total = 6, 3, 1, 10
    nt, np_, ns = wt / total, wp / total, ws / total
    new_bonus = weights["new_boost"] / 10 * 0.6   # 0.0–0.6 additive

    pks = [b.pk for b in due_bits]

    # Last 3 rated logs per bit (single query, grouped in Python)
    rows = (
        PracticeLog.objects
        .filter(tricky_bit_id__in=pks, rating__isnull=False)
        .order_by("tricky_bit_id", "-reviewed_at")
        .values_list("tricky_bit_id", "rating")
    )
    ratings_by_pk: dict[int, list[int]] = {}
    for bit_id, rating in rows:
        bucket = ratings_by_pk.setdefault(bit_id, [])
        if len(bucket) < 3:
            bucket.append(rating)

    # Peer group: bits within the same piece
    by_piece: dict[int, list] = {}
    for b in due_bits:
        by_piece.setdefault(b.piece_id, []).append(b)

    def progress(b):
        if b.desired_tempo and b.current_tempo:
            return b.current_tempo / b.desired_tempo
        return None

    def bottom_quartile(b, group):
        ratios = sorted(r for r in (progress(g) for g in group) if r is not None)
        if len(ratios) < 2:
            return False
        my = progress(b)
        return my is not None and my <= ratios[len(ratios) // 4]

    result = {}
    for b in due_bits:
        # Signal 1: tempo deficit (0..1)
        if b.desired_tempo and b.current_tempo:
            td = max(0.0, 1 - (b.current_tempo / b.desired_tempo))
        elif b.desired_tempo:
            td = 0.8   # goal set but never measured — needs establishing
        else:
            td = 0.5   # no goal — neutral

        # Signal 2: peer lag (binary 0/1)
        pl = 1.0 if bottom_quartile(b, by_piece[b.piece_id]) else 0.0

        # Signal 3: smoothness (inverted rating avg, 0..1)
        r = ratings_by_pk.get(b.pk, [])
        avg = sum(r) / len(r) if r else 2.5
        sd = (4 - avg) / 3

        raw = nt * td + np_ * pl + ns * sd

        if b.repetitions == 0:
            raw += new_bonus   # new bit bonus — ensure early introduction

        result[b.pk] = 3 if raw > 0.55 else (2 if raw >= 0.25 else 1)

    return result


def _build_weighted_order(due_bits: list, weights: dict) -> list:
    """Order bit PKs so higher-weighted bits tend to come first, with jitter.

    Each bit appears once per session, so rather than expanding by weight we use
    weighted random sampling without replacement (Efraimidis–Spirakis): a higher
    weight raises the chance of an earlier slot while keeping the order varied.
    """
    keyed = []
    for b in due_bits:
        w = weights.get(b.pk, 1)
        # random()**(1/w): larger w → key closer to 1 → sorts earlier
        keyed.append((random.random() ** (1.0 / w), b.pk))
    keyed.sort(reverse=True)
    return [pk for _, pk in keyed]


def _get_or_build_practice_order(request, all_due):
    """Return a session-stable, tempo-aware ordering of due bit PKs.

    Builds and stores the list on first call; subsequent calls within the same
    session reuse it so the order stays stable across PRG redirects.
    """
    order = request.session.get("practice_order")
    due_pks = set(all_due.values_list("pk", flat=True))
    if order:
        # Prune PKs that are no longer due
        order = [pk for pk in order if pk in due_pks]
    if not order:
        bits = list(all_due)
        weights = _compute_practice_weights(bits)
        order = _build_weighted_order(bits, weights)
    request.session["practice_order"] = order
    return order


@login_required
def practice_session(request):
    profile = get_active_profile(request)
    skipped_ids = set(request.session.get("skipped_bits", []))
    all_due = _get_due_bits(profile)

    order = _get_or_build_practice_order(request, all_due)

    # Pick the first ordered bit that isn't skipped
    due_pk_set = {b.pk for b in all_due}
    bit = None
    for pk in order:
        if pk not in skipped_ids and pk in due_pk_set:
            bit = all_due.filter(pk=pk).first()
            break

    if bit is None:
        # All fresh bits done — cycle through skipped ones in original order
        for pk in order:
            if pk in skipped_ids and pk in due_pk_set:
                bit = all_due.filter(pk=pk).first()
                break

    if bit is None:
        request.session.pop("skipped_bits", None)
        request.session.pop("practice_order", None)
        return redirect("practice:complete")

    today = timezone.localdate()
    completed_today = PracticeLog.objects.filter(
        reviewed_at__date=today,
        tricky_bit__piece__profile=profile,
    ).count()

    fresh_due_count = sum(1 for pk in order if pk not in skipped_ids and pk in due_pk_set)

    state = SM2State(
        ease_factor=bit.ease_factor,
        interval_days=bit.interval_days,
        repetitions=bit.repetitions,
        next_review_at=bit.next_review_at,
    )
    preview_intervals = {r: apply_rating(state, r, today=today).interval_days for r in [1, 2, 3, 4]}
    ladder = calculate_tempo_ladder(bit.current_tempo, bit.desired_tempo)

    return render(request, "practice/session.html", {
        "bit": bit,
        "due_count": fresh_due_count,
        "skipped_count": len(skipped_ids & due_pk_set),
        "completed_today": completed_today,
        "preview_intervals": preview_intervals,
        "is_skipped": bit.pk in skipped_ids,
        "ladder_json": json.dumps(ladder),
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if bit.current_tempo and t > bit.current_tempo),
            None,
        ),
    })


@login_required
def rate_bit(request):
    if request.method != "POST":
        return redirect("practice:session")

    try:
        bit_id = int(request.POST["bit_id"])
        rating = int(request.POST["rating"])
    except (KeyError, ValueError):
        return redirect("practice:session")

    if rating not in (1, 2, 3, 4):
        return redirect("practice:session")

    profile = get_active_profile(request)
    bit = get_object_or_404(TrickyBit, pk=bit_id, piece__profile=profile)
    interval_before = bit.interval_days

    state = SM2State(
        ease_factor=bit.ease_factor,
        interval_days=bit.interval_days,
        repetitions=bit.repetitions,
        next_review_at=bit.next_review_at,
    )
    new_state = apply_rating(state, rating)

    bit.ease_factor = new_state.ease_factor
    bit.interval_days = new_state.interval_days
    bit.repetitions = new_state.repetitions
    bit.next_review_at = new_state.next_review_at

    update_fields = ["ease_factor", "interval_days", "repetitions", "next_review_at"]

    achieved_tempo_raw = request.POST.get("achieved_tempo", "").strip()
    if achieved_tempo_raw:
        try:
            achieved_tempo = int(achieved_tempo_raw)
            if 20 <= achieved_tempo <= 400:
                bit.current_tempo = achieved_tempo
                update_fields.append("current_tempo")
        except ValueError:
            pass

    bit.save(update_fields=update_fields)

    log_achieved_tempo: int | None = None
    if achieved_tempo_raw:
        try:
            t = int(achieved_tempo_raw)
            if 20 <= t <= 400:
                log_achieved_tempo = t
        except ValueError:
            pass

    PracticeLog.objects.create(
        tricky_bit=bit,
        rating=rating,
        interval_before=interval_before,
        interval_after=new_state.interval_days,
        achieved_tempo=log_achieved_tempo,
    )

    # Remove from skipped set and practice order now that it's been rated
    skipped = list(request.session.get("skipped_bits", []))
    if bit_id in skipped:
        skipped.remove(bit_id)
        request.session["skipped_bits"] = skipped

    order = list(request.session.get("practice_order", []))
    if bit_id in order:
        order.remove(bit_id)
        request.session["practice_order"] = order

    return redirect("practice:session")


@login_required
def skip_bit(request):
    if request.method != "POST":
        return redirect("practice:session")

    try:
        bit_id = int(request.POST["bit_id"])
    except (KeyError, ValueError):
        return redirect("practice:session")

    skipped = list(request.session.get("skipped_bits", []))
    if bit_id not in skipped:
        skipped.append(bit_id)
    request.session["skipped_bits"] = skipped

    return redirect("practice:session")


@login_required
def complete(request):
    request.session.pop("skipped_bits", None)
    request.session.pop("practice_order", None)
    if request.session.get("planner_state"):
        return redirect("planner:section_done")

    profile = get_active_profile(request)
    today = timezone.localdate()

    completed_today = PracticeLog.objects.filter(
        reviewed_at__date=today,
        tricky_bit__piece__profile=profile,
    ).count()

    next_due = TrickyBit.objects.filter(
        piece__is_active=True,
        piece__profile=profile,
        next_review_at__isnull=False,
        next_review_at__gt=today,
    ).aggregate(Min("next_review_at"))["next_review_at__min"]

    return render(request, "practice/complete.html", {
        "completed_today": completed_today,
        "next_due": next_due,
    })


def _get_practice_dates(profile):
    """Return a set of dates on which any practice log was created for the given profile."""
    dates = set()
    # TruncDate uses the active timezone (set by TimezoneMiddleware) when USE_TZ=True,
    # so late-evening local-time practices are correctly attributed to the local date.
    for qs, field in [
        (ScaleLog.objects.filter(scale_practice__profile=profile), "reviewed_at"),
        (PracticeLog.objects.filter(tricky_bit__piece__profile=profile), "reviewed_at"),
    ]:
        dates.update(
            row["d"]
            for row in qs.annotate(d=TruncDate(field)).values("d").distinct()
        )
    dates.update(
        LongToneLog.objects.filter(session__profile=profile)
        .values_list("session__date", flat=True)
        .distinct()
    )
    dates.update(
        ArticulationLog.objects.filter(session__profile=profile)
        .values_list("session__date", flat=True)
        .distinct()
    )
    # Remove None values that can appear if a session has no date set
    dates.discard(None)
    return dates


def calculate_streaks(dates):
    """Return current streak, longest streak, and total practice days."""
    if not dates:
        return {"current": 0, "longest": 0, "total_days": 0}

    today = timezone.localdate()
    # Current streak: consecutive days ending today or yesterday
    sorted_desc = sorted(dates, reverse=True)
    current = 0
    check = today
    for d in sorted_desc:
        if d == check:
            current += 1
            check -= timedelta(days=1)
        elif d == check - timedelta(days=1) and check == today:
            # Nothing logged today yet — start streak from yesterday
            current += 1
            check = d - timedelta(days=1)
        elif d < check:
            break

    # Longest streak
    longest = 0
    run = 0
    prev = None
    for d in sorted(dates):
        if prev is not None and (d - prev).days == 1:
            run += 1
        else:
            run = 1
        if run > longest:
            longest = run
        prev = d

    return {"current": current, "longest": longest, "total_days": len(dates)}


def build_heatmap(dates, weeks=26):
    """Return a list of weeks (columns), each a list of 7 day dicts.

    Each dict: {date, practiced: bool, label: str}.
    The grid starts on the Monday of the week that was `weeks` weeks ago.
    """
    today = timezone.localdate()
    # Go back `weeks` ISO weeks, anchored to Monday
    start = today - timedelta(weeks=weeks - 1)
    # Rewind to the Monday of that week
    start -= timedelta(days=start.weekday())

    date_set = set(dates)
    grid = []
    current = start
    while current <= today:
        week = []
        for _ in range(7):
            week.append({
                "date": current,
                "practiced": current in date_set,
                "label": current.strftime("%a %b %-d"),
                "future": current > today,
            })
            current += timedelta(days=1)
        grid.append(week)
    return grid


@login_required
def consistency_view(request):
    profile = get_active_profile(request)
    practice_dates = _get_practice_dates(profile)
    streaks = calculate_streaks(practice_dates)
    heatmap = build_heatmap(practice_dates)
    return render(request, "practice/consistency.html", {
        "streaks": streaks,
        "heatmap": heatmap,
        "day_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    })
