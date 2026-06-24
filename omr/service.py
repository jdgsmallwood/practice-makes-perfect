from django.utils import timezone

from pieces.models import TrickyBit
from .models import DetectedFeature, PassageAnalysis
from .providers.claude_vision import ClaudeVisionProvider
from .providers.manual import ManualProvider

_PROVIDERS = {
    "manual": ManualProvider,
    "claude_vision": ClaudeVisionProvider,
}


def run_analysis(tricky_bit: TrickyBit, provider_name: str = "manual", **kwargs) -> PassageAnalysis:
    """Run (or re-run) an analysis on a TrickyBit and persist the results.

    Existing DetectedFeature rows are replaced on each run so results stay fresh.
    Raises on provider error after marking analysis as 'failed'.
    """
    analysis, _ = PassageAnalysis.objects.get_or_create(tricky_bit=tricky_bit)
    analysis.status = "processing"
    analysis.provider = provider_name
    analysis.error_message = ""
    analysis.save(update_fields=["status", "provider", "error_message"])

    try:
        provider_class = _PROVIDERS.get(provider_name)
        if provider_class is None:
            raise ValueError(f"Unknown analysis provider: {provider_name!r}")

        result = provider_class().analyze(tricky_bit, **kwargs)

        analysis.detected_features.all().delete()
        for item in result.get("features", []):
            feat_type = item.get("type", "") if isinstance(item, dict) else str(item)
            confidence = float(item.get("confidence", 1.0)) if isinstance(item, dict) else 1.0
            if feat_type:
                DetectedFeature.objects.get_or_create(
                    analysis=analysis,
                    feature_type=feat_type,
                    defaults={"confidence": confidence},
                )

        analysis.raw_response = result.get("raw_response", "")
        analysis.notes = result.get("notes", "")
        analysis.status = "complete"
        analysis.completed_at = timezone.now()
        analysis.save()

    except Exception as exc:
        analysis.status = "failed"
        analysis.error_message = str(exc)
        analysis.save(update_fields=["status", "error_message"])
        raise

    return analysis


def recommend_exercises(tricky_bit: TrickyBit):
    """Return exercises whose target_features overlap the passage's detected features.

    Returns an empty queryset until the Exercise library is populated.
    """
    from .models import Exercise

    try:
        detected = tricky_bit.analysis.detected_feature_types
    except PassageAnalysis.DoesNotExist:
        return Exercise.objects.none()

    if not detected:
        return Exercise.objects.none()

    # Filter exercises that target at least one detected feature.
    # JSONField containment queries vary by backend; we use Python-level filtering
    # because SQLite doesn't support JSON containment natively in Django < 4.2.
    matching_ids = [
        ex.pk
        for ex in Exercise.objects.all()
        if set(ex.target_features) & detected
    ]
    return Exercise.objects.filter(pk__in=matching_ids).order_by("difficulty")
