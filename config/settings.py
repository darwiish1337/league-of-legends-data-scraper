"""Application settings and configuration."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from config/.env (API key only)
ENV_PATH = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    """Application settings loaded from environment variables.
    
    Centralizes:
    - API key and request/timeout policies
    - Rate limiting per endpoint
    - Target patch/date windows
    - Data directories
    - Per-region collection targets and limits
    """

    # API Configuration
    RIOT_API_KEY: str = os.getenv('RIOT_API_KEY', '')
    
    # Rate Limiting (per 10 seconds / per 10 minutes)
    # These defaults are set slightly *below* the documented Riot limits
    # to avoid repeated 429 responses with long Retry-After pauses, which
    # slows scraping more than running a bit under the hard cap.
    RATE_LIMIT_PER_10_SEC: int = 10
    RATE_LIMIT_PER_10_MIN: int = 100
    MATCH_RATE_LIMIT_PER_10_SEC: int = 10
    MATCH_RATE_LIMIT_PER_10_MIN: int = 100
    SUMMONER_RATE_LIMIT_PER_10_SEC: int = 10
    SUMMONER_RATE_LIMIT_PER_10_MIN: int = 80
    LEAGUE_RATE_LIMIT_PER_10_SEC: int = 8
    LEAGUE_RATE_LIMIT_PER_10_MIN: int = 80
    
    # Patch Configuration
    TARGET_PATCH: str = os.getenv('TARGET_PATCH', '16.3')
    
    PATCH_START_DATE: str = os.getenv('PATCH_START_DATE', '2020-01-01')
    PATCH_END_DATE: str = os.getenv('PATCH_END_DATE', '')
    
    # Data paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / 'data'
    DB_DIR: Path = DATA_DIR / 'db'
    CSV_DIR: Path = DATA_DIR / 'csv'
    LOG_DIR: Path = DATA_DIR / 'logs'
    
    # Request configuration
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 2.0
    
    # Concurrent requests
    # This bound controls how many match-detail requests are in flight at once.
    # A slightly lower default keeps us under rate limits more reliably and
    # avoids 50–60s global stalls after 429 responses.
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv('MAX_CONCURRENT_REQUESTS', '8'))
    
    # Match scraping
    MATCHES_PER_SUMMONER: int = int(os.getenv('MATCHES_PER_SUMMONER', '100'))
    MATCHES_PER_REGION: int = 3020
    MATCHES_TOTAL: Optional[int] = int(os.getenv('MATCHES_TOTAL', '0')) or None
    IDS_PER_PUUID: int = 40
    MAX_MATCHES_PER_CHUNK: int = int(os.getenv('MAX_MATCHES_PER_CHUNK', '50'))
    

    # Scraping mode
    SCRAPE_MODE: str = 'patch'
    SCRAPE_DATE: Optional[str] = None
    SEED_PUUIDS: str = ''     # Optional comma-separated PUUIDs to bootstrap
    SEED_SUMMONERS: str = ''  # Optional comma-separated summoner names to bootstrap
    RANDOM_SCRAPE: bool = os.getenv('RANDOM_SCRAPE', 'false').strip().lower() == 'true'
    RANDOM_REGION_TARGET_MIN: int = int(os.getenv('RANDOM_REGION_TARGET_MIN', '25'))
    RANDOM_REGION_TARGET_MAX: int = int(os.getenv('RANDOM_REGION_TARGET_MAX', '75'))
    DISABLED_REGIONS: set[str] = set(
        r.strip().lower()
        for r in os.getenv('DISABLED_REGIONS', '').split(',')
        if r.strip()
    )
    
    # Logging
    LOG_LEVEL: str = 'INFO'  # Global log level for optional loggers
    
    @classmethod
    def validate(cls) -> None:
        """Validate required settings."""
        if not cls.RIOT_API_KEY:
            raise ValueError("RIOT_API_KEY must be set in environment variables or .env file")
    
    @classmethod
    def create_directories(cls) -> None:
        """Create necessary data directories."""
        cls.DB_DIR.mkdir(parents=True, exist_ok=True)
        cls.CSV_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)


# Create settings instance
settings = Settings()
