"""Tests für die Personalisierung: PreferenceProfile und PersonalPreference."""

import pytest

from loomi.demo import run_interactive
from loomi.models import (
    Category,
    ClothingItem,
    ColorFamily,
    Occasion,
    Outfit,
    OutfitContext,
    OutfitFeedback,
    Style,
    WeatherCondition,
)
from loomi.preferences import PreferenceProfile
from loomi.recommender import Recommender
from loomi.scoring.preference import PersonalPreference
from loomi.wardrobe import Wardrobe, sample_wardrobe


def item(item_id, category, color=ColorFamily.BLUE, style=Style.CASUAL, warmth=3, formality=3):
    return ClothingItem(item_id, "Item", category, color, style, warmth, formality)


def outfit(top, bottom, **extra):
    items = {Category.TOP: top, Category.BOTTOM: bottom}
    for category, clothing in extra.items():
        items[Category(category)] = clothing
    return Outfit(items)


def ctx():
    return OutfitContext(20.0, WeatherCondition.SUNNY, Occasion.CASUAL, None)


class FakeInput:
    """Gibt nacheinander vordefinierte Antworten zurück."""

    def __init__(self, answers):
        self._answers = list(answers)

    def __call__(self, prompt=""):
        if not self._answers:
            raise AssertionError(f"Keine weiteren Eingaben vorgesehen (Prompt: {prompt!r})")
        return self._answers.pop(0)


# --- PreferenceProfile: Lernen ---


def test_profile_neutral_without_feedback():
    profile = PreferenceProfile()
    top = item("top", Category.TOP)
    bottom = item("bottom", Category.BOTTOM)
    assert profile.score_item(top) == 0.5
    assert profile.score_outfit(outfit(top, bottom)) == 0.5
    assert profile.feedback_count == 0


def test_positive_feedback_strengthens_similar_attributes():
    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    red = outfit(
        item("top", Category.TOP, color=ColorFamily.RED),
        item("bottom", Category.BOTTOM, color=ColorFamily.RED),
    )
    profile = PreferenceProfile()
    profile.update(OutfitFeedback(outfit=blue, rating=5))
    profile.update(OutfitFeedback(outfit=blue, rating=5))
    assert profile.score_outfit(blue) > profile.score_outfit(red)
    # Farbe blau ist gelernt (1.0), rot blieb neutral (0.5)
    assert profile.attribute_scores(blue)["color"] == pytest.approx(1.0)
    assert profile.attribute_scores(red)["color"] == pytest.approx(0.5)


def test_negative_feedback_weakens_below_neutral():
    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    profile = PreferenceProfile()
    profile.update(OutfitFeedback(outfit=blue, rating=1))
    assert profile.score_outfit(blue) < 0.5


def test_repeated_positive_feedback_stronger_than_single():
    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    single = PreferenceProfile()
    single.update(OutfitFeedback(outfit=blue, rating=5))
    single.update(OutfitFeedback(outfit=blue, rating=1))
    repeated = PreferenceProfile()
    repeated.update(OutfitFeedback(outfit=blue, rating=5))
    repeated.update(OutfitFeedback(outfit=blue, rating=5))
    repeated.update(OutfitFeedback(outfit=blue, rating=1))
    # Mehrfach gelobte Farbe hält einer späteren negativen Bewertung besser stand.
    assert repeated.score_outfit(blue) > single.score_outfit(blue)


def test_positive_then_negative_returns_color_to_neutral():
    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    profile = PreferenceProfile()
    profile.update(OutfitFeedback(outfit=blue, rating=5))
    assert profile.attribute_scores(blue)["color"] == pytest.approx(1.0)
    profile.update(OutfitFeedback(outfit=blue, rating=1))
    assert profile.attribute_scores(blue)["color"] == pytest.approx(0.5)


def test_warmth_preference_learned():
    warm = outfit(
        item("top", Category.TOP, warmth=5),
        item("bottom", Category.BOTTOM, warmth=5),
    )
    profile = PreferenceProfile()
    profile.update(OutfitFeedback(outfit=warm, rating=5))
    assert profile.score_item(item("t1", Category.TOP, warmth=5)) > profile.score_item(
        item("t2", Category.TOP, warmth=1)
    )


# --- PersonalPreference-Komponente ---


def test_personal_preference_neutral_without_data():
    comp = PersonalPreference(PreferenceProfile())
    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    result = comp.score(blue, ctx())
    assert result.score == 0.5
    assert "neutral" in result.details


def test_personal_preference_reflects_profile():
    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    red = outfit(
        item("top", Category.TOP, color=ColorFamily.RED),
        item("bottom", Category.BOTTOM, color=ColorFamily.RED),
    )
    profile = PreferenceProfile()
    profile.update(OutfitFeedback(outfit=blue, rating=5))
    comp = PersonalPreference(profile)
    liked = comp.score(blue, ctx())
    other = comp.score(red, ctx())
    assert liked.component == "preference"
    assert liked.score > other.score
    assert "Farbe" in liked.details  # transparente Begründung


