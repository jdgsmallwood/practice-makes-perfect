from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as dj_timezone

from accounts.utils import get_active_profile
from .models import TransitionLog, TransitionPractice, TransitionSession
from .utils import (
    DRILLS,
    MAX_ACTIVE,
    build_session_queue,
    midi_to_hz,
    normalize_pair,
    selectable_notes,
)


def _instrument_range(profile):
    instrument = getattr(profile, "instrument", None)
    return (
        getattr(instrument, "midi_low", 60) or 60,
        getattr(instrument, "midi_high", 96) or 96,
    )


def _next_position(profile, status):
    last = (
        TransitionPractice.objects
        .filter(profile=profile, status=status)
        .order_by("-position")
        .first()
    )
    return (last.position + 1) if last else 1


def _promote_next_queued(profile):
    active_count = TransitionPractice.objects.filter(
        profile=profile,
        status=TransitionPractice.STATUS_ACTIVE,
    ).count()
    if active_count >= MAX_ACTIVE:
        return None

    next_queued = (
        TransitionPractice.objects
        .filter(profile=profile, status=TransitionPractice.STATUS_QUEUED)
        .order_by("position", "created_at")
        .first()
    )
    if not next_queued:
        return None

    next_queued.status = TransitionPractice.STATUS_ACTIVE
    next_queued.position = _next_position(profile, TransitionPractice.STATUS_ACTIVE)
    next_queued.save(update_fields=["status", "position"])
    return next_queued


@login_required
def home(request):
    profile = get_active_profile(request)
    if not profile:
        messages.error(request, "Select or create a profile before practicing transitions.")
        return redirect("accounts:profile_list")

    if request.method == "POST":
        active = TransitionPractice.objects.filter(
            profile=profile,
            status=TransitionPractice.STATUS_ACTIVE,
        ).order_by("position", "created_at")
        queue = build_session_queue(active)
        if not queue:
            messages.error(request, "Add at least one active transition before starting.")
            return redirect("transitions:home")

        session_obj = TransitionSession.objects.create(
            profile=profile,
            date=dj_timezone.localdate(),
        )
        request.session["transition_session"] = {
            "session_id": session_obj.pk,
            "queue": queue,
            "total": len(queue),
        }
        return redirect("transitions:session")

    active = list(TransitionPractice.objects.filter(
        profile=profile,
        status=TransitionPractice.STATUS_ACTIVE,
    ).order_by("position", "created_at"))
    queued = list(TransitionPractice.objects.filter(
        profile=profile,
        status=TransitionPractice.STATUS_QUEUED,
    ).order_by("position", "created_at"))
    retired = list(TransitionPractice.objects.filter(
        profile=profile,
        status=TransitionPractice.STATUS_RETIRED,
    ).order_by("-created_at")[:5])

    history_rows = (
        TransitionLog.objects
        .filter(transition_practice__profile=profile)
        .values("transition_practice_id")
        .annotate(avg_rating=Avg("rating"), count=Count("id"))
    )
    history = {row["transition_practice_id"]: row for row in history_rows}

    for practice in active + queued + retired:
        practice.history = history.get(practice.pk)

    midi_low, midi_high = _instrument_range(profile)
    return render(request, "transitions/home.html", {
        "active": active,
        "queued": queued,
        "retired": retired,
        "notes": selectable_notes(midi_low, midi_high),
        "max_active": MAX_ACTIVE,
    })


@login_required
def add_transition(request):
    if request.method != "POST":
        return redirect("transitions:home")

    profile = get_active_profile(request)
    if not profile:
        return redirect("accounts:profile_list")

    midi_low, midi_high = _instrument_range(profile)
    try:
        note_low, note_high = normalize_pair(request.POST["note_a"], request.POST["note_b"])
    except (KeyError, ValueError):
        messages.error(request, "Choose two notes for the transition.")
        return redirect("transitions:home")

    if note_low == note_high:
        messages.error(request, "Choose two different notes.")
        return redirect("transitions:home")
    if note_low < midi_low or note_high > midi_high:
        messages.error(request, "Choose notes within the active profile's instrument range.")
        return redirect("transitions:home")
    if TransitionPractice.objects.filter(profile=profile, note_low=note_low, note_high=note_high).exists():
        messages.error(request, "That transition is already in your queue.")
        return redirect("transitions:home")

    active_count = TransitionPractice.objects.filter(
        profile=profile,
        status=TransitionPractice.STATUS_ACTIVE,
    ).count()
    status = (
        TransitionPractice.STATUS_ACTIVE
        if active_count < MAX_ACTIVE
        else TransitionPractice.STATUS_QUEUED
    )
    TransitionPractice.objects.create(
        profile=profile,
        note_low=note_low,
        note_high=note_high,
        status=status,
        position=_next_position(profile, status),
    )
    return redirect("transitions:home")


@login_required
def retire_transition(request):
    if request.method != "POST":
        return redirect("transitions:home")

    profile = get_active_profile(request)
    practice = get_object_or_404(TransitionPractice, pk=request.POST.get("transition_id"), profile=profile)
    was_active = practice.status == TransitionPractice.STATUS_ACTIVE
    practice.status = TransitionPractice.STATUS_RETIRED
    practice.position = _next_position(profile, TransitionPractice.STATUS_RETIRED)
    practice.save(update_fields=["status", "position"])
    if was_active:
        _promote_next_queued(profile)
    return redirect("transitions:home")


