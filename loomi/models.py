"""Zentrale Datenmodelle für Loomis Personal-Style-Engine.

Hier liegen alle Domänenobjekte: Kleidungsstücke, Empfehlungskontext,
Outfits sowie die Ergebnis-Typen des Scoring-Systems. Die Module für
Generierung, Scoring und Empfehlung hängen nur von diesen Typen ab und
können dadurch unabhängig voneinander erweitert werden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Category(str, Enum):
    """Kategorie eines Kleidungsstücks."""

    TOP = "top"
    BOTTOM = "bottom"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"


class Style(str, Enum):
    """Modestil eines Kleidungsstücks."""

    CASUAL = "casual"
    SMART_CASUAL = "smart_casual"
    SPORTY = "sporty"
    ELEGANT = "elegant"
    STREETWEAR = "streetwear"
    BUSINESS = "business"
    BOHO = "boho"


class ColorFamily(str, Enum):
    """Farbfamilie für die Farbharmonie-Berechnung."""

    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    PINK = "pink"
    BROWN = "brown"
    NEUTRAL = "neutral"  # schwarz, weiß, grau, beige


class WeatherCondition(str, Enum):
    """Wetterlage, die der Nutzer mitgibt."""

    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    WINDY = "windy"


class Occasion(str, Enum):
    """Anlass, für den empfohlen wird."""

    CASUAL = "casual"
    WORK = "work"
    DATE = "date"
    PARTY = "party"
    SPORT = "sport"
    FORMAL = "formal"
    TRAVEL = "travel"


@dataclass(frozen=True)
class ClothingItem:
    """Ein einzelnes Kleidungsstück im Kleiderschrank.

    warmth:    1 (sehr leicht) bis 5 (sehr warm)
    formality: 1 (sehr leger) bis 5 (sehr formell)
    """

    id: str
    name: str
    category: Category
    color: ColorFamily
    style: Style
    warmth: int = field(metadata={"range": (1, 5)})
    formality: int = field(metadata={"range": (1, 5)})


@dataclass
class OutfitContext:
    """Kontext, für den eine Empfehlung gesucht wird."""

    temperature: float  # in °C
    condition: WeatherCondition
    occasion: Occasion
    preferred_style: Style | None = None


@dataclass
class Outfit:
    """Eine Kombination aus genau einem Kleidungsstück pro Kategorie.

    Pflicht-Slots (z. B. Top, Bottom) sind immer enthalten, optionale
    Slots (z. B. Jacke, Schuhe) nur, wenn das Outfit sie nutzt.
    """

    items: dict[Category, ClothingItem] = field(default_factory=dict)


@dataclass
class ComponentScore:
    """Teil-Score einer einzelnen Scoring-Komponente mit Begründung."""

    component: str
    score: float  # 0..1
    weight: float  # vom Recommender gesetzt
    details: str = ""


@dataclass
class ScoredOutfit:
    """Outfit mit transparentem Gesamt-Score und Score-Aufschlüsselung."""

    outfit: Outfit
    total: float  # gewichtete Summe der Teil-Scores, 0..1
    components: list[ComponentScore]


@dataclass
class OutfitFeedback:
    """Explizites Nutzer-Feedback zu einem empfohlenen Outfit (1–5).

    Bewusst schlank gehalten – später z. B. um Zeitstempel, Kommentar
    oder persönliche Vorlieben erweiterbar, um daraus zu lernen, welche
    Outfits ein Nutzer mag.
    """

    outfit: Outfit
    rating: int  # 1..5
    context: OutfitContext | None = None
