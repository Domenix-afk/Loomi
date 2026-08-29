"""Persönliches Präferenzprofil: lernt aus Outfit-Feedback (1–5).

Bewusst einfach und deterministisch gehalten – kein ML. Aus jeder
Bewertung werden die Attribute der enthaltenen Kleidungsstücke gelernt
(Kategorie, Farbe, Stil, Wärme, Formalität). Positive Bewertungen
stärken Präferenzen, negative schwächen sie. Ohne Daten liefert das
Profil für jedes Outfit exakt 0.5 (neutral), sodass die Empfehlung
unverändert bleibt, bis erstes Feedback vorliegt.
"""

from __future__ import annotations

from collections import defaultdict

from .models import Category, ClothingItem, ColorFamily, Outfit, OutfitFeedback, Style

# Attribute, aus denen gelernt wird (kategorisch vs. numerisch).
_CATEGORICAL = ("category", "color", "style")
_NUMERIC = ("warmth", "formality")

_LABELS = {
    "category": "Kategorie",
    "color": "Farbe",
    "style": "Stil",
    "warmth": "Wärme",
    "formality": "Formalität",
}

# Enum-Typ je kategorischem Attribut (für die (De-)Serialisierung).
_ENUMS = {
    "category": Category,
    "color": ColorFamily,
    "style": Style,
}


class PreferenceProfile:
    """Deterministisches Präferenzmodell auf Basis von OutfitFeedback (1–5).

    Bewertungen >= 4 stärken Präferenzen, Bewertungen <= 2 schwächen sie,
    Bewertung 3 ist neutral. Die gelernten Werte sind reproduzierbar:
    gleiche Feedback-Sequenz -> gleiches Profil.
    """

    def __init__(self) -> None:
        # Kategorische Attribute: Wert -> aufsummiertes Delta ([-1, 1] je Feedback)
        # sowie Anzahl der Beobachtungen dieses Werts.
        self._cat: dict[str, dict[object, float]] = defaultdict(dict)
        self._cat_count: dict[str, dict[object, float]] = defaultdict(dict)
        # Numerische Attribute: Abweichung vom Neutralwert 3, aufsummiert.
        self._num_signed: dict[str, float] = defaultdict(float)
        self._num_total: dict[str, float] = defaultdict(float)
        self._feedbacks: int = 0

    @property
    def feedback_count(self) -> int:
        """Anzahl der bisher verarbeiteten Bewertungen."""
        return self._feedbacks

    def update(self, feedback: OutfitFeedback) -> None:
        """Lernt aus einer einzelnen Outfit-Bewertung (1–5)."""
        delta = (feedback.rating - 3) / 2  # 5 -> +1, 1 -> -1, 3 -> 0
        for item in feedback.outfit.items.values():
            for attr in _CATEGORICAL:
                value = getattr(item, attr)
                signed = self._cat[attr]
                signed[value] = signed.get(value, 0.0) + delta
                count = self._cat_count[attr]
                count[value] = count.get(value, 0.0) + 1.0
            for attr in _NUMERIC:
                value = float(getattr(item, attr))
                self._num_signed[attr] += delta * (value - 3.0)
                self._num_total[attr] += 1.0
        self._feedbacks += 1

    def _cat_score(self, attr: str, value: object) -> float:
        count = self._cat_count[attr].get(value, 0.0)
        if count <= 0:
            return 0.5  # keine Daten -> neutral
        signed = self._cat[attr].get(value, 0.0)
        return round(0.5 + 0.5 * (signed / count), 4)

    def _num_score(self, attr: str, value: int) -> float:
        total = self._num_total.get(attr, 0.0)
        if total <= 0:
            return 0.5  # keine Daten -> neutral
        preferred = 3.0 + self._num_signed[attr] / total
        distance = abs(value - preferred)
        return round(max(0.0, 1.0 - distance / 4.0), 4)

    def _score(self, attr: str, value: object) -> float:
        if attr in _NUMERIC:
            return self._num_score(attr, int(value))
        return self._cat_score(attr, value)

    def score_item(self, item: ClothingItem) -> float:
        """Präferenz-Score eines einzelnen Kleidungsstücks (0..1, 0.5 = neutral)."""
        scores = [self._score(attr, getattr(item, attr)) for attr in _LABELS]
        return round(sum(scores) / len(scores), 4)

    def attribute_scores(self, outfit: Outfit) -> dict[str, float]:
        """Mittlere Präferenz je Attribut über alle Kleidungsstücke des Outfits."""
        if not outfit.items:
            return {attr: 0.5 for attr in _LABELS}
        result = {}
        for attr in _LABELS:
            values = [getattr(item, attr) for item in outfit.items.values()]
            result[attr] = round(sum(self._score(attr, v) for v in values) / len(values), 4)
        return result

    def score_outfit(self, outfit: Outfit) -> float:
        """Präferenz-Score eines Outfits (0..1, 0.5 = neutral)."""
        scores = self.attribute_scores(outfit).values()
        return round(sum(scores) / len(scores), 4)

    def describe(self, outfit: Outfit) -> str:
        """Kompakte, erklärbare Begründung für den Score eines Outfits."""
        if self._feedbacks == 0:
            return "Keine Präferenzdaten – neutral"
        scores = self.attribute_scores(outfit)
        parts = ", ".join(f"{_LABELS[attr]} {score:.2f}" for attr, score in scores.items())
        return f"aus {self._feedbacks} Bewertungen – {parts}"

    def to_dict(self) -> dict:
        """Serialisiert den Lernzustand (z. B. für SQLite/JSON).

        Enum-Werte werden als Strings abgelegt; `from_dict` stellt sie
        wieder her. Das Ergebnis ist deterministisch und damit als
        JSON-Blob speicherbar.
        """
        return {
            "feedbacks": self._feedbacks,
            "cat": {
                attr: {value.value: signed for value, signed in values.items()}
                for attr, values in self._cat.items()
            },
            "cat_count": {
                attr: {value.value: count for value, count in values.items()}
                for attr, values in self._cat_count.items()
            },
            "num_signed": dict(self._num_signed),
            "num_total": dict(self._num_total),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreferenceProfile":
        """Stellt ein Profil aus `to_dict()` wieder her."""
        profile = cls()
        profile._feedbacks = int(data.get("feedbacks", 0))
        for attr in _CATEGORICAL:
            enum = _ENUMS[attr]
            cat = data.get("cat", {}).get(attr, {})
            if cat:
                profile._cat[attr] = {
                    enum(value): float(signed) for value, signed in cat.items()
                }
            cat_count = data.get("cat_count", {}).get(attr, {})
            if cat_count:
                profile._cat_count[attr] = {
                    enum(value): float(count) for value, count in cat_count.items()
                }
        for attr in _NUMERIC:
            num_signed = data.get("num_signed", {})
            if attr in num_signed:
                profile._num_signed[attr] = float(num_signed[attr])
            num_total = data.get("num_total", {})
            if attr in num_total:
                profile._num_total[attr] = float(num_total[attr])
        return profile
