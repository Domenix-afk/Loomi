"""Persistenz: einfache SQLite-Datenbank für den Kleiderschrank.

Bewusst simpel gehalten: eine Tabelle, keine Migrationen. Später leicht
um weitere Tabellen erweiterbar (z. B. Feedback, Empfehlungs-Historie).
"""

from __future__ import annotations

import sqlite3

from .models import Category, ClothingItem, ColorFamily, Style
from .wardrobe import Wardrobe


class WardrobeStore:
    """Speichert Kleidungsstücke dauerhaft in einer kleinen SQLite-DB."""

    def __init__(self, db_path: str = "loomi.db") -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clothing_items (
                        id        TEXT PRIMARY KEY,
                        name      TEXT NOT NULL,
                        category  TEXT NOT NULL,
                        color     TEXT NOT NULL,
                        style     TEXT NOT NULL,
                        warmth    INTEGER NOT NULL,
                        formality INTEGER NOT NULL
                    )
                    """
                )
        finally:
            conn.close()

    def save(self, item: ClothingItem) -> None:
        """Legt ein Kleidungsstück an oder aktualisiert es (Upsert)."""
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO clothing_items "
                    "(id, name, category, color, style, warmth, formality) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        item.id,
                        item.name,
                        item.category.value,
                        item.color.value,
                        item.style.value,
                        item.warmth,
                        item.formality,
                    ),
                )
        finally:
            conn.close()

    def delete(self, item_id: str) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute("DELETE FROM clothing_items WHERE id = ?", (item_id,))
        finally:
            conn.close()

    def count(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM clothing_items").fetchone()
            return int(row[0])
        finally:
            conn.close()

    def load(self) -> Wardrobe:
        """Lädt alle gespeicherten Kleidungsstücke in einen Wardrobe."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id, name, category, color, style, warmth, formality "
                "FROM clothing_items ORDER BY name"
            ).fetchall()
        finally:
            conn.close()

        wardrobe = Wardrobe()
        for row in rows:
            wardrobe.add(
                ClothingItem(
                    id=row["id"],
                    name=row["name"],
                    category=Category(row["category"]),
                    color=ColorFamily(row["color"]),
                    style=Style(row["style"]),
                    warmth=row["warmth"],
                    formality=row["formality"],
                )
            )
        return wardrobe
