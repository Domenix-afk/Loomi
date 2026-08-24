"""Abwechslung: Vermeidet Wiederholungen zuletzt empfohlener Kleidungsstücke."""

from __future__ import annotations

from ..models import ComponentScore, Outfit, OutfitContext
from .base import ScoreComponent


class Variety(ScoreComponent):
    """Bewertet, wie neu ein Outfit gegenüber früheren Empfehlungen ist.

    Je mehr Kleidungsstücke kürzlich empfohlen wurden, desto niedriger
    der Score. Ohne Historie gibt es volle Abwechslung (Score 1.0).
    """

    name = "variety"

    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        if not history:
            return ComponentScore(self.name, 1.0, 1.0, "Keine Historie – volle Abwechslung")

        seen: set[str] = set()
        for past in history:
            seen.update(item.id for item in past.items.values())

        ids = {item.id for item in outfit.items.values()}
        overlap = len(ids & seen) / len(ids)
        final = 1.0 - overlap
        details = (
            f"{len(ids & seen)} von {len(ids)} Kleidungsstücken "
            f"kürzlich empfohlen"
        )
        return ComponentScore(self.name, round(final, 4), 1.0, details)
