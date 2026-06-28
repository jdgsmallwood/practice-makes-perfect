from datetime import datetime, timezone

from django.utils import timezone as dj_timezone

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.utils import get_active_profile
from scales.models import ScalePractice
from .models import PracticeSession

CATEGORY_CONFIG = {
    "trickybit": {
        "label": "Tricky Passages",
        "min_minutes": 5,
        "max_minutes": 20,
        "mins_per_item": 3,
        "url_name": "practice:session",
    },
    "scales_rotation": {
        "label": "Scales",
        "min_minutes": 5,
        "max_minutes": 15,
        "mins_per_item": 1,
        "url_name": "scales:rotation_session",
    },
    "longtones": {
        "label": "Long Tones",
        "min_minutes": 5,
        "max_minutes": 15,
        "mins_per_item": 0,
        "url_name": "longtones:home",
    },
    "articulation": {
        "label": "Articulation",
        "min_minutes": 5,
        "max_minutes": 15,
        "mins_per_item": 0,
        "url_name": "articulation:home",
    },
}

VALID_CATEGORIES = list(CATEGORY_CONFIG.keys())


def allocate_time(total_minutes, selected_categories, due_counts):
    """Distribute total_minutes across selected categories.

    SM-2 categories are weighted by their due-item count; always-available
    categories (longtones, articulation) each get weight 1.
    Each allocation is clamped to [min_minutes, max_minutes].
    Surplus/deficit from clamping is redistributed proportionally in one pass.
    """
    if not selected_categories:
        return []

    cfg = {cat: CATEGORY_CONFIG[cat] for cat in selected_categories}

    # Weights: SM-2 categories scale with due count; others fixed at 1
    weights = {}
    for cat in selected_categories:
        count = due_counts.get(cat, 0)
        weights[cat] = max(count, 1) if cfg[cat]["mins_per_item"] > 0 else 1

    total_weight = sum(weights.values())

    raw = {cat: weights[cat] / total_weight * total_minutes for cat in selected_categories}

    # First-pass clamp
    allocated = {}
    clamped_sum = 0
    for cat in selected_categories:
        clamped = max(cfg[cat]["min_minutes"], min(cfg[cat]["max_minutes"], raw[cat]))
        allocated[cat] = clamped
        clamped_sum += clamped

    # Redistribute difference
    diff = total_minutes - clamped_sum
    if diff != 0:
        flexible = [
            c for c in selected_categories
            if cfg[c]["min_minutes"] < allocated[c] < cfg[c]["max_minutes"]
        ]
        if flexible:
            per = diff / len(flexible)
            for cat in flexible:
                new_val = allocated[cat] + per
                allocated[cat] = max(cfg[cat]["min_minutes"], min(cfg[cat]["max_minutes"], new_val))

    sections = []
    for cat in selected_categories:
        sections.append({
            "category": cat,
            "label": cfg[cat]["label"],
            "minutes": round(allocated[cat]),
            "start_url": reverse(cfg[cat]["url_name"]),
            "item_count": due_counts.get(cat, 0),
            "completed_at": None,
        })
    return sections


def _get_due_counts(profile):
    """Return dict of due-item counts per category for the given profile."""
    today = dj_timezone.localdate()
    from pieces.models import TrickyBit

    trickybit_count = (
        TrickyBit.objects.filter(piece__is_active=True, piece__profile=profile)
        .filter(Q(next_review_at__lte=today) | Q(next_review_at__isnull=True))
        .count()
        if profile
        else 0
    )
    scales_rotation_count = (
        ScalePractice.objects.filter(profile=profile, enabled=True).count()
        if profile
        else 0
    )
    return {
        "trickybit": trickybit_count,
        "scales_rotation": scales_rotation_count,
        "longtones": 0,
        "articulation": 0,
    }


@login_required
def plan_setup(request):
    profile = get_active_profile(request)
    due_counts = _get_due_counts(profile)
    error = None

    if request.method == "POST":
        # Validate total_minutes
        try:
            total_minutes = int(request.POST.get("total_minutes", ""))
            if not (5 <= total_minutes <= 180):
                raise ValueError
        except (ValueError, TypeError):
            error = "Please enter a time between 5 and 180 minutes."

        selected = [c for c in VALID_CATEGORIES if request.POST.get(f"cat_{c}")]
        if not selected and error is None:
            error = "Please select at least one practice category."

        if error is None:
            sections = allocate_time(total_minutes, selected, due_counts)
            session = PracticeSession.objects.create(
                profile=profile,
                total_minutes_planned=total_minutes,
                categories_json=selected,
                sections_json=sections,
            )
            request.session["planner_state"] = {
                "session_id": session.pk,
                "total_minutes": total_minutes,
                "sections": sections,
            }
            return redirect("planner:overview")

    return render(request, "planner/setup.html", {
        "categories": [
            {
                "key": cat,
                "label": CATEGORY_CONFIG[cat]["label"],
                "due_count": due_counts[cat],
                "always_on": CATEGORY_CONFIG[cat]["mins_per_item"] == 0,
            }
            for cat in VALID_CATEGORIES
        ],
        "quick_times": [15, 30, 45, 60, 90],
        "error": error,
    })


@login_required
def plan_overview(request):
    state = request.session.get("planner_state")
    if not state:
        return redirect("planner:setup")

    sections = state["sections"]
    completed_count = sum(1 for s in sections if s["completed_at"] is not None)

    if completed_count == len(sections):
        return redirect("planner:complete")

    current_section = next((s for s in sections if s["completed_at"] is None), None)

    return render(request, "planner/overview.html", {
        "sections": sections,
        "current_section": current_section,
        "completed_count": completed_count,
        "total_count": len(sections),
        "total_minutes": state["total_minutes"],
    })


@login_required
def plan_section_done(request):
    state = request.session.get("planner_state")
    if not state:
        return redirect("planner:overview")

    for section in state["sections"]:
        if section["completed_at"] is None:
            section["completed_at"] = datetime.now(tz=timezone.utc).isoformat()
            break

    request.session["planner_state"] = state
    PracticeSession.objects.filter(pk=state["session_id"]).update(
        sections_json=state["sections"]
    )
    return redirect("planner:overview")


@login_required
def plan_complete(request):
    state = request.session.pop("planner_state", None)
    if state:
        PracticeSession.objects.filter(pk=state["session_id"]).update(
            finished_at=datetime.now(tz=timezone.utc),
            sections_json=state["sections"],
        )

    return render(request, "planner/complete.html", {
        "sections": state["sections"] if state else [],
        "total_minutes": state["total_minutes"] if state else 0,
        "completed_count": (
            sum(1 for s in state["sections"] if s["completed_at"] is not None)
            if state
            else 0
        ),
    })


@login_required
def plan_abandon(request):
    if request.method != "POST":
        return redirect("planner:overview")
    request.session.pop("planner_state", None)
    return redirect("pieces:dashboard")
