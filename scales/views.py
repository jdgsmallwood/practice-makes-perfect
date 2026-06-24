import json
import random
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Min, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_active_profile
from practice.algorithm import SM2State, apply_rating, calculate_tempo_ladder
from .catalog import ROOTS
from .models import ScaleLog, ScalePractice, ScaleType


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_or_create_practice(profile, scale_type_id, root):
    sp, _ = ScalePractice.objects.get_or_create(
        profile=profile,
        scale_type_id=scale_type_id,
        root=root,
    )
    return sp


def _get_rotation_order(request, enabled_pks):
    """Session-stable shuffle for rotation mode."""
    order = request.session.get("scales_rotation_order")
    pk_set = set(enabled_pks)
    if order:
        order = [pk for pk in order if pk in pk_set]
    if not order:
        order = list(pk_set)
        random.shuffle(order)
    request.session["scales_rotation_order"] = order
    return order


# ── Settings view (toggle on/off) ────────────────────────────────────────────

@login_required
def settings_view(request):
    from collections import defaultdict
    profile = get_active_profile(request)

    # Build enabled map: {scale_type_id: {root: sp_pk}}
    enabled_map = defaultdict(dict)
    if profile:
        for sp in ScalePractice.objects.filter(profile=profile, enabled=True):
            enabled_map[sp.scale_type_id][sp.root] = sp.pk

    scale_types = list(ScaleType.objects.all().order_by("category", "name"))

    by_category = {}
    for st in scale_types:
        if st.category not in by_category:
            by_category[st.category] = []
        by_category[st.category].append({
            "scale_type": st,
            "enabled_roots": dict(enabled_map.get(st.pk, {})),
        })

    return render(request, "scales/settings.html", {
        "catalog_by_category": by_category,
        "roots": ROOTS,
    })


