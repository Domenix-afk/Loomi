"""Kommandozeilen-Demo für Loomis Outfit-Recommendation.

Ausführen mit:
    python -m loomi.demo          # Beispiel-Szenarien
    python -m loomi.demo -i       # eigenes Wetter & Kontext interaktiv eingeben
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from .models import (
    Category,
    Occasion,
    Outfit,
    OutfitContext,
    OutfitFeedback,
    ScoredOutfit,
    Style,
    WeatherCondition,
)
from .preferences import PreferenceProfile
from .recommender import Recommender
from .wardrobe import Wardrobe, sample_wardrobe

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


def _ask_temperature(ask: Callable[[str], str]) -> float:
    while True:
        raw = ask("Aktuelle Temperatur in °C [20]: ").strip().replace(",", ".")
        if not raw:
            return 20.0
        try:
            value = float(raw)
        except ValueError:
            print(f"  Ungültige Temperatur '{raw}' – bitte eine Zahl eingeben.")
            continue
        if -40 <= value <= 50:
            return value
        print("  Bitte einen Wert zwischen -40 und 50 °C angeben.")


def _ask_condition(ask: Callable[[str], str]) -> WeatherCondition:
    choices = ", ".join(
        f"{i}={option.value}" for i, option in enumerate(WeatherCondition, 1)
    )
    while True:
        raw = ask(f"Wetterlage [sunny] ({choices}): ").strip().lower()
        if not raw:
            return WeatherCondition.SUNNY
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(WeatherCondition):
                return list(WeatherCondition)[index - 1]
        for option in WeatherCondition:
            if raw == option.value:
                return option
        print(f"  Ungültige Eingabe '{raw}' – bitte Index oder Wert angeben.")


def ask_context(
    ask: Callable[[str], str] = input,
    occasion: Occasion = Occasion.CASUAL,
) -> OutfitContext:
    """Fragt interaktiv nur das aktuelle Wetter ab (Temperatur + Wetterlage).

    Anlass und Wunsch-Style werden nicht abgefragt, sondern auf sensible
    Defaults gesetzt (Standard: casual / keiner) – per Parameter änderbar.
    `ask` ist injizierbar, damit die Eingabe-Logik testbar bleibt.
    """
    print("\n=== Wetter-Eingabe (Enter = Vorschlag) ===")
    temperature = _ask_temperature(ask)
    condition = _ask_condition(ask)
    return OutfitContext(temperature, condition, occasion, None)


def ask_feedback(
    ask: Callable[[str], str],
    scored: ScoredOutfit,
    context: OutfitContext | None = None,
) -> OutfitFeedback | None:
    """Fragt nach einer Bewertung (1–5) für das beste Outfit.

    Enter = kein Feedback (liefert `None`). `ask` ist injizierbar,
    damit die Logik testbar bleibt.
    """
    while True:
        raw = ask("\nWie gefällt dir das beste Outfit? (1–5, Enter = überspringen): ").strip()
        if not raw:
            return None
        if raw.isdigit():
            rating = int(raw)
            if 1 <= rating <= 5:
                return OutfitFeedback(outfit=scored.outfit, rating=rating, context=context)
        print("  Bitte eine Zahl von 1 bis 5 eingeben (Enter = überspringen).")


def run_interactive(
    recommender: Recommender,
    wardrobe: Wardrobe,
    ask: Callable[[str], str] = input,
    profile: PreferenceProfile | None = None,
) -> None:
    """Interaktive Schleife: Wetter eingeben, Empfehlung bekommen, Feedback geben.

    Der Ablauf (Fragen, Ausgaben) ist bewusst unverändert – lediglich das
    erfasste Feedback wird zusätzlich in das `PreferenceProfile` eingespeist,
    damit spätere Empfehlungen persönlicher werden.
    """
    while True:
        context = ask_context(ask)
        scored = recommender.recommend(wardrobe, context, top_k=3)
        if not scored:
            print("\n  Keine Outfits möglich – im Kleiderschrank fehlen z. B. Top oder Bottom.")
            again = ask("\nNoch eine Empfehlung? (j/N): ").strip().lower()
            if again not in ("j", "ja", "y", "yes"):
                print("Bis bald!")
                return
            continue
        print_results("Deine Empfehlung", context, scored)
        feedback = ask_feedback(ask, scored[0], context)
        if feedback is not None:
            print(f"  Danke! Dein Feedback ({feedback.rating}/5) wurde erfasst.")
            if profile is not None:
                profile.update(feedback)
        again = ask("\nNoch eine Empfehlung? (j/N): ").strip().lower()
        if again not in ("j", "ja", "y", "yes"):
            print("Bis bald!")
            return


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass  # Konsole ohne reconfigure-Unterstützung

    parser = argparse.ArgumentParser(
        description="Loomi – Outfit-Empfehlung (Personal-Style-Engine)"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Wetter und Kontext interaktiv eingeben statt der Beispiel-Szenarien",
    )
    args = parser.parse_args()

    wardrobe = sample_wardrobe()
    profile = PreferenceProfile()
    recommender = Recommender(preference_profile=profile)

    count = f"{recommender.generator.outfit_count(wardrobe):,}".replace(",", ".")
    print(f"Kleiderschrank: {len(wardrobe)} Kleidungsstücke, "
          f"{count} mögliche Outfits")

    if args.interactive:
        run_interactive(recommender, wardrobe, profile=profile)
        return

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
