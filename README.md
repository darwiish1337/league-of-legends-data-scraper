<div align="center">

# ⚔️ Riot LoL Ranked Data Scraper

Production-grade scraper for League of Legends ranked matches (Solo/Duo and Flex 5v5). Scrapes servers sequentially with a clean console UI, accurate per-server progress, durable persistence, and an enterprise logging system.

## Features

- Sequential multi-server scraping (EUW → EUNE → … → ME1)
- Ranked Solo/Duo and Ranked Flex 5v5 per region
- Configurable target matches per region
- Patch-aware filtering (e.g., 16.3 or 16.*)
- Console UI with banner, summary, “Server/Next Server”, and stable progress bar
+- Durable storage: SQLite database and CSV exports
- Endpoint-specific rate limits and concurrent async fetching
- Enterprise logging: colored console + JSON file logs, context, custom levels, optional function trace

## Project Layout

riot_data_scraper/
- config/ settings and environment
- domain/ entities, enums, interfaces
- infrastructure/ Riot API client and repositories
- application/ services and use cases
- presentation/ console UI (ScraperCLI)
- services/ utilities (e.g., DataDeleter)
- core/logging/ enterprise logging system
- data/ databases, CSV exports, logs
- main.py minimal entrypoint

## First-Time Setup

- Python 3.10+
- Create config/.env and set your RIOT_API_KEY
- Install dependencies:

```bash
pip install -r requirements.txt
```

**2 — Create your `.env` file**

```bash
# config/.env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**3 — Run the scraper**

```powershell
# PowerShell
$env:TARGET_PATCH="16.3"
$env:MATCHES_PER_REGION="2500"
python -u .\main.py
```

- You will see:
  - Startup banner
  - Configuration summary (first server, queue types, patch version)
  - For each region: Server / Next Server and a stable “0/target” progress bar
  - On completion: total matches, DB save notice, and CSV export notice

## Output

- Database: data/db/scraper.sqlite
- CSVs: data/csv/
  - matches.csv, teams.csv, participants.csv
  - participant_items.csv, participant_summoner_spells.csv
  - champions.csv, items.csv, summoner_spells.csv
- Logs:
  - Colored console logs
  - JSON logs at data/logs/scraper.jsonl

## Configuration

- Required:
  - RIOT_API_KEY in config/.env
- Common (ENV or settings.py):
  - MATCHES_PER_REGION: per-server target
  - MATCHES_TOTAL: optional global cap
  - TARGET_PATCH: exact (e.g., 16.3) or prefix (e.g., 16)
  - SCRAPE_MODE: patch (default) or date (requires SCRAPE_DATE=YYYY-MM-DD)
  - PATCH_START_DATE and PATCH_END_DATE: patch bounds (for patch mode)
  - MAX_CONCURRENT_REQUESTS and per-endpoint limits
  - SEED_PUUIDS and SEED_SUMMONERS: optional seed lists (comma-separated)
  - LOG_LEVEL: TRACE/DEBUG/INFO/SUCCESS/WARNING/ERROR/CRITICAL
  - DEBUG_TRACE=true to enable function entry/exit timing via decorator

## Enterprise Logging

- Layers:
  - core/logging/config.py: bootstrap/shutdown
  - core/logging/formatter.py: ConsoleFormatter (colored), JSONFormatter (structured)
  - core/logging/levels.py: custom TRACE and SUCCESS levels
  - core/logging/context.py: per-task context via contextvars (bind()/context)
  - core/logging/logger.py: StructuredLogger + traceable decorator
- Activation:
  - Logging is initialized in [main.py](./main.py) with service “scraper”, LOG_DIR, and JSON file output.
- Context example:

```python
from core.logging.logger import get_logger
from core.logging.context import context

log = get_logger(__name__, service="scraper").bind(request_id="abc123")

with context(user_id=42, region="euw1"):
    log.info("start processing")
    # output includes: region=euw1, request_id=abc123
```

**Function tracing** (enable with `DEBUG_TRACE=true`):

```python
from core.logging.logger import traceable

@traceable
def compute(a: int, b: int) -> int:
    return a + b
```

## Data Management (Deletion)

- Service: [services/data_deleter.py](./services/data_deleter.py)
  - DataDeleter:
    - list_tables() → list[str]
    - clear_table(table_name, confirm=True)
    - clear_all(confirm=True)
  - Programmatic usage:

```python
import sqlite3
 from application.services.data_deleter import DataDeleter

deleter = DataDeleter(lambda: sqlite3.connect("data/db/scraper.sqlite"))

deleter.list_tables()                         # → ['matches', 'teams', ...]
deleter.clear_table("participants", confirm=True)
deleter.clear_all(confirm=True)
```

- Interactive CLI: [delete_data.py](./delete_data.py)
  - Run:

```powershell
python -u .\delete_data.py
```

  - Choose all or specific, view a numbered table list for specific, confirm with “yes”.

## Architecture Notes

- Minimal entrypoint: main.py calls ScraperCLI and bootstraps logging
- Clean Architecture layering for domain/application/infrastructure/presentation
- Data persistence via DataPersistenceService with CSV export

## Troubleshooting

- 401 Unauthorized: check RIOT_API_KEY in config/.env (valid and not expired)
- 429 Rate Limited: reduce MAX_CONCURRENT_REQUESTS and adjust rate limits
- DNS issues for some platforms: provide SEED_PUUIDS/SEED_SUMMONERS, or test with a public DNS
- No seeds: add SEED_PUUIDS or SEED_SUMMONERS and retry

## 📄 License

For educational and data engineering purposes only.
This project is not affiliated with or endorsed by Riot Games.

---

<div align="center">


[![Made by](https://img.shields.io/badge/Made_by-Mohamed_Darwish-C8963E?style=flat-square&logo=github&logoColor=white)](https://github.com/MohamedDarwish) [![Riot API](https://img.shields.io/badge/Powered_by-Riot_Games_API-D32F2F?style=flat-square&logo=riotgames&logoColor=white)](https://developer.riotgames.com)

</div>
