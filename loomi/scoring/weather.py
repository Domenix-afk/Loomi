"""Wetter: Passt Wärmegrad und Ausstattung des Outfits zum Wetter?"""

from __future__ import annotations

from ..models import Category, ComponentScore, Outfit, OutfitContext, WeatherCondition
from .base import ScoreComponent


class WeatherFit(ScoreComponent):
    """Bewertet Wärme-Level und wettergerechte Ausstattung (z. B. Jacke)."""

    name = "weather"

    # Beitrag einer Kategorie zum Wärmegrad des Outfits.
    _WEIGHTS: dict[Category, float] = {
        Category.TOP: 1.0,
        Category.BOTTOM: 1.0,
        Category.OUTERWEAR: 1.6,
        Category.SHOES: 0.5,
        Category.ACCESSORY: 0.4,
    }

    # (Bonus mit Jacke, Abzug ohne Jacke) je Wetterlage.
    _CONDITION_MODIFIERS: dict[WeatherCondition, tuple[float, float]] = {
        WeatherCondition.RAIN: (0.20, -0.40),
        WeatherCondition.SNOW: (0.10, -0.20),
        WeatherCondition.WINDY: (0.05, -0.10),
        WeatherCondition.CLOUDY: (0.0, 0.0),
        WeatherCondition.SUNNY: (-0.05, 0.05),
    }

    def _target_warmth(self, temperature: float) -> int:
        raw = (20 - temperature) / 5 + 2
        return min(5, max(1, round(raw)))

    def _outfit_warmth(self, outfit: Outfit) -> float:
        numerator = sum(
            item.warmth * self._WEIGHTS[item.category]
            for item in outfit.items.values()
        )
        denominator = sum(self._WEIGHTS[c] for c in outfit.items)
        return numerator / denominator if denominator else 0.0

    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        target = self._target_warmth(context.temperature)
        warmth = self._outfit_warmth(outfit)
        base = max(0.0, 1.0 - abs(warmth - target) * 0.35)

        has_outer = Category.OUTERWEAR in outfit.items
        bonus, penalty = self._CONDITION_MODIFIERS[context.condition]
        factor = 1.0 + (bonus if has_outer else penalty)

        final = min(1.0, max(0.0, base * factor))
        outer = "mit Jacke" if has_outer else "ohne Jacke"
        details = f"Wärme {warmth:.1f} (Ziel {target}), {context.condition.value}, {outer}"
        return ComponentScore(self.name, round(final, 4), 1.0, details)
