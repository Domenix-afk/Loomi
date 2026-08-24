import pytest

from loomi.models import Category, ClothingItem, ColorFamily, Style
from loomi.wardrobe import Wardrobe, sample_wardrobe


def make_item(item_id="t1", category=Category.TOP):
    return ClothingItem(item_id, item_id, category, ColorFamily.NEUTRAL, Style.CASUAL, 2, 2)


def test_add_get_remove():
    wardrobe = Wardrobe()
    item = make_item()
    wardrobe.add(item)
    assert wardrobe.get("t1") is item
    wardrobe.remove("t1")
    assert wardrobe.get("t1") is None


def test_by_category_filters():
    wardrobe = Wardrobe([make_item("t1", Category.TOP), make_item("b1", Category.BOTTOM)])
    assert len(wardrobe.by_category(Category.TOP)) == 1
    assert len(wardrobe.by_category(Category.BOTTOM)) == 1


def test_rejects_out_of_range_values():
    wardrobe = Wardrobe()
    with pytest.raises(ValueError):
        wardrobe.add(ClothingItem("x", "x", Category.TOP, ColorFamily.NEUTRAL, Style.CASUAL, warmth=6, formality=2))
    with pytest.raises(ValueError):
        wardrobe.add(ClothingItem("y", "y", Category.TOP, ColorFamily.NEUTRAL, Style.CASUAL, warmth=2, formality=0))


def test_sample_wardrobe_covers_all_categories():
    wardrobe = sample_wardrobe()
    for category in Category:
        assert wardrobe.by_category(category), f"Kategorie {category.value} fehlt im Beispiel-Kleiderschrank"