# --- Recommender-Integration ---


def test_recommender_with_profile_adds_preference_component():
    profile = PreferenceProfile()
    rec = Recommender(preference_profile=profile)
    assert "preference" in {c.name for c in rec.components}
    assert rec.weights["preference"] == pytest.approx(0.15)
    assert rec.preference_profile is profile


def test_default_recommender_unchanged():
    rec = Recommender()
    assert {c.name for c in rec.components} == {"style", "color", "occasion", "weather", "variety"}
    assert rec.weights == {
        "style": 0.25,
        "color": 0.20,
        "occasion": 0.25,
        "weather": 0.20,
        "variety": 0.10,
    }
    assert rec.preference_profile is None


def test_total_is_weighted_sum_with_preference():
    profile = PreferenceProfile()
    rec = Recommender(preference_profile=profile)
    scored = rec.recommend(sample_wardrobe(), ctx(), top_k=1)[0]
    expected = sum(comp.score * comp.weight for comp in scored.components)
    assert scored.total == pytest.approx(expected, abs=1e-4)
    assert "preference" in {comp.component for comp in scored.components}


# --- Ranking ändert sich durch Feedback ---


def test_positive_feedback_promotes_liked_outfit():
    top_casual = item("top-casual", Category.TOP)
    top_sporty = item("top-sporty", Category.TOP, style=Style.SPORTY)
    bottom_casual = item("bottom-casual", Category.BOTTOM)
    bottom_sporty = item("bottom-sporty", Category.BOTTOM, style=Style.SPORTY)
    wardrobe = Wardrobe([top_casual, top_sporty, bottom_casual, bottom_sporty])

    profile = PreferenceProfile()
    rec = Recommender(preference_profile=profile, weights={"preference": 1.0})

    target = outfit(top_sporty, bottom_sporty)
    for _ in range(3):
        profile.update(OutfitFeedback(outfit=target, rating=5))

    winner = rec.recommend(wardrobe, ctx(), top_k=1)[0]
    assert winner.outfit == target
    assert winner.total > 0.95  # Präferenz dominiert eindeutig


def test_negative_feedback_demotes_former_winner():
    top_blue = item("top-blue", Category.TOP)
    top_red = item("top-red", Category.TOP, color=ColorFamily.RED)
    bottom_blue = item("bottom-blue", Category.BOTTOM)
    bottom_red = item("bottom-red", Category.BOTTOM, color=ColorFamily.RED)
    wardrobe = Wardrobe([top_blue, top_red, bottom_blue, bottom_red])

    profile = PreferenceProfile()
    rec = Recommender(preference_profile=profile)

    winner = rec.recommend(wardrobe, ctx(), top_k=1)[0]
    for _ in range(3):
        profile.update(OutfitFeedback(outfit=winner.outfit, rating=1))

    new_winner = rec.recommend(wardrobe, ctx(), top_k=1)[0]
    demoted = rec.score_outfit(winner.outfit, ctx())  # alter Gewinner nach Feedback
    assert new_winner.outfit != winner.outfit
    assert new_winner.total > demoted.total


def test_run_interactive_feeds_feedback_into_profile():
    wardrobe = Wardrobe([item("top", Category.TOP), item("bottom", Category.BOTTOM)])
    profile = PreferenceProfile()
    rec = Recommender(preference_profile=profile)
    # Runde 1: 20 °C sunny, Feedback 5. Runde 2: gleiches Wetter, Feedback 3, dann Ende.
    fake = FakeInput(["20", "1", "5", "j", "20", "1", "3", "n"])
    run_interactive(rec, wardrobe, ask=fake, profile=profile)
    assert profile.feedback_count == 2
    single = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    assert profile.score_outfit(single) > 0.5  # Lob hat das Profil geprägt


def test_profile_dict_roundtrip_via_json():
    import json

    blue = outfit(item("top", Category.TOP), item("bottom", Category.BOTTOM))
    profile = PreferenceProfile()
    profile.update(OutfitFeedback(outfit=blue, rating=5))
    profile.update(OutfitFeedback(outfit=blue, rating=2))

    # Wie im PreferenceStore: dict -> JSON -> dict -> Profil
    data = json.loads(json.dumps(profile.to_dict()))
    restored = PreferenceProfile.from_dict(data)
    assert restored.feedback_count == profile.feedback_count
    assert restored.to_dict() == profile.to_dict()
    assert restored.score_outfit(blue) == profile.score_outfit(blue)
    other = item("x", Category.TOP, color=ColorFamily.RED)
    assert restored.score_item(other) == profile.score_item(other)
