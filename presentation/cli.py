"""Command-line interface for the riot data scraper."""
import asyncio
import logging
import sys
import os
from typing import List

from config import settings
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient
from application import ScrapeMatchesUseCase
from application.services.data_persistence_service import DataPersistenceService


class PerLoggerFileHandler(logging.Handler):
    def __init__(self, log_dir):
        super().__init__()
        self.log_dir = log_dir
        self._handlers = {}
        self._formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def emit(self, record):
        name = record.name or "root"
        file_key = name.replace(".", "_")
        handler = self._handlers.get(file_key)
        if handler is None:
            file_path = self.log_dir / f"{file_key}.log"
            handler = logging.FileHandler(file_path, encoding="utf-8")
            handler.setFormatter(self._formatter)
            self._handlers[file_key] = handler
        handler.emit(record)

    def close(self):
        for handler in self._handlers.values():
            handler.close()
        self._handlers.clear()
        super().close()


def setup_logging():
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL))
    for handler in list(root.handlers):
        root.removeHandler(handler)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    root.addHandler(PerLoggerFileHandler(settings.LOG_DIR))
    logging.getLogger("infrastructure.api.rate_limiter").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


setup_logging()

logger = logging.getLogger(__name__)


class CLI:
    """Command-line interface for the scraper."""
    
    @staticmethod
    def print_banner():
        """Print application banner."""
        print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    RIOT GAMES LOL DATA SCRAPER - PATCH 26.01             ║
