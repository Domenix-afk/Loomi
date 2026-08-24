"""Empfehlung: kombiniert Generator und Scoring zum transparenten Gesamt-Score."""

from __future__ import annotations

from .generator import OutfitGenerator
from .models import Outfit, OutfitContext, ScoredOutfit
from .scoring.base import ScoreComponent
from .scoring.color import ColorHarmony
from .scoring.occasion import OccasionFit
from .scoring.style import StyleMatch
from .scoring.variety import Variety
from .scoring.weather import WeatherFit
from .wardrobe import Wardrobe


class Recommender:
    """Empfiehlt die besten Outfits für einen gegebenen Kontext.

    Der Gesamt-Score ist die gewichtete Summe der Teil-Scores. Komponenten
    und Gewichte sind austauschbar – z. B. um später per User-Feedback
    oder ML gelernte Gewichte zu verwenden.
    """

    DEFAULT_COMPONENTS: tuple[type[ScoreComponent], ...] = (
        StyleMatch,
        ColorHarmony,
        OccasionFit,
        WeatherFit,
        Variety,
    )

    DEFAULT_WEIGHTS: dict[str, float] = {
        "style": 0.25,
        "color": 0.20,
        "occasion": 0.25,
        "weather": 0.20,
        "variety": 0.10,
    }

    def __init__(
        self,
        components: list[ScoreComponent] | None = None,
        weights: dict[str, float] | None = None,
        generator: OutfitGenerator | None = None,
    ) -> None:
        self.components = (
            components if components is not None else [c() for c in self.DEFAULT_COMPONENTS]
        )
        self.weights = dict(weights) if weights is not None else dict(self.DEFAULT_WEIGHTS)
        self.generator = generator or OutfitGenerator()

    def score_outfit(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ScoredOutfit:
        """Bewertet ein einzelnes Outfit mit transparenter Aufschlüsselung."""
        results = []
        for component in self.components:
            result = component.score(outfit, context, history)
            result.weight = self.weights.get(result.component, 0.0)
            results.append(result)
        total = sum(r.score * r.weight for r in results)
        return ScoredOutfit(outfit=outfit, total=round(total, 4), components=results)

    def recommend(
        self,
        wardrobe: Wardrobe,
        context: OutfitContext,
        history: list[Outfit] | None = None,
        top_k: int = 1,
        max_outfits: int | None = None,
    ) -> list[ScoredOutfit]:
        """Generiert alle Outfits, bewertet sie und liefert die besten."""
        outfits = self.generator.generate(wardrobe, context=context, limit=max_outfits)
        scored = [self.score_outfit(o, context, history) for o in outfits]
        scored.sort(key=lambda s: s.total, reverse=True)
        return scored[:top_k]
