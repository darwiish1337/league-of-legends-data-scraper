import asyncio
from presentation.cli import ScraperCLI
from core.logging.config import bootstrap_logging, shutdown_logging
from config import settings

async def _run_scraper():
    cli = ScraperCLI()
    await cli.run()

if __name__ == "__main__":
    asyncio.run(_run_scraper())
if __name__ == "__main__":
    bootstrap_logging(service="scraper", level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, log_file_name="scraper.jsonl")
    try:
        asyncio.run(_run_scraper())
    finally:
        shutdown_logging()
