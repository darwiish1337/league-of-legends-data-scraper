# Riot Games LoL Ranked Data Scraper

Production-ready scraper for League of Legends ranked matches (Solo/Duo and Flex 5v5). Collects data sequentially across all servers with a clean console UI, accurate per-server progress, and durable persistence.

## Features

- Multi-server sequential scrape (EUW → EUNE → … → ME1)
- Ranked Solo/Duo and Ranked Flex 5v5 (both collected per region)
- Per-region match targets (configurable per run)
- Patch-aware filtering (e.g., 16.3 or prefix like 16)
- Console UI with banner, summary, “Server”/“Next Server” headers and per-server progress bar
- Durable storage: SQLite database + CSV exports
- Endpoint-specific rate limits and async/concurrent fetching

## Project Layout

riot_data_scraper/
- config/ settings and environment
- domain/ entities, enums, interfaces
- infrastructure/ API client and repositories
- application/ services and use cases
- presentation/ CLI UI (ScraperCLI)
- data/ db (SQLite), csv exports, logs
- main.py minimal entry point

## First-Time Setup

- Python 3.10+
- Create config/.env and set RIOT_API_KEY
- Install dependencies:

```bash
pip install -r requirements.txt
```

## How to Run

- Set target patch and per-region target (examples below are Windows PowerShell):

```powershell
$env:TARGET_PATCH="16.3"
$env:MATCHES_PER_REGION="2500"
python -u .\main.py
```

- Console shows:
  - Banner: RIOT GAMES LOL RANKED GAMES DATA SCRAPER - PATCH <TARGET_PATCH>
  - Summary: Server, Queue Types, Patch Version
  - For each region:
    - Server: <friendly code, e.g., eune>
    - Next Server: <friendly next code>
    - Progress: Start Scraping Data |-----| 0/<target>
  - Completion per region with counts, DB save, and CSV export messages

## Output

- SQLite DB at data/db/scraper.sqlite
- CSVs at data/csv/:
  - matches.csv, teams.csv, participants.csv
  - participant_items.csv, participant_summoner_spells.csv
  - champions.csv, items.csv, summoner_spells.csv
- Logs at data/logs/ (when enabled by environment)

## Configuration

- Required:
  - RIOT_API_KEY in config/.env
- Common (via env or settings.py):
  - MATCHES_PER_REGION: per-server target count
  - MATCHES_TOTAL: optional global cap across all regions
  - TARGET_PATCH: exact (e.g., 16.3) or prefix (e.g., 16) for all 16.x
  - SCRAPE_MODE: “patch” (default) or “date” (requires SCRAPE_DATE=YYYY-MM-DD)
  - PATCH_START_DATE and PATCH_END_DATE: patch window bounds (used by “patch” mode)
  - MAX_CONCURRENT_REQUESTS and per-route limits
  - SEED_PUUIDS and SEED_SUMMONERS: optional bootstrap seeds (comma-separated)

## Architecture Notes

- Entry point: main.py delegates to a presentation-layer ScraperCLI for UI concerns.
- Domain:
  - Region exposes friendly labels and routing hosts used by the API client.
  - QueueType exposes numeric IDs and API queue names for league endpoints.
- Application:
  - ScrapeMatchesUseCase coordinates per-region scraping and progress reporting.
  - DataScraperService implements scraping and seed discovery with rate limiting.
- Infrastructure:
  - RiotAPIClient manages headers, retries, rate limits, and endpoint calls.
  - Repositories project API data into domain entities.
- Persistence:
  - DataPersistenceService maintains schema, writes DB rows, and exports CSVs.

## Troubleshooting

- Unauthorized (401): RIOT_API_KEY missing/invalid/expired; check config/.env and refresh your dev key.
- Rate Limited (429): lower MAX_CONCURRENT_REQUESTS or per-route quotas in settings.
- DNS errors (getaddrinfo failed): ensure *.api.riotgames.com resolves; try a public DNS (1.1.1.1/8.8.8.8) and flush DNS. Corporate/VPN networks may block some regional subdomains.
- No seeds found: provide SEED_PUUIDS or SEED_SUMMONERS in config/.env and retry.

## License

Educational and data engineering purposes.
