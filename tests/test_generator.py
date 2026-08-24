import pytest

from loomi.generator import OutfitGenerator
from loomi.models import Category, ClothingItem, ColorFamily, Style
from loomi.wardrobe import Wardrobe


def make_item(item_id, category, style=Style.CASUAL, color=ColorFamily.NEUTRAL, warmth=2, formality=2):
    return ClothingItem(item_id, item_id, category, color, style, warmth, formality)


def test_generates_valid_slots():
    wardrobe = Wardrobe([
        make_item("t1", Category.TOP),
        make_item("t2", Category.TOP),
        make_item("b1", Category.BOTTOM),
    ])
    outfits = OutfitGenerator().generate(wardrobe)
    assert len(outfits) == 2  # 2 Tops x 1 Bottom, ohne optionale Slots
    for outfit in outfits:
        assert set(outfit.items) == {Category.TOP, Category.BOTTOM}


def test_optional_categories_included():
    wardrobe = Wardrobe([
        make_item("t1", Category.TOP),
        make_item("b1", Category.BOTTOM),
        make_item("o1", Category.OUTERWEAR),
        make_item("s1", Category.SHOES),
        make_item("a1", Category.ACCESSORY),
    ])
    outfits = OutfitGenerator().generate(wardrobe)
    assert len(outfits) == 2 * 2 * 2  # je Kategorie an/aus
    slot_sets = {frozenset(outfit.items) for outfit in outfits}
    assert frozenset({Category.TOP, Category.BOTTOM}) in slot_sets
    assert frozenset({Category.TOP, Category.BOTTOM, Category.OUTERWEAR, Category.SHOES, Category.ACCESSORY}) in slot_sets


def test_missing_required_category_yields_empty():
    wardrobe = Wardrobe([make_item("t1", Category.TOP)])
    assert OutfitGenerator().generate(wardrobe) == []


def test_limit_caps_outfit_count():
    wardrobe = Wardrobe([
        make_item("t1", Category.TOP),
        make_item("t2", Category.TOP),
        make_item("b1", Category.BOTTOM),
        make_item("b2", Category.BOTTOM),
    ])
    generator = OutfitGenerator()
    assert len(generator.generate(wardrobe, limit=2)) == 2
    assert len(generator.generate(wardrobe)) == 4


def test_outfit_count_matches_generated():
    wardrobe = Wardrobe([
        make_item("t1", Category.TOP),
        make_item("t2", Category.TOP),
        make_item("b1", Category.BOTTOM),
        make_item("b2", Category.BOTTOM),
        make_item("o1", Category.OUTERWEAR),
    ])
    generator = OutfitGenerator()
    assert generator.outfit_count(wardrobe) == 2 * 2 * 2
    assert len(generator.generate(wardrobe)) == generator.outfit_count(wardrobe)
