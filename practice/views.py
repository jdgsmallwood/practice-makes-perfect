import json
from datetime import date

from django.db.models import F, Min, Q
from django.shortcuts import get_object_or_404, redirect, render

from pieces.models import PracticeLog, TrickyBit
from .algorithm import SM2State, apply_rating, calculate_tempo_ladder


def _get_due_bits():
    today = date.today()
    return (
        TrickyBit.objects.filter(piece__is_active=True)
        .filter(Q(next_review_at__lte=today) | Q(next_review_at__isnull=True))
        .select_related("piece")
        .order_by(F("next_review_at").asc(nulls_first=True), "-difficulty")
    )


def practice_session(request):
    # Bits deferred this session live in the cookie-backed session.
    # We show all fresh (non-skipped) due bits first, then cycle back to skipped.
    skipped_ids = set(request.session.get("skipped_bits", []))
    all_due = _get_due_bits()
    fresh_due = all_due.exclude(pk__in=skipped_ids)

    bit = fresh_due.first()
    if bit is None:
        # All fresh bits done — start cycling through skipped ones
        bit = all_due.filter(pk__in=skipped_ids).first()

    if bit is None:
        request.session.pop("skipped_bits", None)
        return redirect("practice:complete")

    today = date.today()
    completed_today = PracticeLog.objects.filter(reviewed_at__date=today).count()

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
        "due_count": fresh_due.count(),
        "skipped_count": len(skipped_ids & {b.pk for b in all_due}),
        "completed_today": completed_today,
        "preview_intervals": preview_intervals,
        "is_skipped": bit.pk in skipped_ids,
        "ladder_json": json.dumps(ladder),
        # Index of the push step (first index above original current_tempo)
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if bit.current_tempo and t > bit.current_tempo),
            None,
        ),
    })


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

    bit = get_object_or_404(TrickyBit, pk=bit_id)
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

    # Remove from skipped set now that it's been rated
    skipped = list(request.session.get("skipped_bits", []))
    if bit_id in skipped:
        skipped.remove(bit_id)
        request.session["skipped_bits"] = skipped

    return redirect("practice:session")  # PRG — prevents double-submit on refresh


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


def complete(request):
    request.session.pop("skipped_bits", None)

    today = date.today()
    completed_today = PracticeLog.objects.filter(reviewed_at__date=today).count()

    next_due = TrickyBit.objects.filter(
        piece__is_active=True,
        next_review_at__isnull=False,
        next_review_at__gt=today,
    ).aggregate(Min("next_review_at"))["next_review_at__min"]

    return render(request, "practice/complete.html", {
        "completed_today": completed_today,
        "next_due": next_due,
    })
