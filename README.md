<div align="center">

# ⚔️ Riot LoL Ranked Data Scraper

**Production-grade data pipeline for League of Legends ranked matches**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Async](https://img.shields.io/badge/AsyncIO-Powered-FF6B6B?style=for-the-badge&logo=python&logoColor=white)](https://docs.python.org/3/library/asyncio.html)
[![Riot API](https://img.shields.io/badge/Riot_API-v4-D32F2F?style=for-the-badge&logo=riotgames&logoColor=white)](https://developer.riotgames.com)

[![Servers](https://img.shields.io/badge/Servers-EUW_→_ME1-C8963E?style=flat-square&logo=globe&logoColor=white)]()
[![Queues](https://img.shields.io/badge/Queues-Solo/Duo_+_Flex-5865F2?style=flat-square)]()
[![Storage](https://img.shields.io/badge/Export-SQLite_+_CSV-4EC994?style=flat-square)]()
[![Logging](https://img.shields.io/badge/Logging-JSON_+_Console-38C6C6?style=flat-square)]()
[![Health](https://img.shields.io/badge/Health-Circuit_Breaker_+_Retry-FF9800?style=flat-square)]()

*Scrapes Solo/Duo & Flex 5v5 ranked matches across all major servers with patch-aware filtering, async fetching, durable storage, health monitoring, and enterprise-grade logging.*

</div>

---

## 🗂️ Table of Contents

- [✨ Features](#-features)
- [📁 Project Structure](#-project-structure)
- [🏛️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [🩺 Health Check](#-health-check)
- [⚙️ Configuration](#️-configuration)
- [📊 Output Files](#-output-files)
- [📋 Logging System](#-logging-system)
- [🗑️ Data Management](#️-data-management)
- [🔍 DB Check](#-db-check)
- [🔧 Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌍 **Interactive Server Selection** | Pick servers by number, `all`, or `sea` — or run headless via `REGIONS` env var |
| 🏆 **Both Queue Types** | Ranked Solo/Duo and Ranked Flex 5v5 per region |
| 🔖 **Patch Filtering** | Exact (`16.3`) or prefix (`16.*`) patch-aware match filtering |
| 🎛️ **Console UI** | Labeled per-server progress: `euw1 \| ███----- \| 123/500` |
| 🩺 **Health System** | DNS + HTTP checks with Adaptive Retry and Circuit Breaker per platform |
| 🗄️ **Durable Storage** | SQLite database + automatic CSV export per table |
| ⚡ **Async Fetching** | Configurable concurrency with per-endpoint rate limiting + HTTP/2 support |
| 📋 **Enterprise Logging** | Colored console + structured JSON logs with context binding |
| 🗑️ **Data Management** | Interactive CLI + programmatic table clearing |
| 🔍 **DB Check** | List tables, count rows, and run integrity checks on the database |

---

## 📁 Project Structure

```
riot_data_scraper/
│
├── ⚙️  config/                          # Settings & environment
│   ├── settings.py                      # Central configuration values
│   └── .env                             # 🔐 RIOT_API_KEY (never commit)
│
├── 🧩 domain/                           # Pure business logic (no dependencies)
│   ├── entities/                        # Match, Participant, Team, Champion…
│   ├── enums/                           # Region, QueueType, Tier…
│   └── interfaces/                      # Abstract repository contracts
│
├── 🏗️  infrastructure/                  # External integrations
│   ├── riot_client.py                   # Async Riot API client
│   └── repositories/                   # SQLite repository implementations
│
├── 🔧 application/                      # Orchestration layer
│   ├── services/
│   │   ├── data_persistence_service.py  # SQLite + CSV persistence
│   │   ├── data_scraper/                # Core scraping logic
│   │   ├── seed/                        # Seed discovery service
│   │   ├── delete_data/                 # Data deletion service
│   │   └── health/                      # 🩺 Health subsystem
│   │       ├── dns_checker.py           # DNS resolution checks
│   │       ├── http_checker.py          # HTTP status checks
│   │       ├── retry_policy.py          # Adaptive retry logic
│   │       ├── circuit_breaker.py       # Circuit breaker per platform
│   │       └── manager.py               # Health manager (orchestrator)
│   └── use_cases/
│       └── scrape_matches.py            # Main scraping use case
│
├── 🖥️  presentation/cli/                # User-facing commands
│   ├── ScrapingCommand                  # Handles scraping flow + server selection
│   ├── HealthCommand                    # Runs health checks
│   ├── DeleteDataCommand                # Data deletion UI
│   └── DBCheckCommand                   # Database inspection UI
│
├── 📜 scripts/                          # Standalone entry scripts
│   ├── scraping.py                      # Run scraper directly
│   ├── health.py                        # Run health check directly
│   ├── delete_data.py                   # Run data deletion directly
│   └── db_check.py                      # Run DB check directly
│
├── 📋 core/logging/                     # Enterprise logging system
│   ├── config.py                        # Bootstrap & shutdown
│   ├── formatter.py                     # ConsoleFormatter + JSONFormatter
│   ├── levels.py                        # Custom TRACE & SUCCESS levels
│   ├── context.py                       # Per-task context (contextvars)
│   └── logger.py                        # StructuredLogger + @traceable
│
├── 💾 data/                             # All generated output (gitignored)
│   ├── db/
│   │   └── scraper.sqlite               # 🗄️ Main database
│   ├── csv/                             # 📊 Exported CSV tables
│   └── logs/
│       └── scraper.jsonl                # 📋 Structured JSON log stream
│
└── 🚀 main.py                           # Routing menu entrypoint
```

---

## 🏛️ Architecture

Clean Architecture with strict layer separation — dependencies only point inward.

```
┌─────────────────────────────────────────────────────────┐
│  🖥️  Presentation / CLI Commands                        
├─────────────────────────────────────────────────────────┤
│  🔧  Application (Services / Use Cases)                 
│       └── 🩺 Health (DNS · HTTP · Retry · Breaker)     
├────────────────────────┬────────────────────────────────┤
│  🧩  Domain            │  🏗️  Infrastructure           │
│  Entities / Enums      │  Riot Client / Repositories    │
│  Interfaces            │  SQLite / CSV                  │
└────────────────────────┴────────────────────────────────┘
           ↑ all layers share: 📋 core/logging
```

**Data flow:**

```
Config → Riot API → Domain Entities → Application Services → SQLite + CSV → CLI Output
```

---

## 🚀 Quick Start

**1 — Install dependencies**

```bash
pip install -r requirements.txt

# Optional: enable HTTP/2 support
pip install "httpx[http2]"
```

**2 — Create your `.env` file**

```bash
# config/.env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**3 — Run**

```powershell
# PowerShell
$env:TARGET_PATCH="16.3"
$env:MATCHES_PER_REGION="2500"
python -u .\main.py
```

```bash
# Bash / Linux / macOS
TARGET_PATCH="16.3" MATCHES_PER_REGION="2500" python -u main.py
```

**Main menu:**

```
1) Delete data
2) Health check
3) DB check
4) Scraping
```

**When you choose `4) Scraping`**, you'll be prompted to pick servers:

```
# Interactive — pick by number, type "all", or "sea"
> all

# Headless / CI — skip the prompt entirely
REGIONS=euw1 python -u main.py
REGIONS=sg2,th2 python -u main.py
```

**Progress looks like:**

```
euw1 | ████████-- | 423/500
```

---

## 🩺 Health Check

Check platform availability before or during scraping.

**Via main menu** — option `2) Health check`

**Or run directly:**

```powershell
python -u .\scripts\health.py
```

Menu options:
- `1)` Check specific platforms → numbered list; supports `all` and `sea`
- `2)` Toggle JSON output
- `3)` Toggle Fail-Fast (stop on first failure)
- `4)` Settings → cache TTL, default path, circuit breaker threshold/reset, metrics hook

**Environment overrides:**

| Variable | Description |
|---|---|
| `HEALTH_CACHE_TTL_S` | Cache window in seconds |
| `HEALTH_PATH` | Status path (default: `/lol/status/v4/platform-data`) |
| `HEALTH_RETRY_ATTEMPTS` | Number of retry attempts |
| `HEALTH_RETRY_BACKOFF_MS` | Base backoff in milliseconds |
| `HEALTH_RETRY_FACTOR` | Backoff multiplier |
| `HEALTH_RETRY_JITTER_MS` | Random jitter added to backoff |

---

## ⚙️ Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `RIOT_API_KEY` | ✅ Required | — | Your Riot developer API key |
| `MATCHES_PER_REGION` | Optional | `1000` | Target matches to collect per server |
| `MATCHES_TOTAL` | Optional | — | Global cap across all regions |
| `TARGET_PATCH` | Optional | — | Filter by patch — `16.3` or `16` |
| `SCRAPE_MODE` | Optional | `patch` | `patch` or `date` (requires `SCRAPE_DATE`) |
| `SCRAPE_DATE` | Optional | — | `YYYY-MM-DD` — used when `SCRAPE_MODE=date` |
| `PATCH_START_DATE` | Optional | — | Lower bound for patch date range |
| `PATCH_END_DATE` | Optional | — | Upper bound for patch date range |
| `MAX_CONCURRENT_REQUESTS` | Optional | `5` | Global async concurrency limit |
| `SEED_PUUIDS` | Optional | — | Comma-separated PUUIDs to seed the player pool |
| `SEED_SUMMONERS` | Optional | — | Comma-separated summoner names as seeds |
| `REGIONS` | Optional | — | Limit run to specific servers, e.g. `euw1` or `sg2,th2` |
| `DISABLED_REGIONS` | Optional | — | Blacklist servers to skip, e.g. `ph2` |
| `RANDOM_SCRAPE` | Optional | `false` | Randomize per-region match targets |
| `RANDOM_REGION_TARGET_MIN` | Optional | — | Min target when `RANDOM_SCRAPE=true` |
| `RANDOM_REGION_TARGET_MAX` | Optional | — | Max target when `RANDOM_SCRAPE=true` |
| `MAX_MATCHES_PER_CHUNK` | Optional | — | Per-iteration queue cap for smoother progress |
| `LOG_LEVEL` | Optional | `INFO` | `TRACE` / `DEBUG` / `INFO` / `SUCCESS` / `WARNING` / `ERROR` / `CRITICAL` |
| `DEBUG_TRACE` | Optional | `false` | Set `true` to enable `@traceable` function timing |

---

## 📊 Output Files

```
data/
├── db/
│   └── scraper.sqlite                   ← single source of truth
└── csv/
    ├── matches.csv                      ← match-level data
    ├── teams.csv                        ← team outcomes
    ├── participants.csv                 ← player stats per match
    ├── participant_items.csv            ← items built
    ├── participant_summoner_spells.csv  ← summoner spell choices
    ├── champions.csv                    ← champion reference table
    ├── items.csv                        ← item reference table
    ├── summoner_spells.csv              ← spell reference table
    └── platforms.csv                    ← platform/server metadata
```

---

## 📋 Logging System

The logging system lives in `core/logging/` with **two output streams**:

| Stream | Format | Level |
|---|---|---|
| Console | Colored human-readable | Configurable via `LOG_LEVEL` |
| File (`scraper.jsonl`) | Structured JSON | All levels |

**Log levels** (low → high):

```
TRACE → DEBUG → INFO → SUCCESS → WARNING → ERROR → CRITICAL
```

> `TRACE` and `SUCCESS` are custom levels added on top of the standard Python logging module.

**Binding context to logs:**

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
# automatically logs: function entry, exit, and execution time
```

---

## 🗑️ Data Management

**Via main menu** — option `1) Delete data`

**Or run directly:**

```powershell
python -u .\scripts\delete_data.py
```

Prompts you to delete all tables or pick specific ones from a numbered list. Requires typing `yes` to confirm.

**Programmatic usage:**

```python
import sqlite3
from application.services.data_deleter import DataDeleter

deleter = DataDeleter(lambda: sqlite3.connect("data/db/scraper.sqlite"))

deleter.list_tables()                          # → ['matches', 'teams', ...]
deleter.clear_table("participants", confirm=True)
deleter.clear_all(confirm=True)
```

---

## 🔍 DB Check

Inspect the database without opening it manually.

**Via main menu** — option `3) DB check`

**Or run directly:**

```powershell
# Interactive
python -u .\scripts\db_check.py

# Non-interactive flags
python -u .\scripts\db_check.py --list --count --integrity
```

Options:
- `1)` List tables
- `2)` Count rows per table
- `3)` PRAGMA integrity check

---

## 🔧 Troubleshooting

**`401 Unauthorized`**
> Check `RIOT_API_KEY` in `config/.env` — make sure it's valid and hasn't expired. Get a new key from [developer.riotgames.com](https://developer.riotgames.com).

**`429 Too Many Requests`**
> Reduce `MAX_CONCURRENT_REQUESTS` and tune per-endpoint rate limits in `config/settings.py`.

**DNS / Connection errors on SEA platforms**
> The client auto-fallbacks across `ph2 → sg2 → th2 → tw2 → vn2 → oc1` for league/summoner endpoints.
> If all platform hosts fail, provide `SEED_PUUIDS` or `SEED_SUMMONERS` to proceed via the regional route.
> Or set `DISABLED_REGIONS=ph2` to skip the problematic server until DNS improves.

**No matches collected / empty results**
> Add at least one entry to `SEED_PUUIDS` or `SEED_SUMMONERS` to seed the player pool and retry.

---

## 📄 License

For educational and data engineering purposes only.
This project is not affiliated with or endorsed by Riot Games.

---

<div align="center">

[![Made by](https://img.shields.io/badge/Made_by-Darwish-C8963E?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MohamedDarwish) [![Riot API](https://img.shields.io/badge/Powered_by-Riot_Games_API-D32F2F?style=for-the-badge&logo=riotgames&logoColor=white)](https://developer.riotgames.com)

</div>
