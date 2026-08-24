"""Outfit-Generator: bildet alle gültigen Kombinationen aus dem Kleiderschrank."""

from __future__ import annotations

from itertools import product

from .models import Category, Outfit, OutfitContext
from .wardrobe import Wardrobe


class OutfitGenerator:
    """Erzeugt Outfit-Kombinationen aus dem Kleiderschrank.

    Pflicht-Kategorien (Standard: Top, Bottom) müssen besetzt sein,
    optionale Kategorien (Standard: Jacke, Schuhe, Accessoire) dürfen
    fehlen. Der Generator ist bewusst frei von Bewertungslogik – was
    sinnvoll ist, entscheidet ausschließlich das Scoring-System.
    """

    def __init__(
        self,
        required: tuple[Category, ...] = (Category.TOP, Category.BOTTOM),
        optional: tuple[Category, ...] = (Category.OUTERWEAR, Category.SHOES, Category.ACCESSORY),
    ) -> None:
        self.required = tuple(required)
        self.optional = tuple(optional)

    def outfit_count(self, wardrobe: Wardrobe) -> int:
        """Anzahl möglicher Kombinationen (ohne Limit)."""
        count = 1
        for category in self.required:
            count *= len(wardrobe.by_category(category))
        for category in self.optional:
            count *= len(wardrobe.by_category(category)) + 1
        return count

    def generate(
        self,
        wardrobe: Wardrobe,
        context: OutfitContext | None = None,
        limit: int | None = None,
    ) -> list[Outfit]:
        """Erzeugt alle gültigen Kombinationen.

        `limit` begrenzt die Anzahl (Kappung in deterministischer
        Reihenfolge) – nützlich für sehr große Kleiderschränke.
        """
        pools = []
        for category in self.required:
            items = wardrobe.by_category(category)
            if not items:
                return []
            pools.append(items)
        for category in self.optional:
            pools.append(wardrobe.by_category(category) + [None])

        outfits: list[Outfit] = []
        for combo in product(*pools):
            items = {}
            for category, item in zip(self.required, combo[: len(self.required)]):
                items[category] = item
            for category, item in zip(self.optional, combo[len(self.required) :]):
                if item is not None:
                    items[category] = item
            outfits.append(Outfit(items))
            if limit is not None and len(outfits) >= limit:
                break
        return outfits
