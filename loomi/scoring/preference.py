"""Persönliche Präferenz: bewertet Outfits anhand des gelernten PreferenceProfile.

Die Komponente ersetzt keine bestehende Regel, sondern ergänzt sie:
Sie nutzt das aus bisherigem Feedback (1–5) gelernte Profil und fließt
als weitere Komponente in den gewichteten Gesamt-Score ein. Ohne
Feedback liefert sie für jedes Outfit exakt 0.5 (neutral) und verändert
die Reihenfolge nicht.
"""

from __future__ import annotations

from ..models import ComponentScore, Outfit, OutfitContext
from ..preferences import PreferenceProfile
from .base import ScoreComponent


class PersonalPreference(ScoreComponent):
    """Bewertet, wie gut ein Outfit zu den gelernten Vorlieben passt."""

    name = "preference"

    def __init__(self, profile: PreferenceProfile) -> None:
        self.profile = profile

    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        score = self.profile.score_outfit(outfit)
        details = self.profile.describe(outfit)
        return ComponentScore(self.name, score, 1.0, details)
