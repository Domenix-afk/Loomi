"""Kleiderschrank: Verwaltung der Kleidungsstücke eines Nutzers."""

from __future__ import annotations

from .models import Category, ClothingItem, ColorFamily, Style


class Wardrobe:
    """Verwaltet die Kleidungsstücke eines Nutzers.

    Bewusst dünn gehalten – später z. B. um Nutzer-Feedback,
    persönliche Vorlieben oder Quellen (Kauf, manuell) erweiterbar.
    """

    def __init__(self, items: list[ClothingItem] | None = None) -> None:
        self._items: dict[str, ClothingItem] = {}
        if items:
            for item in items:
                self.add(item)

    def add(self, item: ClothingItem) -> None:
        if not 1 <= item.warmth <= 5 or not 1 <= item.formality <= 5:
            raise ValueError(
                f"{item.id}: warmth und formality müssen zwischen 1 und 5 liegen"
            )
        self._items[item.id] = item

    def remove(self, item_id: str) -> None:
        self._items.pop(item_id, None)

    def get(self, item_id: str) -> ClothingItem | None:
        return self._items.get(item_id)

    @property
    def items(self) -> list[ClothingItem]:
        return list(self._items.values())

    def by_category(self, category: Category) -> list[ClothingItem]:
        return [item for item in self._items.values() if item.category is category]

    def __len__(self) -> int:
        return len(self._items)


def sample_wardrobe() -> Wardrobe:
    """Beispiel-Kleiderschrank für Demo und Tests."""
    items = [
        # Tops
        ClothingItem("t-shirt-white", "Weißes T-Shirt", Category.TOP, ColorFamily.NEUTRAL, Style.CASUAL, 1, 1),
        ClothingItem("shirt-blue", "Dunkelblaues Hemd", Category.TOP, ColorFamily.BLUE, Style.SMART_CASUAL, 2, 3),
        ClothingItem("shirt-white", "Weißes Hemd", Category.TOP, ColorFamily.NEUTRAL, Style.BUSINESS, 2, 4),
        ClothingItem("sweater-beige", "Kaschmir-Pullover", Category.TOP, ColorFamily.NEUTRAL, Style.ELEGANT, 4, 3),
        ClothingItem("hoodie-blue", "Blauer Hoodie", Category.TOP, ColorFamily.BLUE, Style.STREETWEAR, 3, 1),
        ClothingItem("polo-red", "Rotes Polo-Shirt", Category.TOP, ColorFamily.RED, Style.CASUAL, 2, 2),
        ClothingItem("blouse-pink", "Seidenbluse", Category.TOP, ColorFamily.PINK, Style.ELEGANT, 2, 4),
        ClothingItem("tee-sport", "Sport-T-Shirt", Category.TOP, ColorFamily.GREEN, Style.SPORTY, 1, 1),
        # Bottoms
        ClothingItem("jeans-blue", "Blue Jeans", Category.BOTTOM, ColorFamily.BLUE, Style.CASUAL, 2, 1),
        ClothingItem("chino-black", "Schwarze Chino", Category.BOTTOM, ColorFamily.NEUTRAL, Style.SMART_CASUAL, 2, 3),
        ClothingItem("trousers-suit", "Anzugshose", Category.BOTTOM, ColorFamily.NEUTRAL, Style.BUSINESS, 2, 5),
        ClothingItem("jogger-gray", "Jogginghose", Category.BOTTOM, ColorFamily.NEUTRAL, Style.SPORTY, 2, 1),
        ClothingItem("cargo-green", "Cargohose", Category.BOTTOM, ColorFamily.GREEN, Style.STREETWEAR, 2, 2),
        ClothingItem("skirt-leather", "Lederrock", Category.BOTTOM, ColorFamily.NEUTRAL, Style.ELEGANT, 1, 4),
        ClothingItem("pants-brown", "Braune Stoffhose", Category.BOTTOM, ColorFamily.BROWN, Style.BOHO, 3, 2),
        # Outerwear
        ClothingItem("jacket-denim", "Denim-Jacke", Category.OUTERWEAR, ColorFamily.BLUE, Style.CASUAL, 3, 2),
        ClothingItem("jacket-leather", "Schwarze Lederjacke", Category.OUTERWEAR, ColorFamily.NEUTRAL, Style.STREETWEAR, 3, 3),
        ClothingItem("coat-wool", "Grauer Wollmantel", Category.OUTERWEAR, ColorFamily.NEUTRAL, Style.ELEGANT, 5, 4),
        ClothingItem("blazer-white", "Weißer Blazer", Category.OUTERWEAR, ColorFamily.NEUTRAL, Style.BUSINESS, 3, 5),
        ClothingItem("jacket-sport", "Windjacke", Category.OUTERWEAR, ColorFamily.GREEN, Style.SPORTY, 2, 1),
        ClothingItem("cardigan-brown", "Strickjacke", Category.OUTERWEAR, ColorFamily.BROWN, Style.BOHO, 4, 2),
        # Schuhe
        ClothingItem("sneakers-white", "Weiße Sneaker", Category.SHOES, ColorFamily.NEUTRAL, Style.CASUAL, 1, 1),
        ClothingItem("derby-brown", "Braune Derby-Schuhe", Category.SHOES, ColorFamily.BROWN, Style.ELEGANT, 2, 4),
        ClothingItem("oxford-black", "Schwarze Oxford-Schuhe", Category.SHOES, ColorFamily.NEUTRAL, Style.BUSINESS, 2, 5),
        ClothingItem("runners", "Laufschuhe", Category.SHOES, ColorFamily.NEUTRAL, Style.SPORTY, 1, 1),
        ClothingItem("boots-black", "Schwarze Stiefel", Category.SHOES, ColorFamily.NEUTRAL, Style.STREETWEAR, 4, 3),
        ClothingItem("ballet-flats", "Ballerinas", Category.SHOES, ColorFamily.NEUTRAL, Style.ELEGANT, 1, 3),
        # Accessoires
        ClothingItem("scarf-wool", "Wollschal", Category.ACCESSORY, ColorFamily.NEUTRAL, Style.CASUAL, 4, 2),
        ClothingItem("scarf-silk", "Seidenschal", Category.ACCESSORY, ColorFamily.PURPLE, Style.ELEGANT, 1, 4),
        ClothingItem("cap-red", "Baseballcap", Category.ACCESSORY, ColorFamily.RED, Style.STREETWEAR, 1, 1),
        ClothingItem("gloves-brown", "Lederhandschuhe", Category.ACCESSORY, ColorFamily.BROWN, Style.BUSINESS, 3, 3),
        ClothingItem("necklace-gold", "Goldkette", Category.ACCESSORY, ColorFamily.YELLOW, Style.BOHO, 1, 2),
    ]
    return Wardrobe(items)
