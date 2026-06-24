import base64
from datetime import date

from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PieceForm, TrickyBitForm
from .models import Piece, PracticeLog, TrickyBit


def _apply_pasted_image(bit, post_data):
    """Save a base64 pasted image onto bit.image when no file was uploaded.

    Called after form.save(commit=False) so bit.image is still empty.
    """
    image_data = post_data.get("image_data", "")
    if not image_data.startswith("data:image/"):
        return
    try:
        header, b64 = image_data.split(";base64,", 1)
        ext = header.split("/")[-1]
        bit.image.save(
            f"paste.{ext}",
            ContentFile(base64.b64decode(b64)),
            save=False,
        )
    except Exception:
        pass  # silently ignore malformed base64; image stays empty


def dashboard(request):
    today = date.today()
    due_count = TrickyBit.objects.filter(
        piece__is_active=True
    ).filter(
        Q(next_review_at__lte=today) | Q(next_review_at__isnull=True)
    ).count()

    recent_logs = PracticeLog.objects.select_related("tricky_bit__piece").order_by(
        "-reviewed_at"
    )[:10]

    active_pieces = Piece.objects.filter(is_active=True).count()

    return render(request, "dashboard.html", {
        "due_count": due_count,
        "recent_logs": recent_logs,
        "active_pieces": active_pieces,
    })


def piece_list(request):
    pieces = Piece.objects.annotate(bit_count=Count("tricky_bits")).order_by("name")
    return render(request, "pieces/piece_list.html", {"pieces": pieces})


def piece_add(request):
    form = PieceForm(request.POST or None)
    if form.is_valid():
        piece = form.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/piece_form.html", {"form": form, "action": "Add Piece"})


def piece_edit(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    form = PieceForm(request.POST or None, instance=piece)
    if form.is_valid():
        form.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/piece_form.html", {
        "form": form,
        "piece": piece,
        "action": "Edit Piece",
    })


def piece_detail(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    tricky_bits = piece.tricky_bits.order_by("-difficulty", "label")
    return render(request, "pieces/piece_detail.html", {
        "piece": piece,
        "tricky_bits": tricky_bits,
    })


def piece_toggle_active(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    if request.method == "POST":
        piece.is_active = not piece.is_active
        piece.save(update_fields=["is_active"])
    return render(request, "partials/_active_toggle.html", {"piece": piece})


def trickybit_detail(request, pk, bit_pk):
    piece = get_object_or_404(Piece, pk=pk)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    logs = bit.practice_logs.order_by("-reviewed_at")[:50]

    # Pull in OMR analysis if it exists
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


def trickybit_add(request, pk):
    piece = get_object_or_404(Piece, pk=pk)
    form = TrickyBitForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        bit = form.save(commit=False)
        bit.piece = piece
        if not bit.image:
            _apply_pasted_image(bit, request.POST)
        bit.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/trickybit_form.html", {
        "form": form,
        "piece": piece,
        "action": "Add Passage",
    })


def trickybit_edit(request, pk, bit_pk):
    piece = get_object_or_404(Piece, pk=pk)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    form = TrickyBitForm(request.POST or None, request.FILES or None, instance=bit)
    if form.is_valid():
        bit = form.save(commit=False)
        if not bit.image:
            _apply_pasted_image(bit, request.POST)
        bit.save()
        return redirect("pieces:piece_detail", pk=piece.pk)
    return render(request, "pieces/trickybit_form.html", {
        "form": form,
        "piece": piece,
        "bit": bit,
        "action": "Edit Passage",
    })


def trickybit_reset(request, pk, bit_pk):
    """Reset SM-2 state for a passage back to defaults."""
    piece = get_object_or_404(Piece, pk=pk)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    if request.method == "POST":
        bit.ease_factor = 2.5
        bit.interval_days = 0
        bit.repetitions = 0
        bit.next_review_at = None
        bit.save(update_fields=["ease_factor", "interval_days", "repetitions", "next_review_at"])
    return redirect("pieces:trickybit_detail", pk=piece.pk, bit_pk=bit_pk)


def trickybit_delete(request, pk, bit_pk):
    piece = get_object_or_404(Piece, pk=pk)
    bit = get_object_or_404(TrickyBit, pk=bit_pk, piece=piece)
    if request.method == "POST":
        bit.delete()
    return redirect("pieces:piece_detail", pk=piece.pk)
