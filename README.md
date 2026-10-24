# Gratis-Spiele-Scraper (PC & PS5)

Der Gratis-Spiele-Scraper fragt regelmäßig mehrere Spieleshops und Aktionsquellen ab – Epic Games Store, Steam, GOG, PlayStation Store und den Aggregator GamerPower – und sammelt alle PC- und PS5-Spiele, die gerade in einer Aktion zu 100 % kostenlos sind. Die Treffer landen in einer SQLite-Datenbank und erscheinen in einer Weboberfläche als durchsuchbare, filter- und sortierbare Liste mit dem normalen Originalpreis, dem Shop und der Plattform. Free-to-play-Spiele, Demos, Einträge mit Normalpreis 0 und andere Plattformen werden ausgefiltert. Neue Quellen lassen sich über ein einheitliches Adapter-Interface ergänzen.

## Tech-Stack

- **Backend:** Python 3.12+, FastAPI, Uvicorn, httpx, SQLAlchemy 2, SQLite; der Scheduler läuft als eigener Hintergrund-Thread im API-Prozess
- **Frontend:** React + TypeScript mit Vite
- **Tests:** pytest mit aufgezeichneten Fixtures für alle Adapter (kein Netzwerkzugriff), vitest für das Frontend
- **Lint:** ruff (`ruff format`, `ruff check`)

## Projektstruktur

```
backend/              FastAPI-Service "api"
  app/main.py         App-Fabrik, Router, einheitliche Fehlerkörper, CORS
  app/config.py       Konfiguration aus Umgebungsvariablen
  app/db.py           SQLite-Engine, Sessions, Schema-Erzeugung beim Start
  app/models.py       Tabellen deals und source_states
  app/http.py         ausgehende Requests mit Timeout und Größenlimit
  app/urls.py         Prüfung von Link-/Bild-URLs auf http/https
  app/adapters/       ein Adapter pro Quelle + registry.py
  app/runner.py       Scraper-Lauf (Deduplizierung, Ablauf, Fehlerisolation)
  app/scheduler.py    Lauf beim Start und im Intervall, Sperre gegen Doppelläufe
  app/cli.py          Kommandozeile (manueller Lauf)
  app/seed.py         Demo-Daten laden
  app/routers/        HTTP-Endpunkte
  tests/              pytest-Tests
frontend/             Vite/React-Service "web"
Makefile              install, dev, seed, refresh, test
RUN.json              maschinenlesbare Startbeschreibung
```

`RUN.json` beschreibt zwei Teile: den Service `api` (Verzeichnis `backend/`, Start mit `python -m uvicorn app.main:app --port $PORT --no-access-log`, Health-Check `GET /api/health`, Seed `python -m app.seed`) und `tasks` – das `Makefile` im Wurzelverzeichnis. Es ist kein eigenes Programm, sondern nur der Aufgaben-Runner: Installiert wird mit `make install`, getestet mit `make test`, und gestartet wird es nie selbst.

## Installation

Voraussetzungen: Python 3.12 oder neuer, Node.js 20 oder neuer mit npm, `make` (unter Windows z. B. über Git Bash oder WSL).

```bash
make install
```

Das installiert `backend/requirements.txt` per pip und die Frontend-Abhängigkeiten per npm. Empfohlen ist eine virtuelle Umgebung:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
make install
```

## Starten (Entwicklung)

Ein Befehl startet alles – API und Weboberfläche zusammen:

```bash
make dev
```

- API: <http://localhost:8000> (interaktive API-Doku unter <http://localhost:8000/docs>)
- Weboberfläche: <http://localhost:5173>

`Strg+C` beendet beide Prozesse. Ports lassen sich überschreiben, z. B. `make dev API_PORT=8001 WEB_PORT=5174`.

Beim Start legt das Backend die Datenbank und ihr Schema automatisch an und startet (wenn `SCRAPE_ON_START=true`) sofort einen ersten Scraper-Lauf; danach läuft der Scraper alle `REFRESH_INTERVAL_HOURS` Stunden.

Ohne `make` lassen sich beide Teile auch einzeln starten:

```bash
# Terminal 1 – API
cd backend
python -m uvicorn app.main:app --port 8000 --no-access-log

