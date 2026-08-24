# Loomi

Modularer Grundbaustein für Loomis **Personal-Style-Engine**: ein einfaches,
erweiterbares Outfit-Recommendation-System. Der Nutzer pflegt seinen
Kleiderschrank, gibt Kontext an (Wetter, Anlass, Wunsch-Style) und erhält
das beste Outfit – bewertet mit einem transparenten, regelbasierten Score.

> Ziel ist bewusst **kein** komplexes AI-System, sondern ein sauberer,
> funktionierender technischer Basisbaustein, auf dem später User-Feedback,
> persönliche Vorlieben, AI und Machine Learning aufsetzen können.

## Schnellstart

```bash
pip install -e .
python -m loomi.demo      # Demo mit Beispiel-Kleiderschrank
python -m pytest          # Tests ausführen
```

## Architektur

Die Module sind strikt getrennt und hängen nur über die Datenmodelle in
`loomi/models.py` zusammen:

| Modul | Verantwortung |
|---|---|
| `loomi/models.py` | Datenmodelle: `ClothingItem`, `OutfitContext`, `Outfit`, Score-Typen |
| `loomi/wardrobe.py` | Kleiderverwaltung (`Wardrobe`) + Beispiel-Kleiderschrank |
| `loomi/generator.py` | `OutfitGenerator` – bildet alle gültigen Kombinationen (Pflicht- + optionale Slots) |
| `loomi/scoring/` | Scoring-System – eine austauschbare Komponente pro Bewertungsdimension |
| `loomi/recommender.py` | `Recommender` – gewichtet die Teil-Scores und empfiehlt das Beste |
| `loomi/demo.py` | CLI-Demo |

## Nutzung

```python
from loomi import Recommender, OutfitContext, Occasion, Style, WeatherCondition
from loomi.wardrobe import sample_wardrobe

wardrobe = sample_wardrobe()
recommender = Recommender()

context = OutfitContext(
    temperature=24.0,
    condition=WeatherCondition.SUNNY,
    occasion=Occasion.CASUAL,
    preferred_style=Style.CASUAL,
)

top3 = recommender.recommend(wardrobe, context, top_k=3)
best = top3[0]
print(best.total)              # Gesamt-Score 0..1
for comp in best.components:   # transparente Aufschlüsselung
    print(comp.component, comp.score, comp.details)
```

Kleidungsstücke werden über `Wardrobe.add(ClothingItem(...))` gepflegt –
`warmth` und `formality` sind Skalen von 1 bis 5.

## Score-Berechnung

Der Gesamt-Score ist die **gewichtete Summe** der Teil-Scores (alle 0–1):

| Komponente | Gewicht | Bewertet |
|---|---|---|
| `style` | 0.25 | Stil-Kohärenz im Outfit + Match zum Wunsch-Style |
| `color` | 0.20 | Farbharmonie über einen Farbwheel (monochrom/analog/komplementär) |
| `occasion` | 0.25 | Durchschnittliche Formalität vs. Anlass + Konsistenz |
| `weather` | 0.20 | Wärmegrad vs. Temperatur + wettergerechte Jacke |
| `variety` | 0.10 | Vermeidet Wiederholungen kürzlich empfohlener Kleidungsstücke |

Jede Komponente liefert einen erklärbaren Teil-Score mit Begründung, sodass
jede Empfehlung nachvollziehbar ist. Gewichte und Komponenten sind frei
konfigurierbar (`Recommender(weights={...}, components=[...])`).

## Erweiterungspunkte (Roadmap)

- **Persönliche Vorlieben / User-Feedback**: neue `ScoreComponent` (z. B.
  `PreferenceFit`), die explizite Likes/Dislikes berücksichtigt; oder
  Feedback, um die Gewichte im `Recommender` zu lernen.
- **AI / Machine Learning**: eine ML-basierte Komponente kann eine
  regelbasierte ersetzen oder ergänzen – das `ScoreComponent`-Interface
  bleibt unverändert.
- **Abwechslung**: Historie kann um zeitliche Gewichtung („kürzlich“ statt
  „jemals“) erweitert werden.
- **Kontext**: z. B. Luftfeuchtigkeit, Wind, Nutzer-Mood oder
  Kleidungsstück-Attribute wie Material und Muster ergänzen.

## Projektstruktur

```
loomi/
├── models.py          # Datenmodelle (Enums, ClothingItem, Outfit, Scores)
├── wardrobe.py        # Wardrobe + Beispiel-Kleiderschrank
├── generator.py       # OutfitGenerator
├── scoring/           # StyleMatch, ColorHarmony, OccasionFit, WeatherFit, Variety
├── recommender.py     # Recommender (gewichteter Gesamt-Score)
└── demo.py            # CLI-Demo
tests/                 # pytest-Tests für alle Module
```