║                                                           ║
║    Scraping ranked matches (Solo/Duo & Flex 5v5)        ║
║    Clean Architecture + OOP + SOLID Principles           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """)
    
    @staticmethod
    def select_regions() -> List[Region]:
        """Interactive region selection."""
        print("\nAvailable Regions:")
        print("-" * 60)
        
        regions = Region.all_regions()
        for i, region in enumerate(regions, 1):
            print(f"{i:2d}. {region.value:6s} - {region.regional_route}")
        
        print("\nOptions:")
        print("  a. All regions")
        print("  s. Select specific regions (comma-separated numbers)")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'a':
            return regions
        elif choice == 's':
            nums = input("Enter region numbers (e.g., 1,2,3): ").strip()
            try:
                indices = [int(n.strip()) - 1 for n in nums.split(',')]
                selected = [regions[i] for i in indices if 0 <= i < len(regions)]
                return selected if selected else [regions[0]]
            except:
                print("Invalid input. Using EUW1 as default.")
                return [Region.EUW1]
        else:
            return [Region.EUW1]
    
    @staticmethod
    def select_queue_types() -> List[QueueType]:
        """Interactive queue type selection."""
        print("\nQueue Types:")
        print("-" * 60)
        print("1. Ranked Solo/Duo (420)")
        print("2. Ranked Flex 5v5 (440)")
        print("3. Both")
        
        choice = input("\nYour choice [1-3]: ").strip()
        
        if choice == '1':
            return [QueueType.RANKED_SOLO_5x5]
        elif choice == '2':
            return [QueueType.RANKED_FLEX_SR]
        else:
            return QueueType.ranked_queues()
    
    @staticmethod
    def get_matches_per_region() -> int:
        """Get number of matches to scrape per region."""
        print("\nMatches per Region:")
        print("-" * 60)
        
        try:
            count = int(input("Enter number of matches per region [500]: ").strip() or "500")
            return max(100, min(count, 5000))  # Limit between 100 and 5000
        except:
            return 500
    
    @staticmethod
    async def run():
        """Run the CLI application."""
        CLI.print_banner()
        
        # Validate settings
        try:
            settings.validate()
            settings.create_directories()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            print(f"\n❌ Error: {e}")
            print("\nPlease set RIOT_API_KEY in your .env file")
            return
        
        non_interactive = os.getenv("NON_INTERACTIVE", "").strip().lower() in ("1", "true", "yes", "y")
        
        if non_interactive:
            regions_env = os.getenv("REGIONS", "euw1")
            if regions_env.lower() == "all":
                regions = Region.all_regions()
            else:
                codes = [c.strip().lower() for c in regions_env.split(",")]
                all_regions = {r.value: r for r in Region.all_regions()}
                regions = [all_regions[c] for c in codes if c in all_regions] or [Region.EUW1]
            
            queue_env = os.getenv("QUEUE_TYPES", "both").strip().lower()
            if queue_env == "solo":
                queue_types = [QueueType.RANKED_SOLO_5x5]
            elif queue_env == "flex":
                queue_types = [QueueType.RANKED_FLEX_SR]
            else:
                queue_types = QueueType.ranked_queues()
            
            try:
                matches_per_region = int(os.getenv("MATCHES_PER_REGION", "100"))
            except:
                matches_per_region = 100
        else:
            print("\nLet's configure your scraping task...")
            regions = CLI.select_regions()
            queue_types = CLI.select_queue_types()
            matches_per_region = CLI.get_matches_per_region()
        
        # Confirm
        print("\n" + "="*60)
        print("CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Regions: {', '.join(r.value for r in regions)}")
        print(f"Queue Types: {', '.join(q.queue_name for q in queue_types)}")
        print(f"Matches per Region: {matches_per_region}")
        print(f"Total Expected Matches: ~{len(regions) * len(queue_types) * matches_per_region}")
        print(f"Patch Version: {settings.TARGET_PATCH}")
        print("="*60)
        
        if non_interactive:
            confirm = "y"
        else:
            confirm = input("\nProceed with scraping? [Y/n]: ").strip().lower()
            if confirm and confirm != 'y':
                print("Cancelled.")
                return
        
        # Start scraping
        total_target = len(regions) * len(queue_types) * matches_per_region
        current_progress = 0
        last_status = None
        
        def update_progress(current, target):
            nonlocal current_progress
            current_progress = current
            width = 30
            filled = int(width * (current / target)) if target else 0
            bar = "█" * filled + "-" * (width - filled)
            status_text = f"Endpoint {last_status} OK" if last_status else "Endpoint --"
            print(f"\rStart Scraping Data |{bar}| {current}/{target} Total in DB {current} {status_text}", end="", flush=True)
        
        def update_status(code):
            nonlocal last_status
            last_status = code
        
        print("\n🚀 Starting data collection...\n")
        
        async with RiotAPIClient(settings.RIOT_API_KEY) as api_client:
            # Scrape matches
            scrape_use_case = ScrapeMatchesUseCase(api_client, progress_callback=update_progress, status_callback=update_status)
            
            results = await scrape_use_case.execute(
                regions=regions,
                queue_types=queue_types,
                matches_per_region=matches_per_region
            )
            if total_target:
                update_progress(current_progress, total_target)
            print("")
            
            # Collect all matches
            all_matches = []
            for region_data in results.values():
                for matches in region_data.values():
                    all_matches.extend(matches)
            
            print(f"\n✅ Data collection complete! Collected {len(all_matches)} matches")
            
            # Persist and export
            if all_matches:
                print("\n💾 Saving matches to database...")
                db_path = settings.DB_DIR / "scraper.sqlite"
                persistence = DataPersistenceService(db_path)
                try:
                    persistence.reset_db()
                except:
                    pass
                # Seed static data (champions, items with names, summoner spells)
                try:
                    persistence.seed_static_data()
                except:
                    pass
                try:
                    for p in settings.CSV_DIR.glob("*.csv"):
                        p.unlink(missing_ok=True)
                except:
                    pass
                persistence.save_raw_matches(all_matches)
                print("📤 Exporting tables to CSV...")
                persistence.export_tables_csv(settings.CSV_DIR)
                
                print("\n✅ All done! Check the 'data/db' and 'data/csv' directories for results.")
            else:
                print("\n⚠️  No matches collected. Please check your API key and try again.")


def main():
    """Main entry point."""
    try:
        asyncio.run(CLI.run())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
