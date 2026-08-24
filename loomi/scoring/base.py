"""Basis-Abstraktion für Scoring-Bausteine.

Jede Komponente berechnet einen Teil-Score in [0, 1] für ein Outfit und
liefert zusätzlich eine kurze, erklärbare Begründung. So lässt sich der
Gesamt-Score jederzeit transparent nachvollziehen und neue Logik
(z. B. ML-basiert) einfach als weitere Komponente ergänzen oder eine
bestehende ersetzen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ComponentScore, Outfit, OutfitContext


class ScoreComponent(ABC):
    """Ein einzelner, austauschbarer Bewertungsbaustein."""

    name: str = ""

    @abstractmethod
    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        """Bewertet ein Outfit und liefert Score plus Begründung."""