# Terminal 2 – Weboberfläche
cd frontend
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Demo-Daten (Seed)

```bash
make seed
```

Lädt die Demo-Deals aus `backend/app/fixtures/demo_deals.json` samt Quellenstatus in die Datenbank (entspricht `cd backend && python -m app.seed`). Der Befehl ist idempotent: mehrfaches Ausführen erzeugt keine Duplikate. So zeigt die Oberfläche auch ohne Internetzugang sofort eine Liste.

## Manueller Aktualisierungslauf

Per Kommandozeile (synchron, gibt das Ergebnis je Quelle aus):

```bash
make refresh
# entspricht: cd backend && python -m app.cli refresh
```

Per API (startet den Lauf im Hintergrund):

```bash
curl -X POST http://localhost:8000/api/refresh
```

In der Weboberfläche löst der Button **„Jetzt aktualisieren“** denselben Lauf aus. Es läuft immer höchstens ein Lauf gleichzeitig; ein weiterer Aufruf währenddessen wird mit `409` abgelehnt, und Aufrufe pro Client sind ratenbegrenzt (`429`).

## Produktions-Build

```bash
# Frontend bauen (statische Dateien in frontend/dist)
cd frontend
VITE_API_BASE_URL=https://api.example.org npm run build
npm run preview            # gebautes Frontend lokal ansehen

# Backend ohne Reload starten
cd backend
CORS_ORIGINS=https://www.example.org python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

Wird das gebaute Frontend unter demselben Origin wie die API ausgeliefert, bleibt `VITE_API_BASE_URL` leer.

## Konfiguration

Alle Werte kommen aus Umgebungsvariablen und haben sinnvolle Standardwerte; zum Starten muss nichts gesetzt werden.

| Variable | Standard | Bedeutung |
|---|---|---|
| `REFRESH_INTERVAL_HOURS` | `6` | Intervall des automatischen Scraper-Laufs in Stunden (Kommazahl erlaubt, > 0) |
| `DATABASE_PATH` | `backend/data/games.db` | Pfad der SQLite-Datei; das Verzeichnis wird automatisch angelegt |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173` | Kommagetrennte Liste der erlaubten Frontend-Origins; `*` wird nie akzeptiert |
| `SCRAPE_ON_START` | `true` | Ersten Lauf direkt beim Start ausführen (`true`/`false`) |
| `HTTP_TIMEOUT_SECONDS` | `15` | Timeout ausgehender Scraper-Requests |
| `HTTP_MAX_BYTES` | `10485760` | Maximale Antwortgröße ausgehender Scraper-Requests (10 MiB) |
| `PORT` | `8000` | Port der API (über `--port` an Uvicorn übergeben) |
| `VITE_API_BASE_URL` | leer (= gleicher Origin) | Basis-URL der API für das Frontend (zur Build-Zeit) |

Beispiel:

```bash
cd backend
REFRESH_INTERVAL_HOURS=2 DATABASE_PATH=/var/lib/gratis-spiele/games.db python -m uvicorn app.main:app --no-access-log
```

## Bedienung der Weboberfläche

