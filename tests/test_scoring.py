import pytest

from loomi.models import (
    Category,
    ClothingItem,
    ColorFamily,
    Occasion,
    Outfit,
    OutfitContext,
    Style,
    WeatherCondition,
)
from loomi.scoring.color import ColorHarmony
from loomi.scoring.occasion import OccasionFit
from loomi.scoring.style import StyleMatch
from loomi.scoring.variety import Variety
from loomi.scoring.weather import WeatherFit


def item(category, item_id=None, style=Style.CASUAL, color=ColorFamily.NEUTRAL, warmth=2, formality=2):
    return ClothingItem(
        item_id or f"i-{category.value}-{style.value}",
        "Item",
        category,
        color,
        style,
        warmth,
        formality,
    )


def outfit(top, bottom, **extra):
    items = {Category.TOP: top, Category.BOTTOM: bottom}
    for category, clothing in extra.items():
        items[Category(category)] = clothing
    return Outfit(items)


def ctx(occasion=Occasion.CASUAL, temperature=20.0, condition=WeatherCondition.SUNNY, preferred_style=None):
    return OutfitContext(temperature, condition, occasion, preferred_style)


# --- StyleMatch ---


def test_style_matching_styles_score_high():
    top = item(Category.TOP, style=Style.SPORTY)
    bottom = item(Category.BOTTOM, style=Style.SPORTY)
    result = StyleMatch().score(outfit(top, bottom), ctx())
    assert result.score == pytest.approx(1.0, abs=1e-3)


def test_style_clashing_styles_score_low():
    top = item(Category.TOP, style=Style.BUSINESS)
    bottom = item(Category.BOTTOM, style=Style.SPORTY)
    result = StyleMatch().score(outfit(top, bottom), ctx())
    assert result.score < 0.5


def test_style_context_match_mixes_coherence():
    top = item(Category.TOP, style=Style.ELEGANT)
    bottom = item(Category.BOTTOM, style=Style.ELEGANT)
    result = StyleMatch().score(
        outfit(top, bottom),
        ctx(preferred_style=Style.SMART_CASUAL),
    )
    # Kohärenz 1.0, elegant<->smart_casual 0.7 -> 0.85
    assert result.score == pytest.approx(0.85, abs=1e-3)


# --- ColorHarmony ---


def test_neutral_pair_is_perfect():
    top = item(Category.TOP, color=ColorFamily.NEUTRAL)
    bottom = item(Category.BOTTOM, color=ColorFamily.NEUTRAL)
    assert ColorHarmony().score(outfit(top, bottom), ctx()).score == 1.0


def test_monochrome_better_than_clashing():
    harmony = ColorHarmony()
    blue_top = item(Category.TOP, color=ColorFamily.BLUE)
    blue_bottom = item(Category.BOTTOM, color=ColorFamily.BLUE)
    red_top = item(Category.TOP, color=ColorFamily.RED)
    green_bottom = item(Category.BOTTOM, color=ColorFamily.GREEN)
    mono = harmony.score(outfit(blue_top, blue_bottom), ctx()).score
    clash = harmony.score(outfit(red_top, green_bottom), ctx()).score
    assert clash < mono


def test_many_colorful_items_penalized():
    harmony = ColorHarmony()
    red = item(Category.TOP, color=ColorFamily.RED)
    green = item(Category.BOTTOM, color=ColorFamily.GREEN)
    yellow = item(Category.OUTERWEAR, color=ColorFamily.YELLOW)
    two_colors = harmony.score(outfit(red, green), ctx()).score
    three_colors = harmony.score(outfit(red, green, outerwear=yellow), ctx()).score
    assert three_colors < two_colors


# --- OccasionFit ---


def test_formal_outfit_fits_formal_occasion():
    top = item(Category.TOP, formality=4)
    bottom = item(Category.BOTTOM, formality=5)
    result = OccasionFit().score(outfit(top, bottom), ctx(occasion=Occasion.FORMAL))
    assert result.score > 0.95


def test_casual_outfit_fails_formal_occasion():
    top = item(Category.TOP, formality=1)
    bottom = item(Category.BOTTOM, formality=1)
    result = OccasionFit().score(outfit(top, bottom), ctx(occasion=Occasion.FORMAL))
    assert result.score < 0.5


def test_mixed_formality_penalized():
    top = item(Category.TOP, formality=4)
    bottom = item(Category.BOTTOM, formality=1)
    result = OccasionFit().score(outfit(top, bottom), ctx(occasion=Occasion.WORK))
    assert result.score < 0.9  # Streuung zieht ab


# --- WeatherFit ---


def test_light_outfit_better_in_heat():
    weather = WeatherFit()
    light = outfit(item(Category.TOP, warmth=1), item(Category.BOTTOM, warmth=1))
    heavy = outfit(item(Category.TOP, warmth=5), item(Category.BOTTOM, warmth=5))
    hot = ctx(temperature=30.0)
    assert weather.score(light, hot).score > weather.score(heavy, hot).score


def test_heavy_outfit_better_in_cold():
    weather = WeatherFit()
    light = outfit(item(Category.TOP, warmth=1), item(Category.BOTTOM, warmth=1))
    heavy = outfit(item(Category.TOP, warmth=5), item(Category.BOTTOM, warmth=5))
    cold = ctx(temperature=0.0, condition=WeatherCondition.SNOW)
    assert weather.score(heavy, cold).score > weather.score(light, cold).score


def test_rain_penalizes_missing_outerwear():
    weather = WeatherFit()
    base = outfit(item(Category.TOP, warmth=3), item(Category.BOTTOM, warmth=3))
    with_outer = outfit(
        item(Category.TOP, warmth=3),
        item(Category.BOTTOM, warmth=3),
        outerwear=item(Category.OUTERWEAR, warmth=3),
    )
    rainy = ctx(temperature=10.0, condition=WeatherCondition.RAIN)
    assert weather.score(with_outer, rainy).score > weather.score(base, rainy).score


# --- Variety ---


def test_no_history_means_full_variety():
    top = item(Category.TOP, item_id="t1")
    bottom = item(Category.BOTTOM, item_id="b1")
    result = Variety().score(outfit(top, bottom), ctx())
    assert result.score == 1.0


def test_full_overlap_zero_variety():
    top = item(Category.TOP, item_id="t1")
    bottom = item(Category.BOTTOM, item_id="b1")
    the_outfit = outfit(top, bottom)
    result = Variety().score(the_outfit, ctx(), history=[the_outfit])
    assert result.score == 0.0


def test_partial_overlap_scores_in_between():
    t1 = item(Category.TOP, item_id="t1")
    t2 = item(Category.TOP, item_id="t2")
    b1 = item(Category.BOTTOM, item_id="b1")
    first = outfit(t1, b1)
    second = outfit(t2, b1)
    result = Variety().score(second, ctx(), history=[first])
    assert result.score == pytest.approx(0.5)  # 1 von 2 Kleidungsstücken geteilt
