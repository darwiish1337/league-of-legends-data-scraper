# Riot Games LoL Ranked Data Scraper

Production-grade scraper for League of Legends ranked matches (Solo/Duo and Flex 5v5). Scrapes servers sequentially with a clean console UI, accurate per-server progress, durable persistence, and an enterprise logging system.

## Features

- Interactive server selection and sequential scraping (EUW → EUNE → … → ME1)
- Ranked Solo/Duo and Ranked Flex 5v5 per region
- Configurable target matches per region
- Patch-aware filtering (e.g., 16.3 or 16.*)
- Console UI with banner, summary, and labeled per-server progress like: `euw1 | ███----- | 123/500`
- Health system: DNS + HTTP checks with Adaptive Retry and Circuit Breaker
- Durable storage: SQLite database and CSV exports
- Endpoint-specific rate limits and concurrent async fetching
- Enterprise logging: colored console + JSON file logs, context, custom levels, optional function trace

## Project Layout

- config/ settings and environment
- domain/ entities, enums, interfaces
- infrastructure/ Riot API client and repositories
- application/
  - services/
    - data_persistence_service.py
    - health/ (dns/http checkers, retry policy, circuit breaker, manager)
    - data_scraper/
    - seed/
    - delete_data/
  - use_cases/ (e.g., scrape_matches.py)
- presentation/cli/ (ScrapingCommand, HealthCommand, DeleteDataCommand, DBCheckCommand)
- scripts/ (scraping.py, health.py, delete_data.py, db_check.py)
- core/logging/ enterprise logging system
- data/ databases, CSV exports, logs
- main.py minimal entrypoint (routing menu)

## First-Time Setup

- Python 3.10+
- Create config/.env and set your RIOT_API_KEY
- Install dependencies:

```bash
pip install -r requirements.txt
```

## How to Run

- Set patch and per-region target (PowerShell):

```powershell
$env:TARGET_PATCH="16.3"
$env:MATCHES_PER_REGION="2500"
python -u .\main.py
```

Main menu:
- 1) Delete data
- 2) Health check
- 3) DB check
- 4) Scraping

- When you choose “4) Scraping”, you’ll be prompted to pick servers (numbers, `all`, or `sea`).
  - To run headless/CI without prompts, set `REGIONS` (e.g., `REGIONS=euw1` or `REGIONS=sg2,th2`).
  - Progress is labeled by server code to avoid confusion across regions.
  - On completion: you’ll see total matches, DB save notice, and CSV export notice.

## Health Check

Interactive:

```powershell
python -u .\scripts\health.py
```

- 1) Check specific platforms → numbered list; supports `all` and `sea`
- 2) Toggle JSON output
- 3) Toggle Fail-Fast (stop on first failure)
- 4) Settings → cache TTL, default path, circuit breaker threshold/reset, metrics hook

Environment (optional):
- HEALTH_CACHE_TTL_S: cache window (seconds)
- HEALTH_PATH: status path (default /lol/status/v4/platform-data)
- HEALTH_RETRY_ATTEMPTS, HEALTH_RETRY_BACKOFF_MS, HEALTH_RETRY_FACTOR, HEALTH_RETRY_JITTER_MS

## Output

- Database: data/db/scraper.sqlite
- CSVs: data/csv/
  - matches.csv, teams.csv, participants.csv
  - participant_items.csv, participant_summoner_spells.csv
  - champions.csv, items.csv, summoner_spells.csv
  - platforms.csv
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
  - REGIONS: limit run to specific servers (e.g., euw1 or sg2,th2)
  - DISABLED_REGIONS: blacklist servers to skip (e.g., ph2)
  - RANDOM_SCRAPE=true to randomize per-region targets
  - RANDOM_REGION_TARGET_MIN and RANDOM_REGION_TARGET_MAX when RANDOM_SCRAPE=true
  - MAX_MATCHES_PER_CHUNK: per-iteration queue cap for smoother progress
  - To enable HTTP/2: pip install "httpx[http2]"

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

log = get_logger(__name__, service="service").bind(request_id="abc123")
with context(user_id=42, region="euw1"):
    log.info("start processing")
```

- Function tracing (when DEBUG_TRACE=true):

```python
from core.logging.logger import traceable

@traceable
def compute(a: int, b: int) -> int:
    return a + b
```

## Data Management (Deletion)

- Service: [application/services/data_deleter.py](./application/services/data_deleter.py)
  - DataDeleter:
    - list_tables() → list[str]
    - clear_table(table_name, confirm=True)
    - clear_all(confirm=True)
  - Programmatic usage:

```python
import sqlite3
 from application.services.data_deleter import DataDeleter

deleter = DataDeleter(lambda: sqlite3.connect("data/db/scraper.sqlite"))
print(deleter.list_tables())
deleter.clear_table("participants", confirm=True)
deleter.clear_all(confirm=True)
```

Interactive:

```powershell
python -u .\scripts\delete_data.py
```

Or use the main menu option “1) Delete data” to clear specific tables or all data interactively.

## DB Check

Interactive:

```powershell
python -u .\scripts\db_check.py
```

Options:
- 1) List tables
- 2) Count rows per table
- 3) PRAGMA integrity_check

Non-interactive:

```powershell
python -u .\scripts\db_check.py --list --count --integrity
```

## Architecture Notes

- Minimal entrypoint: main.py calls ScraperCLI and bootstraps logging
- Clean Architecture layering for domain/application/infrastructure/presentation
- Data persistence via DataPersistenceService with CSV export
- Seed discovery encapsulated in application/services/seed_discovery_service.py (used by DataScraperService)

## Troubleshooting

- 401 Unauthorized: check RIOT_API_KEY in config/.env (valid and not expired)
- 429 Rate Limited: reduce MAX_CONCURRENT_REQUESTS and adjust rate limits
- DNS issues on SEA platforms:
  - The client auto-fallbacks across ph2→sg2→th2→tw2→vn2→oc1 for league/summoner
  - If all platform hosts fail, provide SEED_PUUIDS/SEED_SUMMONERS to proceed via the regional route
  - Or set DISABLED_REGIONS=ph2 to skip until DNS improves
- No seeds: add SEED_PUUIDS or SEED_SUMMONERS and retry

## License

Educational and data engineering purposes.
