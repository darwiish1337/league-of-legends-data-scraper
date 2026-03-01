"""Application settings and configuration."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    """
    ─── WHY THE OLD CODE WAS SLOW ────────────────────────────────────────
    1. PATCH_START_DATE = 2020-01-01
       → fetched 5 years of matches, discarded 98% (wrong patch)
       → wasted 40× the API quota

    2. RateLimiter used a 600-second window
       Riot's actual limit is 100 req / 120 seconds (2 minutes).
       After 95 requests the old limiter waited 10 minutes instead of 2.
       → 5× slower than it needed to be

    3. MAX_CONCURRENT_REQUESTS = 8, limits = 10/10s
       → very conservative, left most of the quota unused
    ──────────────────────────────────────────────────────────────────────
    """

    RIOT_API_KEY: str = os.getenv('RIOT_API_KEY', '')

    # ── Rate limits (per 1 second / per 2 minutes = Riot's actual windows) ──
    # Riot personal key hard limits: 20/s and 100/120s
    # We stay slightly below to avoid 429s.
    RATE_LIMIT_PER_1_SEC:           int = 18
    RATE_LIMIT_PER_2_MIN:           int = 90

    MATCH_RATE_LIMIT_PER_1_SEC:     int = 18
    MATCH_RATE_LIMIT_PER_2_MIN:     int = 90

    SUMMONER_RATE_LIMIT_PER_1_SEC:  int = 18
    SUMMONER_RATE_LIMIT_PER_2_MIN:  int = 85

    LEAGUE_RATE_LIMIT_PER_1_SEC:    int = 15
    LEAGUE_RATE_LIMIT_PER_2_MIN:    int = 75

    # ── Patch ─────────────────────────────────────────────────────────────
    TARGET_PATCH:     str = os.getenv('TARGET_PATCH',      '16.3')
    # Patch 16.3 released ~2026-02-05. MUST be set correctly or the scraper
    # downloads years of old matches and discards them all.
    PATCH_START_DATE: str = os.getenv('PATCH_START_DATE',  '2026-02-05')
    PATCH_END_DATE:   str = os.getenv('PATCH_END_DATE',    '')

    # ── Paths ──────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / 'data'
    DB_DIR:   Path = DATA_DIR / 'db'
    CSV_DIR:  Path = DATA_DIR / 'csv'
    LOG_DIR:  Path = DATA_DIR / 'logs'

    # ── HTTP ───────────────────────────────────────────────────────────────
    REQUEST_TIMEOUT: int   = 30
    MAX_RETRIES:     int   = 3
    RETRY_BACKOFF:   float = 2.0

    # ── Concurrency ────────────────────────────────────────────────────────
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv('MAX_CONCURRENT_REQUESTS', '16'))

    # ── Match scraping ─────────────────────────────────────────────────────
    MATCHES_PER_SUMMONER: int        = int(os.getenv('MATCHES_PER_SUMMONER', '20'))
    MATCHES_PER_REGION:   int        = 3020
    MATCHES_TOTAL:        Optional[int] = int(os.getenv('MATCHES_TOTAL', '0')) or None

    # With a tight date window (2-3 weeks) most IDs will be on-patch.
    # 20 IDs per call is enough and avoids downloading stale matches.
    IDS_PER_PUUID: int = int(os.getenv('IDS_PER_PUUID', '20'))

    MAX_MATCHES_PER_CHUNK: int = int(os.getenv('MAX_MATCHES_PER_CHUNK', '200'))

    # ── Scraping mode ──────────────────────────────────────────────────────
    SCRAPE_MODE:    str           = 'patch'
    SCRAPE_DATE:    Optional[str] = None
    SEED_PUUIDS:    str           = ''
    SEED_SUMMONERS: str           = ''

    RANDOM_SCRAPE:            bool = os.getenv('RANDOM_SCRAPE', 'false').strip().lower() == 'true'
    RANDOM_REGION_TARGET_MIN: int  = int(os.getenv('RANDOM_REGION_TARGET_MIN', '25'))
    RANDOM_REGION_TARGET_MAX: int  = int(os.getenv('RANDOM_REGION_TARGET_MAX', '75'))

    DISABLED_REGIONS: set = set(
        r.strip().lower()
        for r in os.getenv('DISABLED_REGIONS', '').split(',')
        if r.strip()
    )

    LOG_LEVEL: str = 'INFO'

    @classmethod
    def validate(cls) -> None:
        if not cls.RIOT_API_KEY:
            raise ValueError("RIOT_API_KEY must be set in config/.env")

    @classmethod
    def create_directories(cls) -> None:
        cls.DB_DIR.mkdir(parents=True, exist_ok=True)
        cls.CSV_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()