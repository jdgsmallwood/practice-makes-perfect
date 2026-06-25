from datetime import date, datetime, timezone

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_active_profile
from .models import ArticulationLog, ArticulationSession
from .utils import EXERCISES, TRACK_CHOICES, queue_for_track


@login_required
def home(request):
    profile = get_active_profile(request)

    if request.method == "POST":
        track = request.POST.get("track", "")
        valid_tracks = {v for v, _ in TRACK_CHOICES}
        if track not in valid_tracks:
            return redirect("articulation:home")

        queue = queue_for_track(track)
        session_obj = ArticulationSession.objects.create(
            profile=profile,
            date=date.today(),
            track=track,
        )
        request.session["art_session"] = {
            "session_id": session_obj.pk,
            "queue":      queue,
            "total":      len(queue),
        }
        return redirect("articulation:session")

    history = {}
    if profile:
        rows = (
            ArticulationLog.objects
            .filter(session__profile=profile)
            .values("exercise_id")
            .annotate(avg_rating=Avg("rating"), count=Count("exercise_id"))
        )
        history = {r["exercise_id"]: r for r in rows}

    exercise_list = [
        {**ex, "history": history.get(ex_id)}
        for ex_id, ex in EXERCISES.items()
    ]

    return render(request, "articulation/home.html", {
        "exercise_list": exercise_list,
        "track_choices": TRACK_CHOICES,
    })


@login_required
def session(request):
    art = request.session.get("art_session")
    if not art or not art.get("queue"):
        return redirect("articulation:home")

    profile = get_active_profile(request)
    session_obj = get_object_or_404(ArticulationSession, pk=art["session_id"], profile=profile)

    current_id = art["queue"][0]
    exercise = EXERCISES[current_id]

    remaining = len(art["queue"])
    total     = art["total"]
    pct       = round((total - remaining + 1) * 100 / total) if total else 100

    return render(request, "articulation/session.html", {
        "session_obj":  session_obj,
        "exercise":     exercise,
        "remaining":    remaining,
        "total":        total,
        "pct":          pct,
        "rating_range": range(1, 6),
    })


@login_required
def log_exercise(request):
    if request.method != "POST":
        return redirect("articulation:session")

    art = request.session.get("art_session")
    if not art:
        return redirect("articulation:home")

    try:
        session_id  = int(request.POST["session_id"])
        exercise_id = request.POST["exercise_id"]
        rating      = int(request.POST["rating"])
    except (KeyError, ValueError):
        return redirect("articulation:session")

    if exercise_id not in EXERCISES or not (1 <= rating <= 5):
        return redirect("articulation:session")

    profile = get_active_profile(request)
    session_obj = get_object_or_404(ArticulationSession, pk=session_id, profile=profile)

    ArticulationLog.objects.create(
        session=session_obj,
        exercise_id=exercise_id,
        rating=rating,
    )

    queue = list(art["queue"])
    if queue and queue[0] == exercise_id:
        queue.pop(0)

    if not queue:
        session_obj.completed_at = datetime.now(tz=timezone.utc)
        session_obj.save(update_fields=["completed_at"])
        request.session.pop("art_session", None)
        return redirect("articulation:complete")

    request.session["art_session"] = {
        "session_id": art["session_id"],
        "queue":      queue,
        "total":      art["total"],
    }
    return redirect("articulation:session")


@login_required
def skip(request):
    if request.method != "POST":
        return redirect("articulation:session")

    art = request.session.get("art_session")
    if not art or not art.get("queue"):
        return redirect("articulation:home")

    queue = list(art["queue"])
    if len(queue) > 1:
        queue.append(queue.pop(0))

    request.session["art_session"] = {
        "session_id": art["session_id"],
        "queue":      queue,
        "total":      art["total"],
    }
    return redirect("articulation:session")


@login_required
def complete(request):
    request.session.pop("art_session", None)
    profile = get_active_profile(request)

    session_obj = (
        ArticulationSession.objects
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

    enriched_logs = [
        {"log": l, "exercise": EXERCISES.get(l.exercise_id, {})}
        for l in logs
    ]

    return render(request, "articulation/complete.html", {
        "session_obj":   session_obj,
        "enriched_logs": enriched_logs,
        "avg_rating":    avg_rating,
        "rating_range":  range(1, 6),
    })
