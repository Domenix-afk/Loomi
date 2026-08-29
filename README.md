# Loomi — Your Style. Perfected.

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
python -m loomi.demo       # Beispiel-Szenarien anzeigen
python -m loomi.demo -i    # eigenes Wetter & Kontext interaktiv eingeben
python -m loomi.main       # Hauptprogramm: eigener Kleiderschrank (SQLite)
python -m webapp.server    # Web-App im Browser (http://127.0.0.1:8000)
python -m pytest           # Tests ausführen
```

### Web-App (`webapp/`)

`python -m webapp.server` startet eine schlanke Web-UI **auf Basis des
existierenden Loomi-Kerns** – ohne neue Features und ohne den Kern zu
verändern. Ein stdlib-HTTP-Server (keine weiteren Abhängigkeiten) bedient
eine JSON-API, über die das Frontend (HTML/CSS/JS, kein Build-Schritt)
mit den vorhandenen Loomi-Funktionen arbeitet:

- **Empfehlung**: Wetter (Temperatur + Wetterlage), Anlass und optionaler
  Wunsch-Style → Top-3-Outfits mit transparentem Score und Komponenten-
  Aufschlüsselung. Jede Karte lässt sich mit 1–5 Sternen bewerten.
- **Kleiderschrank**: Kleidungsstücke anlegen/löschen, Beispieldaten laden
  und entfernen – alles direkt in der SQLite-Datenbank.
- **Profil**: zeigt die gelernten Vorlieben (aus dem `PreferenceProfile`)
  und kann das Profil zurücksetzen.

Alle Buttons und Flows sind mit echten API-Endpunkten verdrahtet – es gibt
keine Platzhalter. Optionen:

```bash
python -m webapp.server --port 8080   # anderer Port
python -m webapp.server --db pfad.db  # andere Datenbank
python -m webapp.server --open        # Browser automatisch öffnen
```

### Hauptprogramm (`loomi.main`)

`python -m loomi.main` startet mit einem Menü und fragt, was du tun möchtest:

1. **Kleiderschrank (Wardrobe)** – Kleidung verwalten:
   - **Hinzufügen**: alle wichtigen Fragen (Name, Kategorie, Farbe, Stil,
     Wärme, Formalität) – das Teil wird in der kleinen **SQLite-Datenbank**
     (`loomi.db`, änderbar mit `--db`) gespeichert
   - **Löschen**: Kleidungsstück per Nummer oder Name auswählen und entfernen
   - **Beispieldaten laden**: die 32 Beispiel-Kleidungsstücke in die Datenbank
     übernehmen (idempotent)
   - **Beispieldaten entfernen**: per Befehl wieder aus der Datenbank löschen
2. **Loomi** – Outfit-Empfehlung: Wetter eingeben → Empfehlung + Feedback
   (identisch zur Demo, ohne Kleidungsverwaltung)

Ist die Datenbank leer, kannst du beim Empfehlen den Beispiel-Kleiderschrank
laden. Nach jeder Runde kehrst du zum Start-Menü zurück.

Im interaktiven Modus (`-i`) fragt Loomi nur das aktuelle Wetter ab:
Temperatur (auch mit deutschem Komma, z. B. `24,5`) und Wetterlage –
per Index (z. B. `2`), Wert (z. B. `rain`) oder Enter für den Vorschlag.
Anlass und Wunsch-Style sind dabei auf sensible Standardwerte gesetzt
(casual / keiner). Nach der Empfehlung kannst du das beste Outfit mit
1–5 bewerten (Enter = überspringen) – das Feedback wird als
`OutfitFeedback` erfasst und ist die Grundlage für spätere
Personalisierung.

## Architektur

Die Module sind strikt getrennt und hängen nur über die Datenmodelle in
`loomi/models.py` zusammen:

| Modul | Verantwortung |
|---|---|
| `loomi/models.py` | Datenmodelle: `ClothingItem`, `OutfitContext`, `Outfit`, Score-Typen |
| `loomi/wardrobe.py` | Kleiderverwaltung (`Wardrobe`) + Beispiel-Kleiderschrank |
| `loomi/generator.py` | `OutfitGenerator` – bildet alle gültigen Kombinationen (Pflicht- + optionale Slots) |
| `loomi/preferences.py` | `PreferenceProfile` – lernt aus Feedback (1–5) Vorlieben über Kleidungsattribute |
| `loomi/scoring/` | Scoring-System – eine austauschbare Komponente pro Bewertungsdimension |
| `loomi/recommender.py` | `Recommender` – gewichtet die Teil-Scores und empfiehlt das Beste |
| `loomi/storage.py` | `WardrobeStore` + `PreferenceStore` – einfache SQLite-Persistenz für Kleiderschrank und Präferenzprofil |
| `loomi/demo.py` | CLI-Demo (Beispiel-Szenarien + interaktive Wetter-Eingabe) |
| `loomi/main.py` | Hauptprogramm: eigener Kleiderschrank, Empfehlung, Feedback, Löschen |
| `webapp/` | Web-UI über dem Kern: `app.py` (API-Schicht), `server.py` (HTTP), `static/` (Frontend) |

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
| `preference` | 0.15* | Persönliche Vorlieben aus bisherigem Feedback (nur mit `PreferenceProfile`) |

*Die Präferenz-Komponente ist nur aktiv, wenn der `Recommender` ein
`PreferenceProfile` erhält – ohne Feedback liefert sie für jedes Outfit
exakt 0.5 (neutral) und verändert die Reihenfolge nicht.

Jede Komponente liefert einen erklärbaren Teil-Score mit Begründung, sodass
jede Empfehlung nachvollziehbar ist. Gewichte und Komponenten sind frei
konfigurierbar (`Recommender(weights={...}, components=[...])`).

## Personalisierung: So lernt Loomi Vorlieben

Jede Bewertung (1–5) nach einer Empfehlung speist sich in ein
**`PreferenceProfile`** ein – ein bewusst einfaches, deterministisches
Modell (kein ML). Aus den Attributen der bewerteten Kleidungsstücke
(Kategorie, Farbe, Stil, Wärme, Formalität) lernt es:

- **Bewertungen ≥ 4 stärken** die Präferenz für die vorkommenden
  Attributwerte (z. B. „Blau“, „sporty“, warme Teile),
- **Bewertungen ≤ 2 schwächen** sie („mag Blau nicht mehr so“),
- **Bewertung 3 ist neutral** – sie verschiebt nichts.

Daraus bewertet die neue Komponente `PersonalPreference` jedes weitere
Outfit: Je mehr Attribute es mit dem gelernten Geschmack gemeinsam hat,
desto höher sein Präferenz-Score – und desto besser sein Platz im Ranking.
Ohne Feedback ist das Profil leer und die Komponente neutral (0.5), die
bisherige Empfehlung bleibt also unverändert.

```python
from loomi import OutfitFeedback, PreferenceProfile, Recommender

