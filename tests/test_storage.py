import pytest

from loomi.models import Category, ClothingItem, ColorFamily, Style
from loomi.storage import WardrobeStore


def make_item(item_id="t1"):
    return ClothingItem(
        item_id, "Weißes T-Shirt", Category.TOP, ColorFamily.NEUTRAL, Style.CASUAL, 1, 1
    )


def test_save_and_load_roundtrip(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item())

    wardrobe = store.load()
    assert len(wardrobe) == 1
    item = wardrobe.get("t1")
    assert item is not None
    assert item.name == "Weißes T-Shirt"
    assert item.category is Category.TOP
    assert item.color is ColorFamily.NEUTRAL
    assert item.style is Style.CASUAL
    assert item.warmth == 1
    assert item.formality == 1


def test_delete_removes_item(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item())
    store.delete("t1")
    assert store.count() == 0
    assert len(store.load()) == 0


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "loomi.db")
    WardrobeStore(path).save(make_item("a"))
    WardrobeStore(path).save(make_item("b"))

    store = WardrobeStore(path)
    assert store.count() == 2
    assert {item.id for item in store.load().items} == {"a", "b"}


def test_save_overwrites_existing_item(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item("t1"))
    store.save(ClothingItem("t1", "Neuer Name", Category.TOP, ColorFamily.RED, Style.CASUAL, 2, 2))
    item = store.load().get("t1")
    assert item is not None
    assert item.name == "Neuer Name"
    assert store.count() == 1


def test_empty_db_loads_empty_wardrobe(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    assert len(store.load()) == 0
    assert store.count() == 0
