from .base import AnalysisProvider


class ManualProvider(AnalysisProvider):
    """Saves features that the user selected by hand — no AI involved."""

    def analyze(self, tricky_bit, features=None, notes="", **kwargs):
        return {
            "features": [
                {"type": f, "confidence": 1.0} for f in (features or [])
            ],
            "raw_response": "",
            "notes": notes,
        }