- **Liste:** jede Karte zeigt Titel, Shop, Plattform (PC/PS5), Originalpreis mit Währung, Titelbild und – falls bekannt – das Aktionsende. Ein Klick öffnet die Angebotsseite des Shops in einem neuen Tab.
- **Suche:** Titelsuche im Suchfeld.
- **Filter:** Plattform (Alle/PC/PS5), Shop, Preisbereich (Originalpreis von/bis).
- **Sortierung:** nach Titel, Originalpreis, Aktionsende oder „zuerst gesehen“, auf- oder absteigend.
- Alle Filter wirken ohne Neuladen der Seite; der Zustand steht in der URL und bleibt nach einem Reload oder als Lesezeichen erhalten. **„Filter zurücksetzen“** stellt den Ausgangszustand her.
- **Statusleiste:** „Zuletzt aktualisiert“, Button „Jetzt aktualisieren“ und der Status jeder Quelle (letzter Lauf, Erfolg oder Fehlermeldung, Anzahl Deals).
- **Zustände:** Ladeanzeige, verständliche Fehlermeldung, wenn das Backend nicht erreichbar ist, und ein Leer-Zustand mit Zurücksetzen, wenn Filter keine Treffer liefern.
- **Impressum** und **Datenschutzerklärung** sind von jeder Seite im Footer verlinkt.

## API

Alle Antworten sind JSON (UTF-8), Zeitangaben sind ISO-8601-Strings in UTC. Es gibt keine Anmeldung.

### `GET /api/health`

```json
{"status": "ok"}
```

### `GET /api/deals`

Liefert nur aktuelle (nicht abgelaufene) Gratis-Deals.

| Parameter | Werte | Standard |
|---|---|---|
| `q` | Suchtext im Titel | – |
| `platform` | `pc` oder `ps5` | alle |
| `store` | Shopname (siehe `/api/stores`) | alle |
| `sort` | `title`, `original_price`, `ends_at`, `first_seen` | `first_seen` |
| `order` | `asc`, `desc` | `desc` |
| `min_price`, `max_price` | Originalpreis-Grenzen (≥ 0) | – |
| `limit` | 1 bis 100 | `20` |
| `offset` | ≥ 0 | `0` |

Ungültige Werte (z. B. `limit=500`) werden mit `422` und dem einheitlichen Fehlerkörper abgelehnt.

```bash
curl "http://localhost:8000/api/deals?q=quest&platform=pc&sort=original_price&order=desc&limit=10"
```

```json
{
  "items": [
    {
      "id": 1,
      "title": "Beispielspiel",
      "store": "Epic Games Store",
      "platform": "pc",
      "original_price": 19.99,
      "currency": "EUR",
      "url": "https://store.epicgames.com/de/p/beispielspiel",
      "image_url": "https://cdn.example.org/beispielspiel.jpg",
      "starts_at": "2026-10-22T15:00:00Z",
      "ends_at": "2026-10-29T15:00:00Z",
      "first_seen_at": "2026-10-22T15:05:12Z",
      "last_seen_at": "2026-10-24T09:00:03Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### `GET /api/stores`

Sortierte Liste der Shops mit aktuellen Deals.

```json
{"items": ["Epic Games Store", "GOG", "PlayStation Store", "Steam"]}
```

### `GET /api/sources/status`

```json
{
  "items": [
    {
      "name": "epic",
      "last_run_at": "2026-10-24T09:00:00Z",
      "ok": true,
      "error": null,
      "deal_count": 2,
      "last_success_at": "2026-10-24T09:00:00Z"
    },
    {
      "name": "steam",
      "last_run_at": "2026-10-24T09:00:01Z",
      "ok": false,
      "error": "timeout after 15s fetching https://store.steampowered.com/...",
      "deal_count": 1,
      "last_success_at": "2026-10-23T21:00:02Z"
    }
  ],
  "last_updated_at": "2026-10-24T09:00:03Z",
  "running": false
}
```

### `POST /api/refresh`

Kein Request-Body. Startet einen Scraper-Lauf im Hintergrund.

- `202` → `{"status": "started"}`
- `409` → es läuft bereits ein Lauf
- `429` → Ratenlimit für diesen Client überschritten

### Einheitlicher Fehlerkörper

Jede Antwort mit einem Status außerhalb von 2xx (auch 404, 409, 422, 429, 500) hat diese Form; Stacktraces werden nie ausgeliefert:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request parameters",
    "details": [{"loc": ["query", "limit"], "msg": "Input should be less than or equal to 100", "type": "less_than_equal"}]
  }
}
```

