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

*Scrapes Solo/Duo & Flex 5v5 ranked matches across all major servers with patch-aware filtering, async fetching, durable storage, and enterprise-grade logging.*

</div>

---

## 🗂️ Table of Contents

- [✨ Features](#-features)
- [📁 Project Structure](#-project-structure)
- [🏛️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#️-configuration)
- [📊 Output Files](#-output-files)
- [📋 Logging System](#-logging-system)
- [🩺 Health Check](#-health-check)
- [🗑️ Data Management](#️-data-management)
- [🔧 Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌍 **Multi-Server Scraping** | Sequential scraping across all Riot platforms (EUW → EUNE → … → ME1) |
| 🏆 **Both Queue Types** | Ranked Solo/Duo and Ranked Flex 5v5 per region |
| 🔖 **Patch / Date Filtering** | Patch-aware (`16.3` / `16.*`) with tight date window to avoid old games |
| 🎛️ **Console UI** | Main menu + live per-region progress with ETA and Server/Next Server display |
| 🗄️ **Durable Storage** | SQLite database + automatic CSV export per table |
| ⚡ **Async Fetching** | Optimised concurrency with per-endpoint rate limiting (1s / 2min windows) |
| 🧠 **Smart Seeding** | High-elo leagues + DB seeds + optional SEED_PUUIDS / SEED_SUMMONERS |
| 🧬 **Rich Reference Data** | Champions with roles, items, and summoner spells from Data Dragon |
| 📋 **Enterprise Logging** | Colored console + structured JSON logs with context binding |
| 🩺 **Health Tools** | Simple API key / DNS / platform health checks |
| 🗑️ **Data Management** | Interactive CLI + programmatic table clearing |

---

## 📁 Project Structure

```
riot_data_scraper/
│
├── ⚙️  config/                     # Settings & environment
│   ├── settings.py                 # Central configuration values
│   └── .env                        # 🔐 RIOT_API_KEY (never commit)
│
├── 🧩 domain/                      # Pure business logic (no dependencies)
│   ├── entities/                   # Match, Participant, Team, Champion…
│   ├── enums/                      # Region, QueueType, Tier…
│   └── interfaces/                 # Abstract repository contracts
│
├── 🏗️  infrastructure/             # External integrations
│   ├── api/riot_client.py          # Async Riot API client
│   ├── repositories/               # SQLite repository implementations
│   ├── health/                     # DNS/API/platform helpers
│   └── notifications/              # Windows desktop notifications
│
├── 🔧 application/                 # Orchestration layer
│   ├── services/
│   │   ├── data_scraper/           # Core scraping logic
│   │   ├── seed/                   # Seed discovery service
│   │   ├── delete_data/            # Data deletion service
│   │   ├── data_persistence_service.py  # DB + CSV export + scrape_sessions
│   │   └── region_scrape_runner.py # Region-level orchestration for scrapes
│   └── use_cases/                  # Business use cases (e.g., scrape_matches.py)
│
├── 🖥️  presentation/cli/           # Console UI commands
│   ├── scraping_command.py         # Main scraping command (supports resume)
│   ├── targeted_scrape_command.py  # Targeted single-server / start-from-server scrape
│   ├── health_command.py           # Health tools (API key / DNS / platforms)
│   ├── notifications_command.py    # Notification settings (toggle + test)
│   ├── delete_data_command.py      # Delete data command
│   └── db_check_command.py         # DB check command
│
├── 🧪 scripts/                     # Script entrypoints
│   ├── scraping.py                 # Run scraper directly
│   ├── health.py                   # Run health checks
│   ├── delete_data.py              # Run deletion CLI
│   └── db_check.py                 # Run DB check CLI
│
├── 📋 core/logging/                # Enterprise logging system
│   ├── config.py                   # Bootstrap & shutdown
│   ├── formatter.py                # ConsoleFormatter + JSONFormatter
│   ├── levels.py                   # Custom TRACE & SUCCESS levels
│   ├── context.py                  # Per-task context (contextvars)
│   └── logger.py                   # StructuredLogger + @traceable
│
├── 💾 data/                        # All generated output (gitignored)
│   ├── db/
│   │   └── scraper.sqlite          # 🗄️ Main database
│   ├── csv/                        # 📊 Exported CSV tables
│   └── logs/
│       └── scraper.jsonl           # 📋 Structured JSON log stream
│
└── 🚀 main.py                      # Minimal entrypoint with main menu
```

---

## 🔁 Key Implementation Improvements

- **Correct rate limits**
  - Uses realistic Riot limits per 1 second and per 2 minutes instead of a slow 10‑minute window.
  - Separate budgets for match, summoner, and league endpoints to keep the pipeline fast and safe.
- **Tight patch window**
  - Defaults to `TARGET_PATCH=16.3` with `PATCH_START_DATE` set near the actual release date.
  - Avoids downloading years of old matches only to discard them as off‑patch.
- **Per-region PUUID isolation**
  - Global set of `scraped_match_ids` prevents re-downloading the same match across runs.
  - Region-local PUUID pools ensure EUW seeds are not reused on EUNE (faster discovery, fewer empty calls).
- **Smarter seeding**
  - Bootstraps from Challenger/GM/Master leagues, DB seeds, and optional `SEED_PUUIDS` / `SEED_SUMMONERS`.
  - Falls back gracefully if some platforms (especially SEA) have DNS issues.
- **Better match tables**
  - `matches` includes both ISO date and `match_date_simple` (e.g. `2/2/2026`) plus `duration_mmss` (`45:00`, `30:00`).
  - `participants` stores full rank tier/division, items, spells, and per-player damage/gold stats.
- **Full reference coverage**
  - `champions` table stores every champion with inferred lane roles (e.g. `Top, Middle, Support`).
  - `items` and `summoner_spells` are seeded from Data Dragon with human-readable names.
- **Role normalization**
  - Role enum maps common aliases (`SUP`, `UTILITY`, `ADC`, `BOT`, `MID`, `JG`) into canonical roles like `SUPPORT` and `BOTTOM`.

- **Session-aware scraping**
  - Each run is tracked in `scrape_sessions` and `scrape_session_regions`.
  - On startup, incomplete sessions are detected and you can choose:
    - `Resume latest` → skip already completed regions and continue where you stopped.
    - `Start fresh` → mark old sessions as interrupted and start a clean run.
  - Completed regions are skipped with clear messages (e.g. `EUNE already completed (3,020 matches)`).

- **Desktop notifications (Windows)**
  - Optional Windows toast + sound via `Notifier` (uses `winotify` + `winsound` when available).
  - Notifications on:
    - Region complete (`✓ Region Complete` with match count and duration).
    - All regions complete (`🏆 Scrape Complete` with total matches and total time).
    - Region errors (`⚠ Scrape Error` with summary).
  - Notification and sound toggles are available in the main menu under "Notifications settings".

---

## 🏛️ Architecture

Clean Architecture with strict layer separation — dependencies only point inward.

```
┌─────────────────────────────────────────────────────────┐
│  🖥️  Presentation (ScraperCLI)                          
├─────────────────────────────────────────────────────────┤
│  🔧  Application (Services / Use Cases)                 
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

**What you'll see:**
- 🎯 Startup banner with config summary
- 📡 Per-region progress: `Server → Next Server` with a live progress bar
- ✅ On completion: total matches collected, DB save notice, CSV export notice
- ▶️ Choosing `4) Scraping` starts scraping all servers automatically (sequential loop)
- 🩺 Choosing `2) Health check` opens API key / DNS / platform health tools
- 🔔 Choosing `5) Notifications settings` toggles toast/sound and sends a test notification
- 🎯 Choosing `6) Targeted scrape` runs a focused scrape for a single server, or from a chosen server onward

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
| `LOG_LEVEL` | Optional | `INFO` | `TRACE` / `DEBUG` / `INFO` / `SUCCESS` / `WARNING` / `ERROR` / `CRITICAL` |
| `DEBUG_TRACE` | Optional | `false` | Set `true` to enable `@traceable` function timing |
| `REGIONS` | Optional | — | Limit run to specific servers, e.g., `euw1,na1` |
| `DISABLED_REGIONS` | Optional | — | Comma-separated servers to skip |
| `RANDOM_SCRAPE` | Optional | `false` | Randomize per-region targets |
| `RANDOM_REGION_TARGET_MIN` | Optional | `25` | Minimum when `RANDOM_SCRAPE=true` |
| `RANDOM_REGION_TARGET_MAX` | Optional | `75` | Maximum when `RANDOM_SCRAPE=true` |
| `MAX_MATCHES_PER_CHUNK` | Optional | `50` | Per-iteration chunk size for smoother progress |
| `LOG_CONSOLE` | Optional | `false` | Enable console logging in addition to JSON files |
| `LOG_CONSOLE_LEVEL` | Optional | — | Console verbosity when enabled, e.g., `WARNING` or `ERROR` |

---

## 📊 Output Files

```
data/
├── db/
│   └── scraper.sqlite                  ← main database (matches + sessions metadata)
└── csv/
    ├── matches.csv                     ← match-level data
    ├── teams.csv                       ← team outcomes
    ├── participants.csv                ← player stats per match
    ├── participant_items.csv           ← items built
    ├── participant_summoner_spells.csv ← summoner spell choices
    ├── champions.csv                   ← champion reference table
    ├── items.csv                       ← item reference table
    ├── summoner_spells.csv             ← spell reference table
    └── platforms.csv                   ← platform reference table
```

The SQLite database also contains:

- `scrape_sessions` — one row per scrape run (status, regions, target, patch).
- `scrape_session_regions` — per-region progress for each session (pending/running/completed/skipped).

These tables drive the **resume** experience in the scraping CLI.

---

## 📋 Logging System

The logging system is built in `core/logging/` with **two output streams**:

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

## 🩺 Health Check

From the main menu choose `2) Health check` to open the health tools:

- **1) Check API key / status**
  - Calls `/lol/status/v4/platform-data` on a small set of core platforms.
  - Confirms whether `RIOT_API_KEY` is present and capable of returning `200` responses.
  - Summarises the result:
    - At least one `200` → key appears valid.
    - All `401` → key is invalid or expired.

- **2) Check Riot DNS**
  - Verifies DNS resolution for:
    - `api.riotgames.com`
    - `europe.api.riotgames.com`, `americas.api.riotgames.com`, `asia.api.riotgames.com`
    - `{platform}.api.riotgames.com` for each known platform (`euw1`, `eun1`, `na1`, …).
  - Helpful when some regions fail due to DNS issues on the host machine.

- **3) Check specific platforms**
  - Lets you pick one or more platforms by number (or `all`).
  - Performs DNS checks for `{platform}.api.riotgames.com` only on the selected platforms.

---

## 🔔 Notifications

From the main menu choose `5) Notifications settings`:

- Shows current status:
  - `Notifications` ON/OFF
  - `Sound` ON/OFF
- Options:
  - `1) Toggle notifications` — enable/disable desktop toasts.
  - `2) Toggle sound` — enable/disable sounds while keeping toasts.
  - `3) Test notification` — sends a real test toast + sound using the current settings.

Settings are stored in `data/notifications.json` and are respected by the `Notifier` used
by the scraping command for region-complete and all-complete events.

## 🗑️ Data Management

**Interactive CLI** — choose tables, confirm deletion:

```powershell
python -u .\delete_data.py
```

Prompts you to choose: delete all tables, or pick specific ones from a numbered list. Requires typing `yes` to confirm.

**Programmatic usage:**

```python
import sqlite3
from application.services.delete_data import DataDeleter

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

- Interactive CLI: [delete_data.py](./delete_data.py)
  - Run:

```powershell
python -u .\delete_data.py
```

  - Choose all or specific, view a numbered table list for specific, confirm with “yes”.

**`429 Too Many Requests`**
> Reduce `MAX_CONCURRENT_REQUESTS` and tune the per-endpoint rate limits in `config/settings.py`.

**DNS / Connection errors on some platforms**
> Provide `SEED_PUUIDS` or `SEED_SUMMONERS` to bypass initial discovery, or configure your system to use a public DNS (e.g., `8.8.8.8`).

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

[![Made by](https://img.shields.io/badge/Made_by-Darwish-C8963E?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MohamedDarwish) [![Riot API](https://img.shields.io/badge/Powered_by-Riot_Games_API-D32F2F?style=for-the-badge&logo=riotgames&logoColor=white)](https://developer.riotgames.com)

</div>