@login_required
def toggle_scale(request, scale_type_id, root):
    """HTMX: toggle a (scale_type, root) combination on/off."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    profile = get_active_profile(request)
    if not profile:
        return JsonResponse({"error": "No active profile"}, status=400)

    scale_type = get_object_or_404(ScaleType, pk=scale_type_id)
    if not (0 <= root <= 11):
        return JsonResponse({"error": "Invalid root"}, status=400)

    sp = _get_or_create_practice(profile, scale_type_id, root)
    sp.enabled = not sp.enabled
    sp.save(update_fields=["enabled"])

    return render(request, "scales/partials/_toggle_cell.html", {
        "scale_type": scale_type,
        "root_index": root,
        "root_name": ROOTS[root],
        "sp": sp if sp.enabled else None,
    })


# ── Rotation practice ────────────────────────────────────────────────────────

@login_required
def rotation_session(request):
    profile = get_active_profile(request)
    enabled_practices = list(
        ScalePractice.objects.filter(profile=profile, enabled=True).select_related("scale_type")
    )
    if not enabled_practices:
        return render(request, "scales/rotation_empty.html", {})

    enabled_pks = [sp.pk for sp in enabled_practices]
    order = _get_rotation_order(request, enabled_pks)
    sp_map = {sp.pk: sp for sp in enabled_practices}

    sp = None
    for pk in order:
        if pk in sp_map:
            sp = sp_map[pk]
            break

    if sp is None:
        request.session.pop("scales_rotation_order", None)
        return redirect("scales:rotation_complete")

    ladder = calculate_tempo_ladder(sp.current_tempo, sp.desired_tempo)

    return render(request, "scales/rotation_session.html", {
        "sp": sp,
        "roots": ROOTS,
        "remaining": len(order),
        "total": len(enabled_pks),
        "ladder_json": json.dumps(ladder),
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if sp.current_tempo and t > sp.current_tempo),
            None,
        ),
    })


@login_required
def rotation_log(request):
    """Record a rotation rep result (Got it / Too fast)."""
    if request.method != "POST":
        return redirect("scales:rotation_session")

    try:
        sp_id = int(request.POST["sp_id"])
    except (KeyError, ValueError):
        return redirect("scales:rotation_session")

    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=sp_id, profile=profile)

    achieved_raw = request.POST.get("achieved_tempo", "").strip()
    achieved_tempo = None
    if achieved_raw:
        try:
            t = int(achieved_raw)
            if 20 <= t <= 400:
                achieved_tempo = t
        except ValueError:
            pass

    if achieved_tempo:
        if sp.fastest_tempo is None or achieved_tempo > sp.fastest_tempo:
            sp.fastest_tempo = achieved_tempo
        sp.current_tempo = achieved_tempo
        sp.save(update_fields=["fastest_tempo", "current_tempo"])

    ScaleLog.objects.create(scale_practice=sp, achieved_tempo=achieved_tempo)

    # Advance the rotation order
    order = list(request.session.get("scales_rotation_order", []))
    if sp_id in order:
        order.remove(sp_id)
    request.session["scales_rotation_order"] = order

    if not order:
        return redirect("scales:rotation_complete")
    return redirect("scales:rotation_session")


@login_required
def rotation_complete(request):
    request.session.pop("scales_rotation_order", None)
    profile = get_active_profile(request)
    enabled_count = ScalePractice.objects.filter(profile=profile, enabled=True).count() if profile else 0
    return render(request, "scales/rotation_complete.html", {"enabled_count": enabled_count})


# ── SM-2 scale practice ──────────────────────────────────────────────────────

@login_required
def sm2_session(request):
    profile = get_active_profile(request)
    today = date.today()
    due = list(
        ScalePractice.objects.filter(
            profile=profile,
            sm2_enabled=True,
        ).filter(
            Q(next_review_at__lte=today) | Q(next_review_at__isnull=True)
        ).select_related("scale_type")
    )

    if not due:
        return render(request, "scales/sm2_empty.html", {})

    order = request.session.get("scales_sm2_order")
    due_pks = {sp.pk for sp in due}
    if order:
        order = [pk for pk in order if pk in due_pks]
    if not order:
        order = list(due_pks)
        random.shuffle(order)
    request.session["scales_sm2_order"] = order

    sp_map = {sp.pk: sp for sp in due}
    sp = sp_map.get(order[0]) if order else None

    if sp is None:
        request.session.pop("scales_sm2_order", None)
        return redirect("scales:sm2_complete")

    state = SM2State(
        ease_factor=sp.ease_factor,
        interval_days=sp.interval_days,
        repetitions=sp.repetitions,
        next_review_at=sp.next_review_at,
    )
    preview_intervals = {r: apply_rating(state, r, today=today).interval_days for r in [1, 2, 3, 4]}
    ladder = calculate_tempo_ladder(sp.current_tempo, sp.desired_tempo)

    return render(request, "scales/sm2_session.html", {
        "sp": sp,
        "roots": ROOTS,
        "due_count": len(order),
        "preview_intervals": preview_intervals,
        "ladder_json": json.dumps(ladder),
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if sp.current_tempo and t > sp.current_tempo),
            None,
        ),
    })


@login_required
def sm2_rate(request):
    if request.method != "POST":
        return redirect("scales:sm2_session")

    try:
        sp_id = int(request.POST["sp_id"])
        rating = int(request.POST["rating"])
    except (KeyError, ValueError):
        return redirect("scales:sm2_session")

    if rating not in (1, 2, 3, 4):
        return redirect("scales:sm2_session")

    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=sp_id, profile=profile)
    interval_before = sp.interval_days

    state = SM2State(
        ease_factor=sp.ease_factor,
        interval_days=sp.interval_days,
        repetitions=sp.repetitions,
        next_review_at=sp.next_review_at,
    )
    new_state = apply_rating(state, rating)
    sp.ease_factor = new_state.ease_factor
    sp.interval_days = new_state.interval_days
    sp.repetitions = new_state.repetitions
    sp.next_review_at = new_state.next_review_at

    update_fields = ["ease_factor", "interval_days", "repetitions", "next_review_at"]

    achieved_raw = request.POST.get("achieved_tempo", "").strip()
    achieved_tempo = None
    if achieved_raw:
        try:
            t = int(achieved_raw)
            if 20 <= t <= 400:
                achieved_tempo = t
                sp.current_tempo = t
                update_fields.append("current_tempo")
                if sp.fastest_tempo is None or t > sp.fastest_tempo:
                    sp.fastest_tempo = t
                    update_fields.append("fastest_tempo")
        except ValueError:
            pass

    sp.save(update_fields=update_fields)

    ScaleLog.objects.create(
        scale_practice=sp,
        achieved_tempo=achieved_tempo,
        rating=rating,
        interval_before=interval_before,
        interval_after=new_state.interval_days,
    )

    order = list(request.session.get("scales_sm2_order", []))
    if sp_id in order:
        order.remove(sp_id)
    request.session["scales_sm2_order"] = order

    if not order:
        return redirect("scales:sm2_complete")
    return redirect("scales:sm2_session")


@login_required
def sm2_complete(request):
    request.session.pop("scales_sm2_order", None)
    today = date.today()
    profile = get_active_profile(request)
    next_due = None
    if profile:
        next_due = ScalePractice.objects.filter(
            profile=profile,
            sm2_enabled=True,
            next_review_at__isnull=False,
            next_review_at__gt=today,
        ).aggregate(Min("next_review_at"))["next_review_at__min"]
    return render(request, "scales/sm2_complete.html", {"next_due": next_due})


# ── SM-2 toggle ──────────────────────────────────────────────────────────────

@login_required
def toggle_sm2(request, sp_id):
    if request.method != "POST":
        return redirect("scales:detail", pk=sp_id)
    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=sp_id, profile=profile)
    sp.sm2_enabled = not sp.sm2_enabled
    sp.save(update_fields=["sm2_enabled"])
    return redirect("scales:detail", pk=sp_id)


# ── Detail view ──────────────────────────────────────────────────────────────

@login_required
def detail(request, pk):
    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=pk, profile=profile)
    logs = sp.logs.order_by("-reviewed_at")[:50]

    intervals_json = json.dumps(sp.scale_type.intervals)
    return render(request, "scales/detail.html", {
        "sp": sp,
        "roots": ROOTS,
        "logs": logs,
        "intervals_json": intervals_json,
        "root_index": sp.root,
    })


@login_required
def set_tempo(request, pk):
    """Set desired/current tempo for a ScalePractice."""
    if request.method != "POST":
        return redirect("scales:detail", pk=pk)
    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=pk, profile=profile)

    update_fields = []
    for field in ("desired_tempo", "current_tempo"):
        val = request.POST.get(field, "").strip()
        if val:
            try:
                t = int(val)
                if 20 <= t <= 400:
                    setattr(sp, field, t)
                    update_fields.append(field)
            except ValueError:
                pass
        elif val == "":
            setattr(sp, field, None)
            update_fields.append(field)

    if update_fields:
        sp.save(update_fields=update_fields)
    return redirect("scales:detail", pk=pk)
