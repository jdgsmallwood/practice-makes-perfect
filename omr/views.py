from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from pieces.models import TrickyBit


@login_required
def save_manual_features(request, bit_pk):
    """Save manually selected features for a passage (replaces existing)."""
    bit = get_object_or_404(TrickyBit, pk=bit_pk)
    if request.method == "POST":
        from .service import run_analysis
        features = request.POST.getlist("features")
        notes = request.POST.get("notes", "")
        run_analysis(bit, provider_name="manual", features=features, notes=notes)
        messages.success(request, "Features saved.")
    return redirect("pieces:trickybit_detail", pk=bit.piece_id, bit_pk=bit_pk)


@login_required
def analyze_with_ai(request, bit_pk):
    """Trigger Claude Vision analysis on the passage image."""
    bit = get_object_or_404(TrickyBit, pk=bit_pk)
    if request.method == "POST":
        if not bit.image:
            messages.error(request, "Add a screenshot before running AI analysis.")
        else:
            try:
                from .service import run_analysis
                run_analysis(bit, provider_name="claude_vision")
                messages.success(request, "AI analysis complete.")
            except ImportError:
                messages.error(
                    request,
                    "anthropic package not installed. "
                    "Run: hatch run pip install anthropic",
                )
            except Exception as exc:
                messages.error(request, f"Analysis failed: {exc}")
    return redirect("pieces:trickybit_detail", pk=bit.piece_id, bit_pk=bit_pk)
