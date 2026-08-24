"""Farbharmonie: Farbwheel-basierte Bewertung der Farbkombination."""

from __future__ import annotations

from ..models import ColorFamily, ComponentScore, Outfit, OutfitContext
from .base import ScoreComponent

# Farbton (0–360) je Farbfamilie; Neutral (schwarz/weiß/grau/beige)
# harmoniert mit allem und hat daher keinen Farbton.
_HUE: dict[ColorFamily, int] = {
    ColorFamily.RED: 0,
    ColorFamily.ORANGE: 30,
    ColorFamily.YELLOW: 60,
    ColorFamily.GREEN: 120,
    ColorFamily.BLUE: 240,
    ColorFamily.PURPLE: 270,
    ColorFamily.PINK: 330,
    ColorFamily.BROWN: 25,
}


class ColorHarmony(ScoreComponent):
    """Bewertet, wie gut die Farben eines Outfits zusammenpassen."""

    name = "color"

    def _pair_score(self, a: ColorFamily, b: ColorFamily) -> float:
        if a is ColorFamily.NEUTRAL and b is ColorFamily.NEUTRAL:
            return 1.0
        if a is ColorFamily.NEUTRAL or b is ColorFamily.NEUTRAL:
            return 0.9
        distance = abs(_HUE[a] - _HUE[b])
        distance = min(distance, 360 - distance)
        if distance <= 30:
            return 0.9  # gleiche/benachbarte Familie (monochrom/analog)
        if distance <= 45:
            return 0.85
        if 150 <= distance <= 210:
            return 0.75  # Komplementärfarben
        if distance >= 90:
            return 0.55
        return 0.4  # nah beieinander, aber disharmonisch

    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        colors = [item.color for item in outfit.items.values()]

        if len(colors) <= 1:
            base = 1.0
        else:
            pairs = [(a, b) for i, a in enumerate(colors) for b in colors[i + 1 :]]
            base = sum(self._pair_score(a, b) for a, b in pairs) / len(pairs)

        # Zu viele verschiedene bunte Farben wirken unruhig.
        distinct = len({c for c in colors if c is not ColorFamily.NEUTRAL})
        penalty = 0.0
        if distinct > 2:
            penalty = min(0.3, 0.15 * (distinct - 2))

        final = max(0.0, base - penalty)
        details = f"Farbharmonie {base:.2f}"
        if penalty:
            details += f", Abzug für {distinct} bunte Farben (-{penalty:.2f})"
        return ComponentScore(self.name, round(final, 4), 1.0, details)
