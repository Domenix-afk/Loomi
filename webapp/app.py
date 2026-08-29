"""LoomiApp – API-Schicht über dem bestehenden Loomi-Kern.

Diese Klasse bündelt die gesamte Funktionalität, die der Web-Server
anbietet. Sie nutzt ausschließlich bereits existierende Loomi-Bausteine
(Recommender, WardrobeStore, PreferenceStore, PreferenceProfile, Modelle)
und enthält keinerlei HTTP-Logik – dadurch ist sie unabhängig testbar.

Der Kleiderschrank kommt immer aus der SQLite-Datenbank, das
Präferenzprofil wird beim Start geladen und nach jeder Bewertung
gespeichert (Vorlieben überleben Sitzungen).
"""

from __future__ import annotations

import uuid

from loomi.models import (
    Category,
    ClothingItem,
    ColorFamily,
    Occasion,
    Outfit,
    OutfitContext,
    OutfitFeedback,
    ScoredOutfit,
    Style,
    WeatherCondition,
)
from loomi.preferences import PreferenceProfile
from loomi.recommender import Recommender
from loomi.storage import PreferenceStore, WardrobeStore
from loomi.wardrobe import sample_wardrobe

# Reihenfolge der Slots für die Anzeige (wie in der CLI-Demo).
_SLOT_ORDER = (
    Category.TOP,
    Category.BOTTOM,
    Category.OUTERWEAR,
    Category.SHOES,
    Category.ACCESSORY,
)

# Deutsche Anzeigenamen (für die Profil-Ansicht).
_ATTR_LABELS = {
    "category": "Kategorie",
    "color": "Farbe",
    "style": "Stil",
    "warmth": "Wärme",
    "formality": "Formalität",
}


def _parse_enum(enum, value: str, field: str):
    try:
        return enum(value)
    except (ValueError, TypeError):
        raise ValueError(f"Ungültiger Wert für {field}: {value!r}") from None


def _parse_temperature(value) -> float:
    try:
        temperature = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Ungültige Temperatur: {value!r}") from None
    if not -40 <= temperature <= 50:
        raise ValueError("Temperatur muss zwischen -40 und 50 °C liegen")
    return temperature


def _parse_rating(value) -> int:
    try:
        rating = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Ungültige Bewertung: {value!r}") from None
    if not 1 <= rating <= 5:
        raise ValueError("Bewertung muss zwischen 1 und 5 liegen")
    return rating


def item_dict(item: ClothingItem) -> dict:
    """Serialisiert ein Kleidungsstück für die JSON-API."""
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category.value,
        "color": item.color.value,
        "style": item.style.value,
        "warmth": item.warmth,
        "formality": item.formality,
    }


def context_dict(context: OutfitContext) -> dict:
    return {
        "temperature": context.temperature,
        "condition": context.condition.value,
        "occasion": context.occasion.value,
        "preferred_style": context.preferred_style.value if context.preferred_style else None,
    }


def scored_dict(scored: ScoredOutfit) -> dict:
    """Serialisiert ein bewertetes Outfit inkl. transparenter Aufschlüsselung."""
    items = [
        {"slot": category.value, **item_dict(item)}
        for category, item in sorted(
            scored.outfit.items.items(), key=lambda kv: _SLOT_ORDER.index(kv[0])
        )
    ]
    components = [
        {
            "component": comp.component,
            "score": comp.score,
            "weight": comp.weight,
            "details": comp.details,
        }
        for comp in scored.components
    ]
    return {"total": scored.total, "outfit": {"items": items}, "components": components}


