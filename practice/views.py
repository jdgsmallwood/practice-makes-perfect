import json
import random
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Min, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_active_profile
from pieces.models import PracticeLog, TrickyBit
from .algorithm import SM2State, apply_rating, calculate_tempo_ladder


def _get_due_bits(profile):
    today = date.today()
    return (
        TrickyBit.objects.filter(piece__is_active=True, piece__profile=profile)
        .filter(Q(next_review_at__lte=today) | Q(next_review_at__isnull=True))
        .select_related("piece")
    )


def _get_or_build_practice_order(request, all_due):
    """Return a session-stable randomised list of due bit PKs.

    Builds and stores the list on first call; subsequent calls within the same
    session reuse it so the order stays stable across PRG redirects.
    """
    order = request.session.get("practice_order")
    due_pks = set(all_due.values_list("pk", flat=True))
    if order:
        # Prune PKs that are no longer due
        order = [pk for pk in order if pk in due_pks]
    if not order:
        order = list(due_pks)
        random.shuffle(order)
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

    today = date.today()
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

    profile = get_active_profile(request)
    today = date.today()

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
