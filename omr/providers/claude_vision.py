import base64
import json
import re

from .base import AnalysisProvider

# Prompt instructs Claude to return only JSON — no markdown fences, no prose.
_PROMPT = """\
Analyze this sheet music excerpt written for flute and identify which musical \
features are present. Return ONLY a valid JSON object with this exact structure \
(no markdown, no explanation outside the JSON):

{
  "features": [
    {"type": "<feature_code>", "confidence": <0.0-1.0>}
  ],
  "notes": "<one sentence describing the passage's main challenge>"
}

Only include feature codes that are clearly present. Available codes:
Register:    register_low, register_middle, register_high, register_altissimo
Intervals:   interval_stepwise, interval_thirds, interval_fourths_fifths,
             interval_sixths, interval_octaves, interval_wide_leaps
Techniques:  technique_slur, technique_staccato, technique_trill,
             technique_flutter, technique_harmonic, technique_multiphonic,
             technique_vibrato
Rhythm:      rhythm_fast_runs, rhythm_triplets, rhythm_dotted,
             rhythm_syncopation, rhythm_cross_rhythm
Articulation: mark_accent, mark_tenuto, mark_marcato
Dynamics:    dynamic_soft, dynamic_loud, dynamic_sudden_change
Key & Time:  key_many_sharps, key_many_flats, time_compound,
             time_irregular, time_changing\
"""

_MEDIA_TYPE_MAP = {
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class ClaudeVisionProvider(AnalysisProvider):
    """Sends the passage image to Claude claude-sonnet-4-6 and parses the feature JSON."""

    MODEL = "claude-sonnet-4-6"

    def analyze(self, tricky_bit, **kwargs):
        if not tricky_bit.image:
            raise ValueError("TrickyBit has no image to analyze.")

        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required for AI analysis. "
                "Add 'anthropic' to your dependencies and reinstall."
            ) from exc

        # Determine media type from filename extension
        name = tricky_bit.image.name.lower()
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        media_type = _MEDIA_TYPE_MAP.get(ext, "image/jpeg")

        with tricky_bit.image.open("rb") as fh:
            image_b64 = base64.standard_b64encode(fh.read()).decode("utf-8")

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

        response = client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
        )

        raw_text = response.content[0].text

        # Extract JSON — model may still wrap in ```json fences despite instruction
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_match:
            raise ValueError(
                f"No JSON found in model response. First 300 chars: {raw_text[:300]}"
            )

        parsed = json.loads(json_match.group())
        return {
            "features": parsed.get("features", []),
            "raw_response": raw_text,
            "notes": parsed.get("notes", ""),
        }
