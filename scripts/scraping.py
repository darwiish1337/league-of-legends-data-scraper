from __future__ import annotations

import asyncio

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.logging.config import bootstrap_logging, shutdown_logging
from config import settings
from presentation.cli import ScrapingCommand


def main() -> int:
    bootstrap_logging(service="scraper", level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, log_file_name="scraper.jsonl")
    try:
        asyncio.run(ScrapingCommand().run())
        return 0
    finally:
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main())
