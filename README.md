# Loomi — Your Style. Perfected. ✨

**Persönliche Outfit-Empfehlungen – transparent & regelbasiert.**
Pflege deinen Kleiderschrank, gib Wetter & Anlass an, und Loomi stellt aus
deinen Teilen die besten Outfits zusammen – mit nachvollziehbarem Score.

> Kein komplexes AI-System, sondern ein sauberer, erweiterbarer
> Grundbaustein: Feedback, Vorlieben und später ML setzen direkt darauf auf.

## 🚀 Schnellstart

```bash
pip install -e .
python -m loomi.demo        # Beispiel-Szenarien
python -m loomi.main        # eigener Kleiderschrank (SQLite) + Empfehlung
python -m webapp.server     # Web-App → http://127.0.0.1:8000
python -m pytest            # Tests
```

## 🧠 Wie es funktioniert

Strikt getrennte Module, gekoppelt über `loomi/models.py`:

`OutfitGenerator` (bildet alle Kombinationen) → **Scoring** (Stil, Farbe,
Anlass, Wetter, Abwechslung + „Dein Geschmack“) → `Recommender`
(gewichtete Summe, empfiehlt die Top-3).

## ❤️ Personalisierung

Bewerte Outfits mit 1–5 Sternen – Loomi lernt daraus deine Vorlieben
(Kategorie, Farbe, Stil, Wärme, Formalität). Das `PreferenceProfile` ist
deterministisch, wird in SQLite persistiert und verbessert ab der nächsten
Empfehlung das Ranking.

## 🌐 Deployment (Vercel)

```bash
npm i -g vercel && vercel login && vercel --prod
```

Ein dünner WSGI-Adapter (`wsgi.py`) leitet alle Requests an `LoomiApp` weiter –
Kern und Web-App bleiben unverändert. Hinweis: Vercels Dateisystem ist
ephemer; für dauerhafte Daten `LOOMI_DB_PATH` auf eine externe DB umstellen.