# Bibliotheksübergreifendes Suchsystem

Ein effizientes Tool zur parallelen Suche in mehreren Bibliothekskatalogen.

## Features

- Gleichzeitige Suche in mehreren Bibliothekskatalogen
- Übersichtliche Darstellung der Suchergebnisse
- Export-Funktionen für gefundene Literatur
- Filtermöglichkeiten für Suchergebnisse

## Installation

1. Python 3.8+ installieren
2. Repository klonen:
```bash
git clone [repository-url]
cd library-search-tool
```

3. Virtuelle Umgebung erstellen und aktivieren:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

4. Projekt im Entwicklungsmodus installieren:
```bash
pip install -e .
```

## Entwicklung

- `src/scrapers/`: Enthält die Scraper für verschiedene Bibliotheken
- `src/api/`: FastAPI Backend
- `src/frontend/`: Frontend-Komponenten
- `src/models/`: Datenmodelle
- `src/utils/`: Hilfsfunktionen

## Server starten

1. Backend starten:
```bash
cd src
uvicorn api.main:app --reload
```

2. Frontend öffnen:
- Öffnen Sie `src/frontend/index.html` in einem Webbrowser

## Tests

```bash
pytest
```

## Lizenz

MIT 