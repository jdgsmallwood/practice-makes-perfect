import json
import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_active_profile
from practice.algorithm import calculate_tempo_ladder
from .catalog import ROOTS
from .models import ScaleLog, ScalePractice, ScaleType


# ── Helpers ─────────────────────────────────────────────────────────────────

# Priority signal weights. tempo + peer + smoothness form a budget summing to 10
# (smoothness is the dependent remainder); new_boost is a separate additive 0-10.
DEFAULT_SCALE_WEIGHTS = {"tempo": 6, "peer": 3, "smoothness": 1, "new_boost": 7}


def get_scale_weights(profile) -> dict:
    """Merge a profile's stored weights over defaults; values clamped to 0-10 ints."""
    w = dict(DEFAULT_SCALE_WEIGHTS)
    if profile and isinstance(profile.scale_weights, dict):
        for k in w:
            v = profile.scale_weights.get(k)
            if isinstance(v, (int, float)):
                w[k] = max(0, min(10, int(v)))
    return w


def _get_or_create_practice(profile, scale_type_id, root):
    sp, _ = ScalePractice.objects.get_or_create(
        profile=profile,
        scale_type_id=scale_type_id,
        root=root,
    )
    return sp


def _compute_rotation_weights(enabled_practices: list, weights: dict) -> dict:
    """Return {pk: weight} where weight 1-3 controls appearances per lap.

    Signals (each 0..1, scaled by the user's tempo/peer/smoothness budget which
    sums to 10), plus an additive new-scale bonus:
      1. Tempo deficit vs goal
      2. Peer group lag — bottom quartile of root or type group
      3. Smoothness — inverted avg of last 3 ratings
      New scales (repetitions == 0) get an adjustable bonus for early introduction.
    """
    if not enabled_practices:
        return {}

    wt, wp, ws = weights["tempo"], weights["peer"], weights["smoothness"]
    total = wt + wp + ws
    if total <= 0:                       # malformed → fall back to defaults
        wt, wp, ws, total = 6, 3, 1, 10
    nt, np_, ns = wt / total, wp / total, ws / total
    new_bonus = weights["new_boost"] / 10 * 0.6   # 0.0–0.6 additive

    pks = [sp.pk for sp in enabled_practices]

    # Last 3 rated logs per practice (single query, grouped in Python)
    rows = (
        ScaleLog.objects
        .filter(scale_practice_id__in=pks, rating__isnull=False)
        .order_by("scale_practice_id", "-reviewed_at")
        .values_list("scale_practice_id", "rating")
    )
    ratings_by_pk: dict[int, list[int]] = {}
    for sp_id, rating in rows:
        bucket = ratings_by_pk.setdefault(sp_id, [])
        if len(bucket) < 3:
            bucket.append(rating)

    # Peer group maps
    by_root: dict[int, list] = {}
    by_type: dict[int, list] = {}
    for sp in enabled_practices:
        by_root.setdefault(sp.root, []).append(sp)
        by_type.setdefault(sp.scale_type_id, []).append(sp)

    def progress(sp):
        if sp.desired_tempo and sp.current_tempo:
            return sp.current_tempo / sp.desired_tempo
        return None

    def bottom_quartile(sp, group):
        ratios = sorted(r for r in (progress(s) for s in group) if r is not None)
        if len(ratios) < 2:
            return False
        my = progress(sp)
        return my is not None and my <= ratios[len(ratios) // 4]

    result = {}
    for sp in enabled_practices:
        # Signal 1: tempo deficit (0..1)
        if sp.desired_tempo and sp.current_tempo:
            td = max(0.0, 1 - (sp.current_tempo / sp.desired_tempo))
        elif sp.desired_tempo:
            td = 0.8   # goal set but never measured — needs establishing
        else:
            td = 0.5   # no goal — neutral

        # Signal 2: peer lag (binary 0/1)
        pl = 1.0 if (
            bottom_quartile(sp, by_root[sp.root]) or
            bottom_quartile(sp, by_type[sp.scale_type_id])
        ) else 0.0

        # Signal 3: smoothness (inverted rating avg, 0..1)
        r = ratings_by_pk.get(sp.pk, [])
        avg = sum(r) / len(r) if r else 2.5
        sd = (4 - avg) / 3

        raw = nt * td + np_ * pl + ns * sd

        if sp.repetitions == 0:
            raw += new_bonus   # new scale bonus — ensure early introduction

        result[sp.pk] = 3 if raw > 0.55 else (2 if raw >= 0.25 else 1)

    return result


def _build_weighted_order(enabled_practices: list, weights: dict) -> list:
    """Expand per-scale weights into a shuffled list of pks (repeated by weight)."""
    order: list[int] = []
    for sp in enabled_practices:
        order.extend([sp.pk] * weights.get(sp.pk, 1))
    random.shuffle(order)
    return order


def _get_rotation_order(request, enabled_practices: list) -> list:
    """Session-stable weighted queue for rotation mode.

    Resumes an in-progress lap; builds a fresh weighted lap when exhausted.
    """
    pk_set = {sp.pk for sp in enabled_practices}
    order = [pk for pk in request.session.get("scales_rotation_order", []) if pk in pk_set]
    if order:
        request.session["scales_rotation_order"] = order
        return order

    profile = get_active_profile(request)
    weights = _compute_rotation_weights(enabled_practices, get_scale_weights(profile))
    order = _build_weighted_order(enabled_practices, weights)
    request.session["scales_rotation_order"] = order
    return order


# ── Settings view (toggle on/off) ────────────────────────────────────────────

@login_required
def settings_view(request):
    from collections import defaultdict
    profile = get_active_profile(request)

    enabled_map = defaultdict(dict)
    roots_with_enabled = set()
    active_scales = []
    scale_weights = get_scale_weights(profile)

    if profile:
        enabled_practices = list(
            ScalePractice.objects.filter(profile=profile, enabled=True)
            .select_related("scale_type")
        )
        focus_map = _compute_rotation_weights(enabled_practices, scale_weights)

        for sp in enabled_practices:
            enabled_map[sp.scale_type_id][sp.root] = {
                "pk": sp.pk,
                "current_tempo": sp.current_tempo,
                "desired_tempo": sp.desired_tempo,
            }
            roots_with_enabled.add(sp.root)

            pct = None
            if sp.current_tempo and sp.desired_tempo:
                pct = min(100, int(sp.current_tempo / sp.desired_tempo * 100))
            active_scales.append({
                "pk": sp.pk,
                "name": str(sp),
                "current_tempo": sp.current_tempo,
                "desired_tempo": sp.desired_tempo,
                "pct": pct,
                "focus": focus_map.get(sp.pk, 1),
            })
        active_scales.sort(key=lambda x: (-x["focus"], x["name"]))

    scale_types = list(ScaleType.objects.all().order_by("category", "name"))

    by_category = {}
    for st in scale_types:
        if st.category not in by_category:
            by_category[st.category] = []
        by_category[st.category].append({
            "scale_type": st,
            "enabled_roots": dict(enabled_map.get(st.pk, {})),
        })

    active_roots = [(i, ROOTS[i]) for i in sorted(roots_with_enabled)]

    return render(request, "scales/settings.html", {
        "catalog_by_category": by_category,
        "roots": ROOTS,
        "active_roots": active_roots,
        "active_scales": active_scales,
        "scale_weights": scale_weights,
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

    enabled_count = ScalePractice.objects.filter(
        profile=profile, scale_type=scale_type, enabled=True
    ).count()

    return render(request, "scales/partials/_toggle_cell.html", {
        "scale_type": scale_type,
        "root_index": root,
        "root_name": ROOTS[root],
        "sp": sp if sp.enabled else None,
        "enabled_count": enabled_count,
    })


@login_required
def toggle_all_roots(request, scale_type_id, action):
    """HTMX: enable or disable all 12 roots for a scale type at once."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    if action not in ("enable", "disable"):
        return JsonResponse({"error": "Invalid action"}, status=400)

    profile = get_active_profile(request)
    if not profile:
        return JsonResponse({"error": "No active profile"}, status=400)

    scale_type = get_object_or_404(ScaleType, pk=scale_type_id)
    enabled = action == "enable"

    for root in range(12):
        sp, _ = ScalePractice.objects.get_or_create(
            profile=profile, scale_type=scale_type, root=root
        )
        if sp.enabled != enabled:
            sp.enabled = enabled
            sp.save(update_fields=["enabled"])

    enabled_map = {}
    if enabled:
        for sp in ScalePractice.objects.filter(profile=profile, scale_type=scale_type, enabled=True):
            enabled_map[sp.root] = {
                "pk": sp.pk,
                "current_tempo": sp.current_tempo,
                "desired_tempo": sp.desired_tempo,
            }

    roots_data = [
        {
            "root_idx": i,
            "root_name": ROOTS[i],
            "enabled": i in enabled_map,
            "current_tempo": enabled_map.get(i, {}).get("current_tempo"),
            "desired_tempo": enabled_map.get(i, {}).get("desired_tempo"),
        }
        for i in range(12)
    ]

    enabled_count = ScalePractice.objects.filter(
        profile=profile, scale_type=scale_type, enabled=True
    ).count()

    return render(request, "scales/partials/_roots_row.html", {
        "scale_type": scale_type,
        "roots_data": roots_data,
        "enabled_count": enabled_count,
    })


# ── Rotation practice ────────────────────────────────────────────────────────

@login_required
def rotation_session(request):
    profile = get_active_profile(request)
    enabled_practices = list(
        ScalePractice.objects.filter(profile=profile, enabled=True).select_related("scale_type")
    )
    if not enabled_practices:
        first_use = (
            not ScalePractice.objects.filter(profile=profile).exists()
            if profile else False
        )
        return render(request, "scales/rotation_empty.html", {"first_use": first_use})

    order = _get_rotation_order(request, enabled_practices)
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

    next_scales = [sp_map[pk] for pk in order[1:3] if pk in sp_map]

    technique_index = request.session.get("scales_technique_index", 0)
    if sp.repetitions < 2:
        technique_index = 0

    # Counts are by distinct scale, not weighted queue length: a scale "remains"
    # until all of its reps for this lap are done. total = scales in the rotation.
    total = len(enabled_practices)
    remaining = len(set(order))
    progress_pct = round((total - remaining) / total * 100) if total else 0

    return render(request, "scales/rotation_session.html", {
        "sp": sp,
        "roots": ROOTS,
        "remaining": remaining,
        "total": total,
        "progress_pct": progress_pct,
        "ladder_json": json.dumps(ladder),
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if sp.current_tempo and t > sp.current_tempo),
            None,
        ),
        "next_scales": next_scales,
        "technique_index": technique_index,
    })


@login_required
def rotation_log(request):
    """Record a practice result and advance the queue."""
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

    update_fields = ["repetitions"]
    if achieved_tempo:
        if sp.fastest_tempo is None or achieved_tempo > sp.fastest_tempo:
            sp.fastest_tempo = achieved_tempo
            update_fields.append("fastest_tempo")
        sp.current_tempo = achieved_tempo
        update_fields.append("current_tempo")
    sp.repetitions += 1
    sp.save(update_fields=update_fields)

    rating_raw = request.POST.get("rating", "").strip()
    rating = None
    if rating_raw:
        try:
            r = int(rating_raw)
            if r in (1, 2, 3, 4):
                rating = r
        except ValueError:
            pass

    ScaleLog.objects.create(scale_practice=sp, achieved_tempo=achieved_tempo, rating=rating)

    request.session["scales_technique_index"] = request.session.get("scales_technique_index", 0) + 1

    order = list(request.session.get("scales_rotation_order", []))
    if sp_id in order:
        order.remove(sp_id)
    request.session["scales_rotation_order"] = order

    if not order:
        return redirect("scales:rotation_complete")
    return redirect("scales:rotation_session")


@login_required
def rotation_reshuffle(request):
    """Clear rotation order so a fresh weighted lap is built on next visit."""
    if request.method == "POST":
        request.session.pop("scales_rotation_order", None)
    return redirect("scales:rotation_session")


@login_required
def rotation_skip(request):
    """Skip the current scale — move it to the end of the queue without logging."""
    if request.method != "POST":
        return redirect("scales:rotation_session")
    try:
        sp_id = int(request.POST["sp_id"])
    except (KeyError, ValueError):
        return redirect("scales:rotation_session")

    order = list(request.session.get("scales_rotation_order", []))
    if sp_id in order:
        order.remove(sp_id)
        order.append(sp_id)
    request.session["scales_rotation_order"] = order
    return redirect("scales:rotation_session")


@login_required
def rotation_complete(request):
    request.session.pop("scales_rotation_order", None)
    if request.session.get("planner_state"):
        return redirect("planner:section_done")
    profile = get_active_profile(request)
    enabled_count = ScalePractice.objects.filter(profile=profile, enabled=True).count() if profile else 0

    from datetime import datetime, timedelta, timezone
    session_start = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    recent_logs = (
        ScaleLog.objects
        .filter(scale_practice__profile=profile, reviewed_at__gte=session_start)
        .select_related("scale_practice")
        if profile else []
    )
    scales_played = len({log.scale_practice_id for log in recent_logs})
    tempos = [log.achieved_tempo for log in recent_logs if log.achieved_tempo]
    new_bests = sum(
        1 for log in recent_logs
        if log.achieved_tempo and log.scale_practice.fastest_tempo == log.achieved_tempo
    )

    return render(request, "scales/rotation_complete.html", {
        "enabled_count": enabled_count,
        "scales_played": scales_played,
        "new_bests": new_bests,
        "top_tempo": max(tempos) if tempos else None,
    })


# ── Detail view ──────────────────────────────────────────────────────────────

@login_required
def detail(request, pk):
    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=pk, profile=profile)
    logs = sp.logs.order_by("-reviewed_at")[:50]

    intervals_json = json.dumps(sp.scale_type.intervals)
    ladder = calculate_tempo_ladder(sp.current_tempo, sp.desired_tempo)
    return render(request, "scales/detail.html", {
        "sp": sp,
        "roots": ROOTS,
        "logs": logs,
        "intervals_json": intervals_json,
        "root_index": sp.root,
        "ladder_json": json.dumps(ladder),
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if sp.current_tempo and t > sp.current_tempo),
            None,
        ),
    })


@login_required
def log_from_detail(request, pk):
    if request.method != "POST":
        return redirect("scales:detail", pk=pk)
    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=pk, profile=profile)

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
    return redirect("scales:detail", pk=pk)


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


@login_required
def save_notes(request, pk):
    """Save freetext notes for a ScalePractice."""
    if request.method != "POST":
        return redirect("scales:detail", pk=pk)
    profile = get_active_profile(request)
    sp = get_object_or_404(ScalePractice, pk=pk, profile=profile)
    sp.notes = request.POST.get("notes", "").strip()
    sp.save(update_fields=["notes"])
    return redirect("scales:detail", pk=pk)


# ── Rotation by key ──────────────────────────────────────────────────────────

@login_required
def rotation_by_key(request, root):
    """Rotation filtered to a single root note — 'all C scales', etc."""
    if not (0 <= root <= 11):
        return redirect("scales:rotation_session")

    profile = get_active_profile(request)
    enabled_practices = list(
        ScalePractice.objects.filter(profile=profile, enabled=True, root=root)
        .select_related("scale_type")
    )
    if not enabled_practices:
        return render(request, "scales/rotation_empty.html", {})

    weights = _compute_rotation_weights(enabled_practices, get_scale_weights(profile))
    weighted = _build_weighted_order(enabled_practices, weights)
    request.session["scales_rotation_order"] = weighted

    sp_map = {sp.pk: sp for sp in enabled_practices}
    sp = sp_map[weighted[0]]

    ladder = calculate_tempo_ladder(sp.current_tempo, sp.desired_tempo)
    next_scales = [sp_map[pk] for pk in weighted[1:3] if pk in sp_map]
    technique_index = request.session.get("scales_technique_index", 0)
    if sp.repetitions < 2:
        technique_index = 0

    return render(request, "scales/rotation_session.html", {
        "sp": sp,
        "roots": ROOTS,
        "remaining": len(weighted),
        "total": len(enabled_practices),
        "ladder_json": json.dumps(ladder),
        "push_step_index": next(
            (i for i, t in enumerate(ladder) if sp.current_tempo and t > sp.current_tempo),
            None,
        ),
        "by_key_root": root,
        "by_key_root_name": ROOTS[root],
        "next_scales": next_scales,
        "technique_index": technique_index,
    })


# ── Unified entry point + bulk tempo ─────────────────────────────────────────

@login_required
def practice_redirect(request):
    return redirect("scales:rotation_session")


@login_required
def bulk_set_tempo(request):
    """Set desired_tempo on all enabled ScalePractices for this profile."""
    if request.method != "POST":
        return redirect("scales:settings")
    profile = get_active_profile(request)
    if not profile:
        return redirect("scales:settings")
    val = request.POST.get("desired_tempo", "").strip()
    try:
        t = int(val)
        if 20 <= t <= 400:
            ScalePractice.objects.filter(profile=profile, enabled=True).update(desired_tempo=t)
    except ValueError:
        pass
    return redirect("scales:settings")


@login_required
def save_scale_weights(request):
    """Persist the per-profile priority weights for the rotation queue.

    tempo + peer form a budget; smoothness is derived as the remainder so the
    three always sum to 10. new_boost is an independent additive slider.
    """
    if request.method != "POST":
        return redirect("scales:settings")
    profile = get_active_profile(request)
    if profile:
        def clamp(key):
            try:
                return max(0, min(10, int(request.POST.get(key, ""))))
            except (ValueError, TypeError):
                return DEFAULT_SCALE_WEIGHTS[key]
        tempo = clamp("tempo")
        peer = min(clamp("peer"), 10 - tempo)        # tempo + peer ≤ 10
        smoothness = 10 - tempo - peer               # remainder → always sums to 10
        profile.scale_weights = {
            "tempo": tempo,
            "peer": peer,
            "smoothness": smoothness,
            "new_boost": clamp("new_boost"),
        }
        profile.save(update_fields=["scale_weights"])
        request.session.pop("scales_rotation_order", None)  # rebuild next lap
    return redirect("scales:settings")