class LoomiApp:
    """Bedient die Web-UI mit den bereits vorhandenen Loomi-Funktionen."""

    def __init__(self, db_path: str = "loomi.db") -> None:
        self.db_path = str(db_path)
        self.wardrobe_store = WardrobeStore(self.db_path)
        self.pref_store = PreferenceStore(self.db_path)
        self.profile = self.pref_store.load() or PreferenceProfile()
        self.recommender = Recommender(preference_profile=self.profile)

    # --- Kleiderschrank ---

    def list_items(self) -> dict:
        items = [item_dict(i) for i in self.wardrobe_store.load().items]
        return {"count": len(items), "items": items}

    def add_item(self, payload: dict) -> dict:
        """Legt ein Kleidungsstück an (Validierung wie in main.py)."""
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("Name darf nicht leer sein")
        category = _parse_enum(Category, payload.get("category"), "category")
        color = _parse_enum(ColorFamily, payload.get("color"), "color")
        style = _parse_enum(Style, payload.get("style"), "style")
        try:
            warmth = int(payload.get("warmth"))
            formality = int(payload.get("formality"))
        except (ValueError, TypeError):
            raise ValueError("Wärme und Formalität müssen Zahlen von 1 bis 5 sein") from None
        if not 1 <= warmth <= 5 or not 1 <= formality <= 5:
            raise ValueError("Wärme und Formalität müssen zwischen 1 und 5 liegen")
        item_id = f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        item = ClothingItem(item_id, name, category, color, style, warmth, formality)
        self.wardrobe_store.save(item)
        return item_dict(item)

    def delete_item(self, item_id: str) -> dict:
        if self.wardrobe_store.load().get(item_id) is None:
            raise KeyError(f"Kleidungsstück {item_id!r} nicht gefunden")
        self.wardrobe_store.delete(item_id)
        return {"deleted": item_id}

    def load_sample(self) -> dict:
        """Fügt die 32 Beispiel-Teile hinzu (idempotent, wie in main.py)."""
        sample = sample_wardrobe()
        existing = {item.id for item in self.wardrobe_store.load().items}
        added = 0
        for item in sample.items:
            if item.id not in existing:
                self.wardrobe_store.save(item)
                added += 1
        return {"added": added, "total": len(sample.items)}

    def remove_sample(self) -> dict:
        """Entfernt nur die Beispiel-Teile (eigene bleiben erhalten)."""
        sample_ids = {item.id for item in sample_wardrobe().items}
        to_remove = [
            item for item in self.wardrobe_store.load().items if item.id in sample_ids
        ]
        for item in to_remove:
            self.wardrobe_store.delete(item.id)
        return {"removed": len(to_remove)}

    # --- Empfehlung ---

    def _context_from_payload(self, payload: dict) -> OutfitContext:
        temperature = _parse_temperature(payload.get("temperature", 20))
        condition = _parse_enum(WeatherCondition, payload.get("condition", "sunny"), "condition")
        occasion = _parse_enum(Occasion, payload.get("occasion", "casual"), "occasion")
        style_raw = payload.get("preferred_style")
        preferred_style = None
        if style_raw:
            preferred_style = _parse_enum(Style, style_raw, "preferred_style")
        return OutfitContext(temperature, condition, occasion, preferred_style)

    def recommend(self, payload: dict) -> dict:
        """Empfiehlt die besten Outfits (identische Logik wie Recommender.recommend)."""
        context = self._context_from_payload(payload)
        try:
            top_k = int(payload.get("top_k", 3))
        except (ValueError, TypeError):
            top_k = 3
        wardrobe = self.wardrobe_store.load()
        scored = self.recommender.recommend(wardrobe, context, top_k=max(1, top_k))
        return {
            "context": context_dict(context),
            "wardrobe_count": len(wardrobe),
            "outfits": [scored_dict(s) for s in scored],
        }

    # --- Feedback & Präferenzprofil ---

    def add_feedback(self, payload: dict) -> dict:
        """Verarbeitet eine Bewertung (1–5) wie im interaktiven Flow."""
        rating = _parse_rating(payload.get("rating"))
        outfit_payload = payload.get("outfit")
        if isinstance(outfit_payload, list):
            items_payload = outfit_payload  # direktes Item-Array tolerieren
        elif isinstance(outfit_payload, dict):
            items_payload = outfit_payload.get("items", [])
        else:
            items_payload = []
        if not items_payload:
            raise ValueError("Feedback benötigt das bewertete Outfit")

        wardrobe = self.wardrobe_store.load()
        items: dict[Category, ClothingItem] = {}
        for entry in items_payload:
            item = wardrobe.get(entry.get("id", ""))
            if item is None:
                raise ValueError(
                    f"Kleidungsstück {entry.get('id')!r} ist nicht mehr im Kleiderschrank"
                )
            items[item.category] = item
        if not items:
            raise ValueError("Outfit enthält keine Kleidungsstücke")

        context = None
        ctx_payload = payload.get("context")
        if isinstance(ctx_payload, dict):
            context = self._context_from_payload(ctx_payload)

        self.profile.update(OutfitFeedback(Outfit(items), rating, context))
        self.pref_store.save(self.profile)
        return {"rating": rating, "feedback_count": self.profile.feedback_count}

    def preferences(self) -> dict:
        """Liefert den gelernten Präferenz-Zustand für die Profil-Ansicht."""
        data = self.profile.to_dict()
        values = []
        for attr in ("category", "color", "style"):
            for value, signed in data["cat"].get(attr, {}).items():
                count = data["cat_count"].get(attr, {}).get(value, 0)
                if count:
                    values.append(
                        {
                            "attribute": attr,
                            "label": _ATTR_LABELS[attr],
                            "value": value,
                            "score": round(0.5 + 0.5 * signed / count, 3),
                            "count": count,
                        }
                    )
        values.sort(key=lambda v: abs(v["score"] - 0.5), reverse=True)
        numeric = {}
        for attr in ("warmth", "formality"):
            total = data["num_total"].get(attr, 0)
            if total:
                numeric[attr] = {
                    "label": _ATTR_LABELS[attr],
                    "preferred": round(3.0 + data["num_signed"].get(attr, 0) / total, 2),
                    "count": total,
                }
        return {
            "feedback_count": self.profile.feedback_count,
            "values": values,
            "numeric": numeric,
        }

    def reset_preferences(self) -> dict:
        self.pref_store.delete()
        self.profile = PreferenceProfile()
        self.recommender = Recommender(preference_profile=self.profile)
        return {"feedback_count": 0}
