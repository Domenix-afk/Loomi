"""Anlass: Passt der Formalismus-Grad des Outfits zum Anlass?"""

from __future__ import annotations

from ..models import ComponentScore, Occasion, Outfit, OutfitContext
from .base import ScoreComponent


class OccasionFit(ScoreComponent):
    """Bewertet Formalität (1 = leger, 5 = formell) gegen den Anlass."""

    name = "occasion"

    # Zielbereich der durchschnittlichen Formalität je Anlass.
    _TARGET_RANGES: dict[Occasion, tuple[float, float]] = {
        Occasion.CASUAL: (1.0, 2.5),
        Occasion.WORK: (3.0, 4.0),
        Occasion.DATE: (2.5, 4.0),
        Occasion.PARTY: (2.0, 4.0),
        Occasion.SPORT: (1.0, 2.0),
        Occasion.FORMAL: (4.5, 5.0),
        Occasion.TRAVEL: (1.0, 2.5),
    }

    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        formality = [item.formality for item in outfit.items.values()]
        mean = sum(formality) / len(formality)
        low, high = self._TARGET_RANGES[context.occasion]

        if low <= mean <= high:
            fit = 1.0
        elif mean < low:
            fit = max(0.0, 1.0 - (low - mean) * 0.5)
        else:
            fit = max(0.0, 1.0 - (mean - high) * 0.5)

        # Konsistenz: stark gemischte Formalitätsgrade (z. B. Anzug +
        # Sneaker) wirken zusammengewürfelt.
        if len(formality) > 1:
            variance = sum((f - mean) ** 2 for f in formality) / len(formality)
            spread = variance**0.5
            spread_penalty = min(0.3, max(0.0, (spread - 0.8)) * 0.35)
        else:
            spread_penalty = 0.0

        final = max(0.0, fit * (1.0 - spread_penalty))
        details = f"Formalität {mean:.1f} (Ziel {low:.1f}–{high:.1f})"
        if spread_penalty:
            details += f", Streuung {spread:.1f} -> Abzug"
        return ComponentScore(self.name, round(final, 4), 1.0, details)
