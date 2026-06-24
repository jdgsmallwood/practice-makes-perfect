"""Unit tests for OMR service, providers, and models."""
from unittest.mock import MagicMock, patch

import pytest

from omr.models import FEATURE_LABELS, DetectedFeature, Exercise, PassageAnalysis
from omr.providers.manual import ManualProvider
from omr.service import recommend_exercises, run_analysis
from tests.factories import PieceFactory, TrickyBitFactory


class TestManualProvider:
    def test_returns_features_with_full_confidence(self):
        result = ManualProvider().analyze(None, features=["register_high", "technique_trill"])
        assert result["features"] == [
            {"type": "register_high", "confidence": 1.0},
            {"type": "technique_trill", "confidence": 1.0},
        ]

    def test_empty_features_list(self):
        result = ManualProvider().analyze(None, features=[])
        assert result["features"] == []

    def test_passes_notes_through(self):
        result = ManualProvider().analyze(None, features=[], notes="High passage")
        assert result["notes"] == "High passage"

    def test_raw_response_is_empty_string(self):
        result = ManualProvider().analyze(None, features=["register_high"])
        assert result["raw_response"] == ""


@pytest.mark.django_db
class TestRunAnalysisManual:
    def test_creates_passage_analysis(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=["register_high"])
        assert PassageAnalysis.objects.filter(tricky_bit=bit).exists()

    def test_sets_status_complete(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        analysis = run_analysis(bit, provider_name="manual", features=["register_high"])
        assert analysis.status == "complete"

    def test_saves_detected_features(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=["register_high", "technique_trill"])
        analysis = PassageAnalysis.objects.get(tricky_bit=bit)
        detected = {f.feature_type for f in analysis.detected_features.all()}
        assert detected == {"register_high", "technique_trill"}

    def test_rerunning_replaces_features(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=["register_high"])
        run_analysis(bit, provider_name="manual", features=["rhythm_triplets"])
        analysis = PassageAnalysis.objects.get(tricky_bit=bit)
        detected = {f.feature_type for f in analysis.detected_features.all()}
        assert detected == {"rhythm_triplets"}
        assert "register_high" not in detected

    def test_saves_notes(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=[], notes="Very hard passage")
        analysis = PassageAnalysis.objects.get(tricky_bit=bit)
        assert analysis.notes == "Very hard passage"

    def test_unknown_provider_marks_failed(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        with pytest.raises(ValueError):
            run_analysis(bit, provider_name="nonexistent")
        analysis = PassageAnalysis.objects.get(tricky_bit=bit)
        assert analysis.status == "failed"
        assert "nonexistent" in analysis.error_message

    def test_one_to_one_per_tricky_bit(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=["register_high"])
        run_analysis(bit, provider_name="manual", features=["rhythm_triplets"])
        # Should still be only one PassageAnalysis per bit
        assert PassageAnalysis.objects.filter(tricky_bit=bit).count() == 1


@pytest.mark.django_db
class TestClaudeVisionProvider:
    """Tests for the Claude Vision provider use a mock to avoid real API calls."""

    def _make_mock_response(self, features, notes="test passage"):
        import json
        payload = {"features": features, "notes": notes}
        msg = MagicMock()
        msg.content = [MagicMock(text=json.dumps(payload))]
        return msg

    @patch("anthropic.Anthropic")
    def test_calls_api_and_returns_features(self, mock_anthropic_class, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)

        # Write a minimal PNG so image.open() works
        import base64
        from django.core.files.base import ContentFile
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
            "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
        )
        bit.image.save("test.png", ContentFile(png_bytes), save=True)

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_response(
            [{"type": "register_high", "confidence": 0.9}],
            notes="High register passage",
        )

        analysis = run_analysis(bit, provider_name="claude_vision")
        assert analysis.status == "complete"
        assert mock_client.messages.create.called

        detected = {f.feature_type for f in analysis.detected_features.all()}
        assert "register_high" in detected

    def test_no_image_raises(self):
        # ValueError is raised before the API call, so no mock needed
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)  # no image
        with pytest.raises(ValueError, match="no image"):
            run_analysis(bit, provider_name="claude_vision")


@pytest.mark.django_db
class TestRecommendExercises:
    def test_no_analysis_returns_empty(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        assert list(recommend_exercises(bit)) == []

    def test_matching_exercise_returned(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=["register_high"])

        ex = Exercise.objects.create(
            title="High register exercises",
            description="Practice overtones",
            target_features=["register_high", "register_altissimo"],
            difficulty=4,
        )
        result = list(recommend_exercises(bit))
        assert ex in result

    def test_non_matching_exercise_excluded(self):
        piece = PieceFactory()
        bit = TrickyBitFactory(piece=piece)
        run_analysis(bit, provider_name="manual", features=["technique_staccato"])

        Exercise.objects.create(
            title="Octave leaps",
            description="Practice octave leaps",
            target_features=["interval_octaves"],
            difficulty=3,
        )
        result = list(recommend_exercises(bit))
        assert result == []


class TestFeatureModel:
    def test_feature_labels_dict_covers_all_choices(self):
        from omr.models import FEATURE_CHOICES
        keys = {code for code, _ in FEATURE_CHOICES}
        assert set(FEATURE_LABELS.keys()) == keys

    def test_feature_groups_reference_valid_codes(self):
        from omr.models import FEATURE_CHOICES, FEATURE_GROUPS
        valid_codes = {code for code, _ in FEATURE_CHOICES}
        for group_name, codes in FEATURE_GROUPS:
            for code in codes:
                assert code in valid_codes, f"{code!r} in group {group_name!r} is not a valid feature code"