## Tests

```bash
make test
```

Führt `pytest` im Backend und `npm test` (vitest) im Frontend aus. Kein Test greift auf das Netzwerk zu: die Adapter-Tests spielen aufgezeichnete Fixtures aus `backend/tests/fixtures/` ab, und ein Test-Fixture lässt jeden Verbindungsversuch nach außen fehlschlagen. Jeder Test nutzt eine eigene temporäre SQLite-Datei.

Einzeln:

```bash
cd backend && python -m pytest
cd backend && ruff format --check . && ruff check .
cd frontend && npm test
```

## Einen neuen Adapter hinzufügen

1. Eine Datei `backend/app/adapters/<quelle>.py` anlegen, deren Klasse `SourceAdapter` implementiert:

   ```python
   from app import http
   from app.adapters.base import FetchJson, FetchText, NormalizedDeal, SourceAdapter, SourceFetchError
   from app.urls import safe_http_url


   class BeispielAdapter(SourceAdapter):
       name = "beispiel"

       def __init__(
           self, fetch_json: FetchJson = http.fetch_json, fetch_text: FetchText = http.fetch_text
       ) -> None:
           self._fetch_json = fetch_json
           self._fetch_text = fetch_text

       def fetch(self) -> list[NormalizedDeal]:
           data = self._fetch_json("https://api.beispiel.example/free")
           deals: list[NormalizedDeal] = []
           for item in data.get("items", []):
               url = safe_http_url(item.get("url"))
               if url is None or item.get("price", 0) <= 0:
                   continue
               deals.append(
                   NormalizedDeal(
                       source_deal_id=str(item["id"]),
                       title=item["title"],
                       store="Beispiel-Shop",
                       platform="pc",
                       original_price=float(item["price"]),
                       currency="EUR",
                       url=url,
                       image_url=safe_http_url(item.get("image")),
                       starts_at=None,
                       ends_at=None,
                   )
               )
           return deals
   ```

   `fetch()` liefert nur Deals mit 100 % Rabatt, Originalpreis > 0 und Plattform `pc` oder `ps5`; bei Timeout, HTTP- oder Parse-Fehlern wirft er `SourceFetchError`. Requests laufen immer über `app.http` (Timeout und Größenlimit inklusive).
2. Die Klasse in `backend/app/adapters/registry.py` mit einer Zeile in `ADAPTER_CLASSES` eintragen.
3. Einen Test mit aufgezeichneter Fixture unter `backend/tests/` ergänzen; die Fetch-Funktionen werden dabei über den Konstruktor ersetzt.

Scheduler, Lauf-Logik, API und Oberfläche übernehmen die neue Quelle ohne weitere Änderung.

## Funktionen

- Adapter für Epic Games Store, Steam, GOG, PlayStation Store und den Aggregator GamerPower
- Nur PC- und PS5-Spiele mit 100 % Rabatt und echtem Originalpreis > 0
- Automatischer Lauf beim Start und im konfigurierbaren Intervall, manueller Lauf per Button, API und CLI
- Keine Duplikate bei wiederholten Läufen; abgelaufene oder nicht mehr angebotene Deals verschwinden aus der Liste
- Fällt eine Quelle aus, bleiben ihre Deals erhalten, die übrigen Quellen werden gespeichert, und der Fehler ist im Quellenstatus sichtbar
- Suche, Filter (Plattform, Shop, Preis), Sortierung und Paginierung, Zustand in der URL
- Sicherheit: höchstens ein Lauf gleichzeitig und Ratenbegrenzung für `POST /api/refresh`, nur http/https-Links, Timeout und Größenlimit für ausgehende Requests, explizite CORS-Origins, gebundene SQL-Parameter
- Datenschutz: keine Speicherung oder Protokollierung von IP-Adressen und User-Agents der Besucher (Access-Log ist abgeschaltet), keine Drittanbieter-Ressourcen in der Oberfläche, Impressum und Datenschutzerklärung
