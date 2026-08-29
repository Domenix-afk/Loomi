"""Hauptprogramm für Loomi: Kleiderschrank verwalten (SQLite) oder Outfit-Empfehlung.

Start-Menü:
    1. Kleiderschrank (Wardrobe) – Kleidungsstücke hinzufügen oder löschen
    2. Loomi – Wetter eingeben -> Outfit-Empfehlung + Feedback

Ausführen mit:
    python -m loomi.main            # Datenbank loomi.db im Projektordner
    python -m loomi.main --db pfad  # andere Datenbank verwenden
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Callable

from .demo import run_interactive
from .models import Category, ClothingItem, ColorFamily, Style
from .preferences import PreferenceProfile
from .recommender import Recommender
from .storage import PreferenceStore, WardrobeStore
from .wardrobe import sample_wardrobe


def _ask_choice(
    ask: Callable[[str], str],
    label: str,
    options: list,
    default,
) -> object:
    choices = ", ".join(f"{i}={o.value}" for i, o in enumerate(options, 1))
    while True:
        raw = ask(f"{label} [{default.value}] ({choices}): ").strip().lower()
        if not raw:
            return default
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1]
        for option in options:
            if raw == option.value:
                return option
        print(f"  Ungültige Eingabe '{raw}' – bitte Index oder Wert angeben.")


def _ask_scale(ask: Callable[[str], str], label: str, default: int) -> int:
    while True:
        raw = ask(f"{label} 1–5 [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return int(raw)
        print("  Bitte eine Zahl von 1 bis 5 eingeben.")


def ask_new_item(ask: Callable[[str], str] = input) -> ClothingItem | None:
    """Fragt alle wichtigen Infos für ein Kleidungsstück ab.

    None, wenn abgebrochen (Enter beim Namen).
    """
    name = ask("Name des Kleidungsstücks (Enter = fertig): ").strip()
    if not name:
        return None
    category = _ask_choice(ask, "Kategorie", list(Category), Category.TOP)
    color = _ask_choice(ask, "Farbe", list(ColorFamily), ColorFamily.NEUTRAL)
    style = _ask_choice(ask, "Stil", list(Style), Style.CASUAL)
    warmth = _ask_scale(ask, "Wärme (1 = leicht, 5 = warm)", 3)
    formality = _ask_scale(ask, "Formalität (1 = leger, 5 = formell)", 2)
    item_id = f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    return ClothingItem(item_id, name, category, color, style, warmth, formality)


def _select_item(
    ask: Callable[[str], str],
    items: list[ClothingItem],
) -> ClothingItem | None:
    """Listet Kleidungsstücke und fragt, welches gewählt werden soll."""
    print("  Vorhandene Kleidungsstücke:")
    for i, item in enumerate(items, 1):
        print(f"    {i}. {item.name} ({item.category.value}, {item.color.value})")
    while True:
        pick = ask("  Welches? (Nummer oder Name, Enter = abbrechen): ").strip()
        if not pick:
            return None
        if pick.isdigit():
            index = int(pick)
            if 1 <= index <= len(items):
                return items[index - 1]
        else:
            for item in items:
                if item.name.lower() == pick.lower():
                    return item
        print("  Nicht gefunden – bitte Nummer oder Namen angeben.")


def load_sample_items(store: WardrobeStore) -> None:
    """Fügt die 32 Beispiel-Kleidungsstücke zur Datenbank hinzu (idempotent)."""
    sample = sample_wardrobe()
    existing = {item.id for item in store.load().items}
    added = 0
    for item in sample.items:
        if item.id not in existing:
            store.save(item)
            added += 1
    total = len(sample.items)
    if added == total:
        print(f"  {total} Beispiel-Kleidungsstücke hinzugefügt.")
    else:
        print(f"  {added} Beispiel-Kleidungsstücke hinzugefügt "
              f"({total - added} waren bereits vorhanden).")


def remove_sample_items(store: WardrobeStore) -> None:
    """Entfernt die Beispiel-Kleidungsstücke per Befehl aus der Datenbank."""
    sample_ids = {item.id for item in sample_wardrobe().items}
    to_remove = [item for item in store.load().items if item.id in sample_ids]
    for item in to_remove:
        store.delete(item.id)
    if to_remove:
        print(f"  {len(to_remove)} Beispiel-Kleidungsstücke entfernt.")
    else:
        print("  Keine Beispiel-Kleidungsstücke in der Datenbank.")


def wardrobe_menu(
    store: WardrobeStore,
    ask: Callable[[str], str] = input,
) -> None:
    """Kleiderschrank verwalten: Kleidungsstücke hinzufügen oder löschen."""
    while True:
        wardrobe = store.load()
        raw = ask(
            f"\nKleiderschrank ({len(wardrobe)} Stücke): "
            "(1) Hinzufügen, (2) Löschen, (3) Beispieldaten laden, "
            "(4) Beispieldaten entfernen, (Enter) Fertig: "
        ).strip().lower()
        if not raw:
            return
        if raw in ("1", "hinzufügen", "hinzufuegen", "add"):
            item = ask_new_item(ask)
            if item is None:
                continue
            store.save(item)
            print(f"  Gespeichert: {item.name} ({item.category.value}, {item.color.value}, "
                  f"Wärme {item.warmth}, Formalität {item.formality})")
        elif raw in ("2", "löschen", "loeschen", "delete"):
            items = wardrobe.items
            if not items:
                print("  Der Kleiderschrank ist leer – nichts zu löschen.")
                continue
            selected = _select_item(ask, items)
            if selected is None:
                continue
            store.delete(selected.id)
            print(f"  Gelöscht: {selected.name}")
        elif raw in ("3", "beispieldaten", "beispiel", "sample"):
            load_sample_items(store)
        elif raw in ("4", "beispieldaten-entfernen", "sample-entfernen"):
            remove_sample_items(store)
        else:
            print("  Ungültige Eingabe – bitte 1–4 oder Enter wählen.")


def loomi_session(
    store: WardrobeStore,
    pref_store: PreferenceStore | None = None,
    ask: Callable[[str], str] = input,
) -> None:
    """Loomi-Modus: Wetter eingeben, Outfits empfohlen bekommen, Feedback geben.

    Mit `pref_store` werden gelernte Vorlieben aus früheren Sitzungen
    geladen und nach der Sitzung wieder gespeichert (überlebt Neustarts).
    Ohne `pref_store` bleibt das Profil auf die Sitzung beschränkt.
    """
    wardrobe = store.load()
    if not wardrobe.items:
        raw = ask("\nDer Kleiderschrank ist leer. Beispieldaten laden? (j/N): ").strip().lower()
        if raw in ("j", "ja", "y", "yes"):
            wardrobe = sample_wardrobe()
            print(f"  {len(wardrobe)} Beispiel-Kleidungsstücke geladen.")
        else:
            print("Ohne Kleidung gibt es nichts zu empfehlen.")
            return

    # Gelernte Vorlieben aus früheren Sitzungen laden (falls vorhanden).
    profile = pref_store.load() if pref_store is not None else None
    if profile is None:
        profile = PreferenceProfile()
    recommender = Recommender(preference_profile=profile)
    count = f"{recommender.generator.outfit_count(wardrobe):,}".replace(",", ".")
    print(f"\nKleiderschrank: {len(wardrobe)} Kleidungsstücke, {count} mögliche Outfits")
    run_interactive(recommender, wardrobe, ask=ask, profile=profile)
    if pref_store is not None:
        pref_store.save(profile)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass  # Konsole ohne reconfigure-Unterstützung

    parser = argparse.ArgumentParser(
        description="Loomi – Kleiderschrank verwalten oder Outfits empfohlen bekommen"
    )
    parser.add_argument(
        "--db",
        default="loomi.db",
        help="Pfad zur SQLite-Datenbank (Standard: loomi.db)",
    )
    args = parser.parse_args()

    store = WardrobeStore(args.db)

    print("=== Loomi – dein persönlicher Style-Assistent ===")
    print(f"Datenbank: {args.db} ({store.count()} Kleidungsstücke)")

    while True:
        try:
            raw = input(
                "\nWas möchtest du tun?\n"
                "  (1) Kleiderschrank (Wardrobe) – Kleidung verwalten\n"
                "  (2) Loomi – Outfit-Empfehlung\n"
                "  (Enter) Beenden\n"
                "Wahl: "
            ).strip().lower()
        except EOFError:
            print("\nBis bald!")
            return
        if not raw:
            print("Bis bald!")
            return
        if raw in ("1", "kleiderschrank", "wardrobe"):
            wardrobe_menu(store)
        elif raw in ("2", "loomi", "generator"):
            loomi_session(store, PreferenceStore(args.db))
        else:
            print("  Ungültige Eingabe – bitte 1, 2 oder Enter wählen.")


if __name__ == "__main__":
    main()