@login_required
def remove_transition(request):
    if request.method != "POST":
        return redirect("transitions:home")

    profile = get_active_profile(request)
    practice = get_object_or_404(TransitionPractice, pk=request.POST.get("transition_id"), profile=profile)
    was_active = practice.status == TransitionPractice.STATUS_ACTIVE
    practice.delete()
    if was_active:
        _promote_next_queued(profile)
    return redirect("transitions:home")


@login_required
def session(request):
    state = request.session.get("transition_session")
    if not state or not state.get("queue"):
        return redirect("transitions:home")

    profile = get_active_profile(request)
    session_obj = get_object_or_404(TransitionSession, pk=state["session_id"], profile=profile)
    current = state["queue"][0]
    practice = get_object_or_404(TransitionPractice, pk=current["transition_id"], profile=profile)
    exercise = DRILLS[current["exercise_id"]]
    remaining = len(state["queue"])
    total = state["total"]
    pct = round((total - remaining + 1) * 100 / total) if total else 100

    instrument = getattr(profile, "instrument", None)
    return render(request, "transitions/session.html", {
        "session_obj": session_obj,
        "transition": practice,
        "exercise": exercise,
        "note_low_hz": round(midi_to_hz(practice.note_low), 1),
        "note_high_hz": round(midi_to_hz(practice.note_high), 1),
        "instrument_slug": getattr(instrument, "slug", "flute") or "flute",
        "remaining": remaining,
        "total": total,
        "pct": pct,
        "rating_range": range(1, 6),
    })


@login_required
def log_transition(request):
    if request.method != "POST":
        return redirect("transitions:session")

    state = request.session.get("transition_session")
    if not state:
        return redirect("transitions:home")

    try:
        session_id = int(request.POST["session_id"])
        transition_id = int(request.POST["transition_id"])
        exercise_id = request.POST["exercise_id"]
        rating = int(request.POST["rating"])
    except (KeyError, ValueError):
        return redirect("transitions:session")

    if exercise_id not in DRILLS or not (1 <= rating <= 5):
        return redirect("transitions:session")

    profile = get_active_profile(request)
    session_obj = get_object_or_404(TransitionSession, pk=session_id, profile=profile)
    practice = get_object_or_404(TransitionPractice, pk=transition_id, profile=profile)

    achieved_tempo = None
    if DRILLS[exercise_id].get("prompts_tempo") and request.POST.get("achieved_tempo"):
        try:
            achieved_tempo = int(request.POST["achieved_tempo"])
        except ValueError:
            achieved_tempo = None
        if achieved_tempo is not None and not (30 <= achieved_tempo <= 240):
            achieved_tempo = None

    TransitionLog.objects.create(
        session=session_obj,
        transition_practice=practice,
        exercise_id=exercise_id,
        rating=rating,
        achieved_tempo=achieved_tempo,
    )

    if achieved_tempo is not None:
        practice.current_tempo = achieved_tempo
        practice.fastest_tempo = max(practice.fastest_tempo or 0, achieved_tempo)
        practice.save(update_fields=["current_tempo", "fastest_tempo"])

    queue = list(state["queue"])
    if queue and queue[0] == {"transition_id": transition_id, "exercise_id": exercise_id}:
        queue.pop(0)

    if not queue:
        session_obj.completed_at = datetime.now(tz=timezone.utc)
        session_obj.save(update_fields=["completed_at"])
        request.session.pop("transition_session", None)
        return redirect("transitions:complete")

    request.session["transition_session"] = {
        "session_id": state["session_id"],
        "queue": queue,
        "total": state["total"],
    }
    return redirect("transitions:session")


@login_required
def skip(request):
    if request.method != "POST":
        return redirect("transitions:session")

    state = request.session.get("transition_session")
    if not state or not state.get("queue"):
        return redirect("transitions:home")

    queue = list(state["queue"])
    if len(queue) > 1:
        queue.append(queue.pop(0))

    request.session["transition_session"] = {
        "session_id": state["session_id"],
        "queue": queue,
        "total": state["total"],
    }
    return redirect("transitions:session")


@login_required
def complete(request):
    request.session.pop("transition_session", None)
    if request.session.get("planner_state"):
        return redirect("planner:section_done")

    profile = get_active_profile(request)
    session_obj = (
        TransitionSession.objects
        .filter(profile=profile, completed_at__isnull=False)
        .order_by("-completed_at")
        .first()
    )
    logs = list(session_obj.logs.select_related("transition_practice").all()) if session_obj else []
    avg_rating = round(sum(log.rating for log in logs) / len(logs), 1) if logs else None
    enriched_logs = [
        {"log": log, "exercise": DRILLS.get(log.exercise_id, {})}
        for log in logs
    ]
    return render(request, "transitions/complete.html", {
        "session_obj": session_obj,
        "enriched_logs": enriched_logs,
        "avg_rating": avg_rating,
        "rating_range": range(1, 6),
    })
