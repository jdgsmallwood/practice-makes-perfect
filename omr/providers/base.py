from abc import ABC, abstractmethod
from typing import Any


class AnalysisProvider(ABC):
    """Interface for all passage analysis backends."""

    @abstractmethod
    def analyze(self, tricky_bit, **kwargs) -> dict[str, Any]:
        """
        Analyse a TrickyBit and return detected features.

        Returns:
            dict with:
            - features: list of {"type": str, "confidence": float}
            - raw_response: str  (AI response text or "" for manual)
            - notes: str         (human-readable summary)
        """
        raise NotImplementedError
