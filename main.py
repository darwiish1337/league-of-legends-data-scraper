import sys
from core.logging.config import bootstrap_logging, shutdown_logging
from config import settings
from presentation.cli import ScrapingCommand, HealthCommand, DeleteDataCommand, DBCheckCommand


def _menu() -> None:
    while True:
        print("\n=== Main Menu ===")
        print("1) Delete data")
        print("2) Health check")
        print("3) DB check")
        print("4) Scraping")
        print("5) Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            DeleteDataCommand().run()
        elif choice == "2":
            import asyncio
            asyncio.run(HealthCommand().run_interactive())
        elif choice == "3":
            DBCheckCommand().run()
        elif choice == "4":
            import asyncio
            asyncio.run(ScrapingCommand().run())
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


def main(argv: list[str]) -> int:
    bootstrap_logging(service="scraper", level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, log_file_name="scraper.jsonl")
    try:
        _menu()
        return 0
    finally:
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
