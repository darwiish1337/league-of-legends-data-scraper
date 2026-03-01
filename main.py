"""Main CLI entry-point."""
from __future__ import annotations

import shutil
import sys

from core.logging.config import bootstrap_logging, shutdown_logging
from config import settings

_BRIGHT_GREEN = "\033[1;92m"
_CYAN = "\033[96m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _g(s: str) -> str:
    return f"{_BRIGHT_GREEN}{s}{_RESET}"


def _c(s: str) -> str:
    return f"{_CYAN}{s}{_RESET}"


_LOGO = r"""
  ██████╗ ██╗ ██████╗ ████████╗    ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗
  ██╔══██╗██║██╔═══██╗╚══██╔══╝    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
  ██████╔╝██║██║   ██║   ██║       ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
  ██╔══██╗██║██║   ██║   ██║       ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
  ██║  ██║██║╚██████╔╝   ██║       ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
  ╚═╝  ╚═╝╚═╝ ╚═════╝    ╚═╝       ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
"""


def _print_logo() -> None:
    cols = shutil.get_terminal_size(fallback=(100, 20)).columns
    div = "═" * min(cols, 96)
    print(_g(div))
    for line in _LOGO.splitlines():
        print(_g(line))
    print(_c("  League of Legends Ranked Match Data Collector"))
    print(_g(div))


def _menu() -> None:
    _print_logo()
    # Lazy imports here — avoids any circular-import risk at module level
    from presentation.cli import ScrapingCommand, HealthCommand, DeleteDataCommand, DBCheckCommand

    while True:
        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        print(f"\n{_g('═' * min(cols, 48))}")
        print(f"  {_BOLD}MAIN MENU{_RESET}")
        print(_g("═" * min(cols, 48)))
        print(f"  {_c('1')}  Delete data")
        print(f"  {_c('2')}  Health check")
        print(f"  {_c('3')}  DB check")
        print(f"  {_c('4')}  Scraping")
        print(f"  {_c('5')}  Exit")
        print(_g("─" * min(cols, 48)))
        choice = input("  Choose: ").strip()

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
            print(f"\n  {_g('Goodbye!')}\n")
            break
        else:
            print(f"  {_YELLOW}Invalid option.{_RESET}")


def main(argv: list[str]) -> int:
    bootstrap_logging(
        service="scraper",
        level=settings.LOG_LEVEL,
        log_dir=settings.LOG_DIR,
        log_file_name="scraper.jsonl",
    )
    try:
        _menu()
        return 0
    finally:
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))