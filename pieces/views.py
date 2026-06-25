import io
import logging
import uuid
from datetime import datetime
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_active_profile
from .forms import PieceForm, TrickyBitForm
from .models import Piece, PracticeLog, TrickyBit

logger = logging.getLogger(__name__)


@login_required
def upload_image_ajax(request):
    """Accept a pasted image file, normalise it to PNG, persist it immediately."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    image_file = request.FILES.get("image")
    if not image_file:
        return JsonResponse({"error": "No image file"}, status=400)

    try:
        from PIL import Image as PilImage
        img = PilImage.open(image_file)
        img = img.convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        content = ContentFile(buf.read())
    except Exception:
        logger.exception("Pillow could not read pasted image; saving raw bytes")
        image_file.seek(0)
        content = ContentFile(image_file.read())

    filename = f"tricky_bits/{datetime.now().strftime('%Y/%m')}/paste_{uuid.uuid4().hex[:10]}.png"
    path = default_storage.save(filename, content)

    return JsonResponse({"path": path})


@login_required
def dashboard(request):
    profile = get_active_profile(request)
    today = date.today()

    due_qs = TrickyBit.objects.filter(piece__is_active=True)
    pieces_qs = Piece.objects.filter(is_active=True)
    logs_qs = PracticeLog.objects.select_related("tricky_bit__piece")
    due_qs = due_qs.filter(piece__profile=profile)
    pieces_qs = pieces_qs.filter(profile=profile)
    logs_qs = logs_qs.filter(tricky_bit__piece__profile=profile)

    due_count = due_qs.filter(
        Q(next_review_at__lte=today) | Q(next_review_at__isnull=True)
    ).count()
    recent_logs = logs_qs.order_by("-reviewed_at")[:10]
    active_pieces = pieces_qs.count()

    from practice.views import _get_practice_dates, calculate_streaks
    practice_dates = _get_practice_dates(profile)
    current_streak = calculate_streaks(practice_dates)["current"]

    return render(request, "dashboard.html", {
        "due_count": due_count,
        "recent_logs": recent_logs,
        "active_pieces": active_pieces,
        "current_streak": current_streak,
    })


@login_required
def piece_list(request):
    profile = get_active_profile(request)
    pieces = Piece.objects.filter(profile=profile).annotate(
        bit_count=Count("tricky_bits")
    ).order_by("name")
    return render(request, "pieces/piece_list.html", {"pieces": pieces})


@login_required
def piece_add(request):
    profile = get_active_profile(request)
    form = PieceForm(request.POST or None)
    if form.is_valid():
        piece = form.save(commit=False)
        piece.profile = profile
        piece.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/piece_form.html", {"form": form, "action": "Add Piece"})


@login_required
def piece_edit(request, pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    form = PieceForm(request.POST or None, instance=piece)
    if form.is_valid():
        form.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/piece_form.html", {
        "form": form,
        "piece": piece,
        "action": "Edit Piece",
    })


@login_required
def piece_detail(request, pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    tricky_bits = piece.tricky_bits.order_by("-difficulty", "label")
    return render(request, "pieces/piece_detail.html", {
        "piece": piece,
        "tricky_bits": tricky_bits,
    })


@login_required
def piece_toggle_active(request, pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    if request.method == "POST":
        piece.is_active = not piece.is_active
        piece.save(update_fields=["is_active"])
    return render(request, "partials/_active_toggle.html", {"piece": piece})


@login_required
def trickybit_detail(request, pk, bit_pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    logs = bit.practice_logs.order_by("-reviewed_at")[:50]

    try:
        from omr.models import FEATURE_GROUPS, FEATURE_LABELS, PassageAnalysis
        analysis = PassageAnalysis.objects.prefetch_related("detected_features").filter(
            tricky_bit=bit
        ).first()
        detected_types = set(analysis.detected_feature_types) if analysis else set()
    except Exception:
        analysis = None
        detected_types = set()
        FEATURE_GROUPS = []
        FEATURE_LABELS = {}

    return render(request, "pieces/trickybit_detail.html", {
        "piece": piece,
        "bit": bit,
        "logs": logs,
        "analysis": analysis,
        "detected_types": detected_types,
        "feature_groups": FEATURE_GROUPS,
        "feature_labels": FEATURE_LABELS,
    })


def _attach_uploaded_image(bit, post_data):
    """If the paste handler pre-uploaded an image, point bit.image at it."""
    path = post_data.get("uploaded_image_path", "").strip()
    if path and default_storage.exists(path):
        bit.image = path
    elif path:
        logger.warning("uploaded_image_path %r does not exist in storage", path)


@login_required
def trickybit_add(request, pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    form = TrickyBitForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        bit = form.save(commit=False)
        bit.piece = piece
        if request.POST.get("uploaded_image_path", "").strip():
            _attach_uploaded_image(bit, request.POST)
        bit.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/trickybit_form.html", {
        "form": form,
        "piece": piece,
        "action": "Add Passage",
    })


@login_required
def trickybit_edit(request, pk, bit_pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    form = TrickyBitForm(request.POST or None, request.FILES or None, instance=bit)
    if form.is_valid():
        bit = form.save(commit=False)
        if request.POST.get("uploaded_image_path", "").strip():
            _attach_uploaded_image(bit, request.POST)
        bit.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/trickybit_form.html", {
        "form": form,
        "piece": piece,
        "bit": bit,
        "action": "Edit Passage",
    })


@login_required
def trickybit_reset(request, pk, bit_pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    if request.method == "POST":
        bit.ease_factor = 2.5
        bit.interval_days = 0
        bit.repetitions = 0
        bit.next_review_at = None
        bit.save(update_fields=["ease_factor", "interval_days", "repetitions", "next_review_at"])
    return redirect("pieces:trickybit_detail", pk=piece.pk, bit_pk=bit_pk)


@login_required
def trickybit_delete(request, pk, bit_pk):
    profile = get_active_profile(request)
    piece = get_object_or_404(Piece, pk=pk, profile=profile)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    if request.method == "POST":
        bit.delete()
    return redirect("pieces:piece_detail", pk=piece.pk)
