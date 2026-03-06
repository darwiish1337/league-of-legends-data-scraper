<div align="center">

# ⚔️ Riot LoL Ranked Data Scraper

**Production-grade data pipeline for League of Legends ranked matches**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Async](https://img.shields.io/badge/AsyncIO-Powered-FF6B6B?style=for-the-badge&logo=python&logoColor=white)](https://docs.python.org/3/library/asyncio.html)
[![Riot API](https://img.shields.io/badge/Riot_API-v4-D32F2F?style=for-the-badge&logo=riotgames&logoColor=white)](https://developer.riotgames.com)

[![Servers](https://img.shields.io/badge/Servers-EUW_→_ME1-C8963E?style=flat-square)]()
[![Queues](https://img.shields.io/badge/Queues-Solo/Duo_+_Flex-5865F2?style=flat-square)]()
[![Storage](https://img.shields.io/badge/Export-SQLite_+_CSV-4EC994?style=flat-square)]()
[![Logging](https://img.shields.io/badge/Logging-JSON_+_Console-38C6C6?style=flat-square)]()

*Scrapes Solo/Duo & Flex 5v5 ranked matches across all major servers with patch-aware filtering, async fetching, durable storage, and enterprise-grade logging.*

</div>

---

## 🗂️ Table of Contents

- [✨ Features](#-features)
- [📁 Project Structure](#-project-structure)
- [🏛️ Architecture](#-architecture)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#-configuration)
- [📊 Dataset](#-dataset)
- [📊 Output Files](#-output-files)
- [📋 Logging System](#-logging-system)
- [🩺 Health Check](#-health-check)
- [🔔 Notifications](#-notifications)
- [🗑️ Data Management](#-data-management)
- [🧪 Testing](#-testing)
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
| 🧠 **Smart Seeding** | High-elo leagues + DB seeds + optional `SEED_PUUIDS` / `SEED_SUMMONERS` |
| 🧬 **Rich Reference Data** | Champions with roles, items, and summoner spells from Data Dragon |
| 📋 **Enterprise Logging** | Colored console + structured JSON logs with context binding |
| 🩺 **Health Tools** | API key / DNS / platform health checks |
| 🔔 **Desktop Notifications** | Windows toast + sound on region/scrape complete or error |
| 🗑️ **Data Management** | Interactive CLI + programmatic table clearing |
| 🔁 **Session Resume** | Crash-safe — resume from exact region where you stopped |

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
│   │   ├── data_persistence_service.py
│   │   └── region_scrape_runner.py
│   └── use_cases/
│
├── 🖥️  presentation/cli/           # Console UI commands
│   ├── scraping_command.py         # Main scraping (supports resume)
│   ├── targeted_scrape_command.py  # Single-server / start-from scrape
│   ├── health_command.py
│   ├── notifications_command.py
│   ├── delete_data_command.py
│   └── db_check_command.py
│
├── 🧪 scripts/                     # Entrypoints
│   ├── scraping.py
│   ├── health.py
│   ├── delete_data.py
│   └── db_check.py
│
├── 📋 core/logging/                # Enterprise logging system
│   ├── config.py
│   ├── formatter.py
│   ├── levels.py                   # Custom TRACE & SUCCESS levels
│   ├── context.py
│   └── logger.py                   # StructuredLogger + @traceable
│
├── 💾 data/                        # Generated output (gitignored)
│   ├── db/scraper.sqlite
│   ├── csv/
│   └── logs/scraper.jsonl
│
└── 🚀 main.py
```

---

## 🏛️ Architecture

Clean Architecture — dependencies only point inward.

```
┌─────────────────────────────────────────────────────────┐
│  🖥️  Presentation (CLI)                                 │
├─────────────────────────────────────────────────────────┤
│  🔧  Application (Services / Use Cases)                 │
├────────────────────────┬────────────────────────────────┤
│  🧩  Domain            │  🏗️  Infrastructure            │
│  Entities / Enums      │  Riot Client / SQLite / CSV    │
└────────────────────────┴────────────────────────────────┘
           ↑ all layers share: 📋 core/logging
```

```
Config → Riot API → Domain Entities → Application Services → SQLite + CSV → CLI Output
```

---

## 🚀 Quick Start

**1 — Install dependencies**

```bash
pip install -r requirements.txt

# Optional: HTTP/2 support
pip install "httpx[http2]"
```

**2 — Create `.env`**

```bash
# config/.env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**3 — Run**

```powershell
# PowerShell
$env:TARGET_PATCH="16.3"; $env:MATCHES_PER_REGION="2500"
python -u .\main.py
```

```bash
# Bash / Linux / macOS
TARGET_PATCH="16.3" MATCHES_PER_REGION="2500" python -u main.py
```

**Menu options:**

| Option | Action |
|--------|--------|
| `4) Scraping` | Start full sequential scrape across all servers |
| `6) Targeted scrape` | Scrape a single server or start from a chosen server |
| `2) Health check` | Validate API key / DNS / platforms |
| `3) DB check` | Inspect table counts and integrity |
| `5) Notifications settings` | Toggle toast/sound, send test notification |

---

## ⚙️ Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `RIOT_API_KEY` | ✅ | — | Your Riot developer API key |
| `MATCHES_PER_REGION` | ⬜ | `1000` | Target matches per server |
| `MATCHES_TOTAL` | ⬜ | — | Global cap across all regions |
| `TARGET_PATCH` | ⬜ | — | Filter by patch — `16.3` or `16` |
| `SCRAPE_MODE` | ⬜ | `patch` | `patch` or `date` |
| `SCRAPE_DATE` | ⬜ | — | `YYYY-MM-DD` — used when `SCRAPE_MODE=date` |
| `PATCH_START_DATE` | ⬜ | — | Lower bound for patch date range |
| `PATCH_END_DATE` | ⬜ | — | Upper bound for patch date range |
| `MAX_CONCURRENT_REQUESTS` | ⬜ | `5` | Async concurrency limit |
| `SEED_PUUIDS` | ⬜ | — | Comma-separated PUUIDs to seed the player pool |
| `SEED_SUMMONERS` | ⬜ | — | Comma-separated summoner names as seeds |
| `LOG_LEVEL` | ⬜ | `INFO` | `TRACE` / `DEBUG` / `INFO` / `SUCCESS` / `WARNING` / `ERROR` |
| `DEBUG_TRACE` | ⬜ | `false` | Enable `@traceable` function timing |
| `REGIONS` | ⬜ | — | Limit to specific servers, e.g. `euw1,na1` |
| `DISABLED_REGIONS` | ⬜ | — | Servers to skip |
| `RANDOM_SCRAPE` | ⬜ | `false` | Randomize per-region targets |
| `MAX_MATCHES_PER_CHUNK` | ⬜ | `50` | Per-iteration chunk size |
| `LOG_CONSOLE` | ⬜ | `false` | Enable console logging in addition to JSON |

---

## 📊 Dataset

> The full scraped dataset is publicly available on Kaggle.

<div align="center">

[<img src="https://www.kaggle.com/static/images/site-logo.svg" width="140" alt="View Dataset on Kaggle"/>](https://www.kaggle.com/datasets/darwish1337/riot-lol-ranked-games-soloflex-patch-16-3)

</div>

The dataset includes ranked Solo/Duo and Flex 5v5 matches across all major servers, with full participant stats, item builds, champion roles, and match metadata — all patch-filtered and deduplicated.

---

## 📊 Output Files

```
data/
├── db/
│   └── scraper.sqlite                   ← main database
└── csv/
    ├── matches.csv                      ← match-level data
    ├── teams.csv                        ← team outcomes
    ├── participants.csv                 ← player stats per match
    ├── participant_items.csv            ← items built
    ├── participant_summoner_spells.csv  ← summoner spell choices
    ├── champions.csv                    ← champion reference
    ├── items.csv                        ← item reference
    ├── summoner_spells.csv              ← spell reference
    └── platforms.csv                    ← platform reference
```

The SQLite database also includes `scrape_sessions` and `scrape_session_regions` — used to power the **resume** experience.

---

## 📋 Logging System

| Stream | Format | Level |
|---|---|---|
| Console | Colored, human-readable | Configurable via `LOG_LEVEL` |
| File (`scraper.jsonl`) | Structured JSON | All levels |

**Custom levels:** `TRACE` and `SUCCESS` are added on top of Python's standard logging.

**Context binding:**

```python
from core.logging.logger import get_logger
from core.logging.context import context

log = get_logger(__name__).bind(request_id="abc123")

with context(region="euw1"):
    log.info("start processing")
    # → includes: region=euw1, request_id=abc123
```

**Function tracing** (enable with `DEBUG_TRACE=true`):

```python
@traceable
def compute(a: int, b: int) -> int:
    return a + b
# logs: entry, exit, and execution time automatically
```

---

## 🩺 Health Check

From the main menu → `2) Health check`:

| Option | What it does |
|--------|-------------|
| `1) Check API key` | Calls `/lol/status/v4/platform-data` on core platforms to validate your key |
| `2) Check Riot DNS` | Resolves `*.api.riotgames.com` for all known platforms |
| `3) Check specific platforms` | DNS check for selected platforms only |

---

## 🔔 Notifications

From the main menu → `5) Notifications settings`:

- Toggle desktop toasts (Windows) on/off
- Toggle sound on/off
- Send a live test notification

Fires automatically on: region complete, all regions complete, and scrape errors. Settings saved to `data/notifications.json`.

---

## 🗑️ Data Management

**Interactive CLI:**

```powershell
python -u .\scripts\delete_data.py
```

Choose all tables or pick specific ones. Requires typing `yes` to confirm.

**Programmatic:**

```python
from application.services.delete_data import DataDeleter

deleter = DataDeleter(lambda: sqlite3.connect("data/db/scraper.sqlite"))
deleter.clear_table("participants", confirm=True)
deleter.clear_all(confirm=True)
```

**DB inspection:**

```powershell
python -u .\scripts\db_check.py --list --count --integrity
```

---

## 🧪 Testing

87 tests, all passing — organized by component with full fixture isolation.

```bash
# Windows
$env:TESTING='true'; pytest tests/ -v

# macOS / Linux
TESTING=true pytest tests/ -v
```

> See [TEST_STRUCTURE.md](./TEST_STRUCTURE.md) for the full breakdown — unit, CLI, integration, and legacy test docs.

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| `401 Unauthorized` | Check `RIOT_API_KEY` in `config/.env` — key may be expired |
| `429 Too Many Requests` | Reduce `MAX_CONCURRENT_REQUESTS`, tune rate limits in `config/settings.py` |
| DNS errors on some platforms | Add `SEED_PUUIDS` / `SEED_SUMMONERS`, or switch to a public DNS (`8.8.8.8`) |
| No matches collected | Verify `TARGET_PATCH` and `PATCH_START_DATE` are set correctly |
| Windows Unicode errors in tests | Run with `$env:TESTING='true'` |

---

## 📄 License

For educational and data engineering purposes only.
Not affiliated with or endorsed by Riot Games.

---

<div align="center">

[![Made by](https://img.shields.io/badge/Made_by-Darwish-C8963E?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MohamedDarwish)
[![Riot API](https://img.shields.io/badge/Powered_by-Riot_Games_API-D32F2F?style=for-the-badge&logo=riotgames&logoColor=white)](https://developer.riotgames.com)

</div>
