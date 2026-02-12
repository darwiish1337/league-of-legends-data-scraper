"""Application settings and configuration."""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from config/.env
ENV_PATH = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Configuration
    RIOT_API_KEY: str = os.getenv('RIOT_API_KEY', '')
    
    # Rate Limiting (per 10 seconds / per 10 minutes)
    RATE_LIMIT_PER_10_SEC: int = int(os.getenv('RATE_LIMIT_PER_10_SEC', '20'))
    RATE_LIMIT_PER_10_MIN: int = int(os.getenv('RATE_LIMIT_PER_10_MIN', '100'))
    
    # Patch Configuration
    TARGET_PATCH: str = os.getenv('TARGET_PATCH', '26.01')
    
    # Patch 26.01 dates (approximate)
    # Default window for current patch scraping
    PATCH_START_DATE: str = os.getenv('PATCH_START_DATE', '2026-02-01')
    PATCH_END_DATE: Optional[str] = os.getenv('PATCH_END_DATE', None)  # None = current
    
    # Data paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / 'data'
    DB_DIR: Path = DATA_DIR / 'db'
    CSV_DIR: Path = DATA_DIR / 'csv'
    LOG_DIR: Path = DATA_DIR / 'logs'
    
    # API endpoints
    RIOT_API_BASE: str = "https://{platform}.api.riotgames.com"
    RIOT_REGIONAL_BASE: str = "https://{region}.api.riotgames.com"
    
    # Request configuration
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF: float = float(os.getenv('RETRY_BACKOFF', '2.0'))
    
    # Concurrent requests
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv('MAX_CONCURRENT_REQUESTS', '10'))
    
    # Match scraping
    MATCHES_PER_SUMMONER: int = int(os.getenv('MATCHES_PER_SUMMONER', '100'))
    ENRICH_RANKS: bool = os.getenv('ENRICH_RANKS', '0') in ('1', 'true', 'True')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
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
