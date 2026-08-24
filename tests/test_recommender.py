import pytest

from loomi.models import Occasion, OutfitContext, Style, WeatherCondition
from loomi.recommender import Recommender
from loomi.wardrobe import sample_wardrobe


def casual_ctx():
    return OutfitContext(24.0, WeatherCondition.SUNNY, Occasion.CASUAL, Style.CASUAL)


def test_recommendations_sorted_descending():
    recommender = Recommender()
    results = recommender.recommend(sample_wardrobe(), casual_ctx(), top_k=5)
    assert len(results) == 5
    totals = [entry.total for entry in results]
    assert totals == sorted(totals, reverse=True)


def test_total_is_weighted_sum_of_components():
    recommender = Recommender()
    ctx = OutfitContext(10.0, WeatherCondition.RAIN, Occasion.WORK, Style.SMART_CASUAL)
    scored = recommender.recommend(sample_wardrobe(), ctx, top_k=1)[0]
    expected = sum(comp.score * comp.weight for comp in scored.components)
    assert scored.total == pytest.approx(expected, abs=1e-4)
    names = {comp.component for comp in scored.components}
    assert names == {"style", "color", "occasion", "weather", "variety"}


def test_weights_are_configurable():
    recommender = Recommender(weights={"style": 1.0, "color": 0.0, "occasion": 0.0, "weather": 0.0, "variety": 0.0})
    scored = recommender.recommend(sample_wardrobe(), casual_ctx(), top_k=1)[0]
    style = next(comp for comp in scored.components if comp.component == "style")
    assert scored.total == pytest.approx(style.score, abs=1e-4)


def test_variety_lowers_score_for_repeated_outfit():
    recommender = Recommender()
    first = recommender.recommend(sample_wardrobe(), casual_ctx(), top_k=1)[0]
    again_fresh = recommender.score_outfit(first.outfit, casual_ctx())
    again_with_history = recommender.score_outfit(first.outfit, casual_ctx(), history=[first.outfit])
    assert again_with_history.total < again_fresh.total


def test_second_recommendation_differs():
    recommender = Recommender()
    first = recommender.recommend(sample_wardrobe(), casual_ctx(), top_k=1)[0]
    second = recommender.recommend(sample_wardrobe(), casual_ctx(), history=[first.outfit], top_k=1)[0]
    assert second.outfit != first.outfit
