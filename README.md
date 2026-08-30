# Loomi — Your Style. Perfected. 

**Personalized outfit recommendations—transparent and rule-based.**
Organize your closet, specify the weather and occasion, and Loomi will put together
the best outfits from your items—with a transparent score.

> Not a complex AI system, but a clean, extensible
> building block: feedback, preferences, and—later—machine learning build directly on top of it.

##  Quick Start

```bash
pip install -e .
python -m loomi.demo        # Example scenarios
python -m loomi.main        # Your own wardrobe (SQLite) + recommendations
python -m webapp.server     # Web app → http://127.0.0.1:8000
python -m pytest            # Tests
```

##  How It Works

Strictly separated modules, linked via `loomi/models.py`:

`OutfitGenerator` (generates all combinations) → **Scoring** (style, color,
occasion, weather, variety + “your taste”) → `Recommender`
(weighted sum, recommends the top 3) .

##  Personalization

Rate outfits with 1–5 stars—Loomi learns your preferences from this
(category, color, style, warmth, formality). The `PreferenceProfile` is
deterministic, is persisted in SQLite, and improves the ranking starting with the next
recommendation.

##  Deployment (Vercel)

Website: https://loomi-virid.vercel.app/

A lightweight WSGI adapter (`wsgi.py`) forwards all requests to `LoomiApp`—
the core and web app remain unchanged. Note: Vercel’s file system is
ephemeral; for persistent data, set `LOOMI_DB_PATH` to an external database.

Translated with DeepL.com (free version)