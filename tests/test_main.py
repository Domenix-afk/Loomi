import pytest

from loomi.main import ask_new_item, loomi_session, wardrobe_menu
from loomi.models import Category, ClothingItem, ColorFamily, Style
from loomi.storage import WardrobeStore


class FakeInput:
    """Gibt nacheinander vordefinierte Antworten zurück."""

    def __init__(self, answers):
        self._answers = list(answers)

    def __call__(self, prompt=""):
        if not self._answers:
            raise AssertionError(f"Keine weiteren Eingaben vorgesehen (Prompt: {prompt!r})")
        return self._answers.pop(0)


def make_item(
    item_id,
    name,
    category=Category.TOP,
    color=ColorFamily.NEUTRAL,
    style=Style.CASUAL,
    warmth=1,
    formality=1,
):
    return ClothingItem(item_id, name, category, color, style, warmth, formality)


# --- ask_new_item ---


def test_ask_new_item_returns_none_on_enter():
    assert ask_new_item(FakeInput([""])) is None


def test_ask_new_item_full_entry():
    fake = FakeInput(["Weißes T-Shirt", "1", "9", "1", "1", "1"])
    item = ask_new_item(fake)
    assert item is not None
    assert item.name == "Weißes T-Shirt"
    assert item.category is Category.TOP      # Index 1
    assert item.color is ColorFamily.NEUTRAL  # Index 9
    assert item.style is Style.CASUAL         # Index 1
    assert item.warmth == 1
    assert item.formality == 1
    assert item.id.startswith("weißes-t-shirt-")


# --- wardrobe_menu ---


def test_wardrobe_menu_adds_item(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["1", "T-Shirt", "1", "9", "1", "1", "1", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 1
    items = store.load().items
    assert len(items) == 1
    assert items[0].name == "T-Shirt"


def test_wardrobe_menu_deletes_by_number(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item("t1", "T-Shirt"))
    store.save(make_item("h1", "Hemd", color=ColorFamily.BLUE, style=Style.SMART_CASUAL))
    # Sortierung in der DB (nach Name): Hemd (1), T-Shirt (2)
    fake = FakeInput(["2", "2", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 1
    assert store.load().get("h1") is not None
    assert store.load().get("t1") is None


def test_wardrobe_menu_deletes_by_name(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item("t1", "Weißes T-Shirt"))
    fake = FakeInput(["2", "weißes t-shirt", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 0


def test_wardrobe_menu_retries_invalid_pick(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item("h1", "Hemd"))
    fake = FakeInput(["2", "99", "1", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 0


def test_wardrobe_menu_empty_delete_is_harmless(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["2", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 0


def test_wardrobe_menu_invalid_choice_is_harmless(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["abc", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 0


def test_wardrobe_menu_loads_sample_items(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["3", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 32


def test_wardrobe_menu_loads_sample_items_idempotent(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["3", "3", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 32  # zweites Laden fügt nichts hinzu


def test_wardrobe_menu_removes_sample_items(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["3", "4", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 0


def test_wardrobe_menu_removes_only_sample_items(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item("custom-1", "Eigener Pullover"))
    fake = FakeInput(["3", "4", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 1  # eigene Teile bleiben erhalten
    assert store.load().get("custom-1") is not None


def test_remove_sample_items_without_samples_is_harmless(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    fake = FakeInput(["4", ""])
    wardrobe_menu(store, ask=fake)
    assert store.count() == 0


# --- loomi_session ---


def test_loomi_session_empty_wardrobe_skips(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    loomi_session(store, ask=FakeInput(["n"]))


def test_loomi_session_loads_sample_and_recommends(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    # Beispieldaten laden, 24 °C sunny, Feedback 5, keine weitere Empfehlung
    loomi_session(store, ask=FakeInput(["j", "24", "1", "5", "n"]))


def test_loomi_session_uses_stored_items(tmp_path):
    store = WardrobeStore(str(tmp_path / "loomi.db"))
    store.save(make_item("t1", "T-Shirt"))
    store.save(make_item("b1", "Hose", category=Category.BOTTOM))
    # Wetter 20 °C sunny (Defaults), Feedback überspringen, keine weitere Empfehlung
    loomi_session(store, ask=FakeInput(["", "", "", "n"]))
