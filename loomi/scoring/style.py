"""Style-Match: Passt das Outfit stilistisch zusammen und zum Wunsch-Style?"""

from __future__ import annotations

from ..models import ComponentScore, Outfit, OutfitContext, Style
from .base import ScoreComponent

# Kompatibilität zwischen Stilen (0 = passt gar nicht, 1 = passt perfekt).
_COMPATIBILITY: dict[Style, dict[Style, float]] = {
    Style.CASUAL: {
        Style.CASUAL: 1.0,
        Style.SMART_CASUAL: 0.65,
        Style.SPORTY: 0.8,
        Style.ELEGANT: 0.2,
        Style.STREETWEAR: 0.6,
        Style.BUSINESS: 0.15,
        Style.BOHO: 0.5,
    },
    Style.SMART_CASUAL: {
        Style.CASUAL: 0.65,
        Style.SMART_CASUAL: 1.0,
        Style.SPORTY: 0.4,
        Style.ELEGANT: 0.7,
        Style.STREETWEAR: 0.4,
        Style.BUSINESS: 0.6,
        Style.BOHO: 0.5,
    },
    Style.SPORTY: {
        Style.CASUAL: 0.8,
        Style.SMART_CASUAL: 0.4,
        Style.SPORTY: 1.0,
        Style.ELEGANT: 0.1,
        Style.STREETWEAR: 0.6,
        Style.BUSINESS: 0.1,
        Style.BOHO: 0.3,
    },
    Style.ELEGANT: {
        Style.CASUAL: 0.2,
        Style.SMART_CASUAL: 0.7,
        Style.SPORTY: 0.1,
        Style.ELEGANT: 1.0,
        Style.STREETWEAR: 0.15,
        Style.BUSINESS: 0.6,
        Style.BOHO: 0.4,
    },
    Style.STREETWEAR: {
        Style.CASUAL: 0.6,
        Style.SMART_CASUAL: 0.4,
        Style.SPORTY: 0.6,
        Style.ELEGANT: 0.15,
        Style.STREETWEAR: 1.0,
        Style.BUSINESS: 0.1,
        Style.BOHO: 0.3,
    },
    Style.BUSINESS: {
        Style.CASUAL: 0.15,
        Style.SMART_CASUAL: 0.6,
        Style.SPORTY: 0.1,
        Style.ELEGANT: 0.6,
        Style.STREETWEAR: 0.1,
        Style.BUSINESS: 1.0,
        Style.BOHO: 0.15,
    },
    Style.BOHO: {
        Style.CASUAL: 0.5,
        Style.SMART_CASUAL: 0.5,
        Style.SPORTY: 0.3,
        Style.ELEGANT: 0.4,
        Style.STREETWEAR: 0.3,
        Style.BUSINESS: 0.15,
        Style.BOHO: 1.0,
    },
}


def _make_symmetric() -> dict[Style, dict[Style, float]]:
    table = {style: dict(row) for style, row in _COMPATIBILITY.items()}
    for a, row in _COMPATIBILITY.items():
        for b, value in row.items():
            table[b][a] = value
    return table


class StyleMatch(ScoreComponent):
    """Bewertet Stil-Kohärenz im Outfit und den Match zum Wunsch-Style."""

    name = "style"

    def __init__(self) -> None:
        self._compat = _make_symmetric()

    def score(
        self,
        outfit: Outfit,
        context: OutfitContext,
        history: list[Outfit] | None = None,
    ) -> ComponentScore:
        styles = [item.style for item in outfit.items.values()]

        if len(styles) <= 1:
            coherence = 1.0
        else:
            pairs = [
                (a, b)
                for i, a in enumerate(styles)
                for b in styles[i + 1 :]
            ]
            coherence = sum(self._compat[a][b] for a, b in pairs) / len(pairs)

        # Dominanter Stil = Stil mit der höchsten durchschnittlichen
        # Kompatibilität zu allen Stilen im Outfit.
        dominant = max(styles, key=lambda s: sum(self._compat[s][t] for t in styles) / len(styles))

        details = f"Kohärenz {coherence:.2f}, dominanter Stil '{dominant.value}'"
        if context.preferred_style is not None:
            context_match = self._compat[dominant][context.preferred_style]
            details += (
                f", Wunsch-Style '{context.preferred_style.value}' -> {context_match:.2f}"
            )
            final = 0.5 * coherence + 0.5 * context_match
        else:
            final = coherence

        return ComponentScore(self.name, round(final, 4), 1.0, details)
