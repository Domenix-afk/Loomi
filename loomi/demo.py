"""Kommandozeilen-Demo für Loomis Outfit-Recommendation.

Ausführen mit:  python -m loomi.demo
"""

from __future__ import annotations

from .models import Category, Occasion, Outfit, OutfitContext, Style, WeatherCondition
from .recommender import Recommender
from .wardrobe import sample_wardrobe

_SLOT_ORDER = (
    Category.TOP,
    Category.BOTTOM,
    Category.OUTERWEAR,
    Category.SHOES,
    Category.ACCESSORY,
)


def format_outfit(outfit: Outfit) -> str:
    parts = []
    for category in _SLOT_ORDER:
        item = outfit.items.get(category)
        if item:
            parts.append(f"{item.name} ({category.value})")
    return " + ".join(parts)


def print_results(title: str, ctx: OutfitContext, scored: list, top: int = 3) -> None:
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print(f"    Wetter: {ctx.temperature:.0f} °C, {ctx.condition.value}"
          f" | Anlass: {ctx.occasion.value}"
          + (f" | Wunsch-Style: {ctx.preferred_style.value}" if ctx.preferred_style else ""))
    for rank, entry in enumerate(scored[:top], 1):
        print(f"\n  #{rank}  Gesamt-Score: {entry.total:.3f}")
        print(f"      {format_outfit(entry.outfit)}")
        for comp in entry.components:
            print(f"        {comp.component:<9} {comp.score:.3f}  (Gewicht {comp.weight:.2f})  {comp.details}")


def main() -> None:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass  # Konsole ohne reconfigure-Unterstützung

    wardrobe = sample_wardrobe()
    recommender = Recommender()

    count = f"{recommender.generator.outfit_count(wardrobe):,}".replace(",", ".")
    print(f"Kleiderschrank: {len(wardrobe)} Kleidungsstücke, "
          f"{count} mögliche Outfits")

    scenarios = [
        ("Sommerlicher Stadtbummel",
         OutfitContext(24.0, WeatherCondition.SUNNY, Occasion.CASUAL, Style.CASUAL)),
        ("Bürotag im Regen",
         OutfitContext(9.0, WeatherCondition.RAIN, Occasion.WORK, Style.SMART_CASUAL)),
        ("Sport am Morgen",
         OutfitContext(18.0, WeatherCondition.CLOUDY, Occasion.SPORT, Style.SPORTY)),
        ("Formeller Abend",
         OutfitContext(14.0, WeatherCondition.CLOUDY, Occasion.FORMAL, Style.ELEGANT)),
    ]
    for title, ctx in scenarios:
        scored = recommender.recommend(wardrobe, ctx, top_k=3)
        print_results(title, ctx, scored)

    # Abwechslung demonstrieren: gleicher Kontext, zweite Empfehlung mit Historie.
    ctx = OutfitContext(24.0, WeatherCondition.SUNNY, Occasion.CASUAL, Style.CASUAL)
    first = recommender.recommend(wardrobe, ctx, top_k=1)[0]
    second = recommender.recommend(wardrobe, ctx, history=[first.outfit], top_k=1)[0]

    print(f"\n{'=' * 70}")
    print("Abwechslung: gleicher Kontext, zweite Empfehlung")
    print(f"  1. Empfehlung: {format_outfit(first.outfit)}   (Score {first.total:.3f})")
    print(f"  2. Empfehlung: {format_outfit(second.outfit)}   (Score {second.total:.3f})")
    for comp in second.components:
        if comp.component == "variety":
            print(f"    variety: {comp.score:.3f} – {comp.details}")


if __name__ == "__main__":
    main()
