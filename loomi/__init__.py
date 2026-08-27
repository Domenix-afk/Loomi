"""Loomi – modularer Grundbaustein für eine Personal-Style-Engine.

Öffentliche API: Kleiderschrank, Outfit-Generator, Scoring-Komponenten
und Recommender. Die Module sind bewusst getrennt, damit später
User-Feedback, persönliche Vorlieben, AI und ML ergänzt werden können.
"""

from .generator import OutfitGenerator
from .models import (
    Category,
    ClothingItem,
    ColorFamily,
    ComponentScore,
    Occasion,
    Outfit,
    OutfitContext,
    OutfitFeedback,
    ScoredOutfit,
    Style,
    WeatherCondition,
)
from .recommender import Recommender
from .scoring.base import ScoreComponent
from .scoring.color import ColorHarmony
from .scoring.occasion import OccasionFit
from .scoring.style import StyleMatch
from .scoring.variety import Variety
from .scoring.weather import WeatherFit
from .wardrobe import Wardrobe, sample_wardrobe

__all__ = [
    "Category",
    "ClothingItem",
    "ColorFamily",
    "ComponentScore",
    "Occasion",
    "Outfit",
    "OutfitContext",
    "OutfitFeedback",
    "ScoredOutfit",
    "Style",
    "WeatherCondition",
    "OutfitGenerator",
    "Wardrobe",
    "sample_wardrobe",
    "ScoreComponent",
    "StyleMatch",
    "ColorHarmony",
    "OccasionFit",
    "WeatherFit",
    "Variety",
    "Recommender",
]
