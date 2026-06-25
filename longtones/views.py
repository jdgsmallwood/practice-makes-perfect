from datetime import date, datetime, timezone

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_active_profile
from .models import LongToneLog, LongToneSession
from .utils import (
    FOCUS_CHOICES,
    FOCUS_PROMPTS,
    FOCUS_QUESTION,
    MIDI_NAMES,
    midi_to_hz,
    session_notes_for_date,
)


def _instrument_range(profile):
    if profile and profile.instrument:
        return profile.instrument.midi_low, profile.instrument.midi_high
    return 60, 96


@login_required
def home(request):
    profile = get_active_profile(request)
    midi_low, midi_high = _instrument_range(profile)

    if request.method == "POST":
        focus = request.POST.get("focus", "")
        valid_focuses = {v for v, _ in FOCUS_CHOICES}
        if focus not in valid_focuses:
            return redirect("longtones:home")

        use_drone = request.POST.get("use_drone") == "on"
        today = date.today()
        queue = session_notes_for_date(today, midi_low=midi_low, midi_high=midi_high)

        session_obj = LongToneSession.objects.create(
            profile=profile,
            date=today,
            focus=focus,
            use_drone=use_drone,
        )
        request.session["lt_session"] = {
            "session_id": session_obj.pk,
            "queue": queue,
            "total": len(queue),
        }
        return redirect("longtones:session")

    today_notes = [
        {"midi": m, "name": MIDI_NAMES[m]}
        for m in session_notes_for_date(midi_low=midi_low, midi_high=midi_high)
    ]

    weakness_map = {}
    if profile:
        rows = (
            LongToneLog.objects
            .filter(session__profile=profile)
            .values("midi", "note_name")
            .annotate(avg_rating=Avg("rating"), count=Count("midi"))
            .order_by("midi")
        )
        for row in rows:
            weakness_map[row["midi"]] = {
                "note_name": row["note_name"],
                "avg_rating": row["avg_rating"],
                "count": row["count"],
            }

    # Attach weakness data to today's notes
    for note in today_notes:
        note["wm"] = weakness_map.get(note["midi"])

    focus_items = [
        {"value": v, "label": l, "prompt": FOCUS_PROMPTS[v]}
        for v, l in FOCUS_CHOICES
    ]

    return render(request, "longtones/home.html", {
        "today_notes": today_notes,
        "note_count": len(today_notes),
        "focus_items": focus_items,
        "weakness_map": sorted(weakness_map.values(), key=lambda r: r["note_name"]),
    })


@login_required
def session(request):
    lt = request.session.get("lt_session")
    if not lt or not lt.get("queue"):
        return redirect("longtones:home")

    profile = get_active_profile(request)
    session_obj = get_object_or_404(LongToneSession, pk=lt["session_id"], profile=profile)

    current_midi = lt["queue"][0]
    note_name = MIDI_NAMES[current_midi]
    hz = midi_to_hz(current_midi)

    remaining = len(lt["queue"])
    total = lt["total"]
    pct = round(remaining * 100 / total) if total else 100

    return render(request, "longtones/session.html", {
        "session_obj": session_obj,
        "current_midi": current_midi,
        "note_name": note_name,
        "hz": hz,
        "remaining": remaining,
        "total": total,
        "pct": pct,
        "focus_prompt": FOCUS_PROMPTS[session_obj.focus],
        "focus_question": FOCUS_QUESTION[session_obj.focus],
        "rating_range": range(1, 6),
    })


@login_required
def log_note(request):
    if request.method != "POST":
        return redirect("longtones:session")

    lt = request.session.get("lt_session")
    if not lt:
        return redirect("longtones:home")

    try:
        session_id = int(request.POST["session_id"])
        midi = int(request.POST["midi"])
        rating = int(request.POST["rating"])
    except (KeyError, ValueError):
        return redirect("longtones:session")

    if not (1 <= rating <= 5):
        return redirect("longtones:session")

    profile = get_active_profile(request)
    session_obj = get_object_or_404(LongToneSession, pk=session_id, profile=profile)

    LongToneLog.objects.create(
        session=session_obj,
        midi=midi,
        note_name=MIDI_NAMES.get(midi, str(midi)),
        rating=rating,
    )

    queue = list(lt["queue"])
    if queue and queue[0] == midi:
        queue.pop(0)

    if not queue:
        session_obj.completed_at = datetime.now(tz=timezone.utc)
        session_obj.save(update_fields=["completed_at"])
        request.session.pop("lt_session", None)
        return redirect("longtones:complete")

    request.session["lt_session"] = {
        "session_id": lt["session_id"],
        "queue": queue,
        "total": lt["total"],
    }
    return redirect("longtones:session")


@login_required
def skip(request):
    if request.method != "POST":
        return redirect("longtones:session")

    lt = request.session.get("lt_session")
    if not lt or not lt.get("queue"):
        return redirect("longtones:home")

    queue = list(lt["queue"])
    if len(queue) > 1:
        queue.append(queue.pop(0))

    request.session["lt_session"] = {
        "session_id": lt["session_id"],
        "queue": queue,
        "total": lt["total"],
    }
    return redirect("longtones:session")


@login_required
def complete(request):
    request.session.pop("lt_session", None)
    profile = get_active_profile(request)

    session_obj = (
        LongToneSession.objects
        .filter(profile=profile, completed_at__isnull=False)
        .order_by("-completed_at")
        .first()
    )

    logs = []
    avg_rating = None
    if session_obj:
        logs = list(session_obj.logs.all())
        if logs:
            avg_rating = round(sum(l.rating for l in logs) / len(logs), 1)

    return render(request, "longtones/complete.html", {
        "session_obj": session_obj,
        "logs": logs,
        "avg_rating": avg_rating,
        "rating_range": range(1, 6),
    })