profile = PreferenceProfile()
recommender = Recommender(preference_profile=profile)

# … Empfehlung anzeigen …
# Feedback aus dem interaktiven Flow in das Profil einspeisen:
profile.update(OutfitFeedback(outfit=best.outfit, rating=5))
```

Gleiche Feedback-Sequenz → gleiches Profil: Das Lernen ist reproduzierbar
und jede Empfehlung zeigt in der Score-Aufschlüsselung (`preference`),
warum ein Outfit zum bisherigen Geschmack passt („aus 3 Bewertungen –
Farbe 1.00, Stil 0.50, …“). Der interaktive Modus (`-i` bzw. `loomi.main`)
verwendet das Profil automatisch; der Feedback-Flow selbst ist unverändert.

### Persistenz: Vorlieben überleben Sitzungen

`loomi.main` speichert das gelernte Profil in derselben SQLite-Datenbank
wie den Kleiderschrank (`PreferenceStore`, Tabelle `preference_profile`).
Beim nächsten Start wird es automatisch geladen – Vorlieben bleiben also
auch über Programm-Neustarts hinweg erhalten:

```python
from loomi.preferences import PreferenceProfile
from loomi.storage import PreferenceStore

pref_store = PreferenceStore("loomi.db")
profile = pref_store.load() or PreferenceProfile()  # gespeichert oder neu
# … Empfehlungen + Feedback …
pref_store.save(profile)  # am Ende der Sitzung speichern
```

Der Lernzustand wird als JSON-Blob abgelegt; `to_dict()`/`from_dict()`
machen das Profil serialisierbar. Die Demo (`loomi.demo`) bleibt bewusst
ohne Persistenz – sie arbeitet nur mit Beispieldaten in der Sitzung.

## Erweiterungspunkte (Roadmap)

- **Persönliche Vorlieben / User-Feedback**: Das `PreferenceProfile` ist
der erste Baustein – es wird bereits in der SQLite-Datenbank persistiert;
später können weitere Attribute (Material, Muster) oder mehrere Nutzer
(Profile je Person) ergänzt werden.
- **AI / Machine Learning**: eine ML-basierte Komponente kann die
  regelbasierte Präferenz-Logik ersetzen oder ergänzen – das
  `ScoreComponent`-Interface bleibt unverändert.
- **Abwechslung**: Historie kann um zeitliche Gewichtung („kürzlich“ statt
  „jemals“) erweitert werden.
- **Kontext**: z. B. Luftfeuchtigkeit, Wind, Nutzer-Mood oder
  Kleidungsstück-Attribute wie Material und Muster ergänzen.

## Projektstruktur

```
loomi/                 # bestehender Python-Kern (unverändert)
├── models.py          # Datenmodelle (Enums, ClothingItem, Outfit, Scores, Feedback)
├── wardrobe.py        # Wardrobe + Beispiel-Kleiderschrank
├── generator.py       # OutfitGenerator
├── preferences.py     # PreferenceProfile (lernt aus Feedback 1–5)
├── scoring/           # StyleMatch, ColorHarmony, OccasionFit, WeatherFit, Variety, PersonalPreference
├── recommender.py     # Recommender (gewichteter Gesamt-Score)
├── storage.py         # WardrobeStore + PreferenceStore (SQLite-Persistenz)
├── demo.py            # CLI-Demo (Szenarien + interaktive Wetter-Eingabe)
└── main.py            # Hauptprogramm (eigener Kleiderschrank, Feedback, Löschen)
webapp/                # Web-App über dem Kern (isoliert, keine Kern-Änderungen)
├── app.py             # LoomiApp: API-Schicht, nutzt nur bestehende Loomi-Funktionen
├── server.py          # HTTP-Server (nur Standardbibliothek) + statische Dateien
└── static/            # index.html, style.css, app.js (kein Build-Schritt)
tests/                 # pytest-Tests für alle Module inkl. webapp (test_webapp.py)
```
