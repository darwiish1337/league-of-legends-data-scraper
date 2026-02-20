from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.logging.config import bootstrap_logging, shutdown_logging
from config import settings
from presentation.cli import DBCheckCommand
import argparse


def main() -> int:
    bootstrap_logging(service="db", level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, log_file_name="db.jsonl")
    try:
        parser = argparse.ArgumentParser(description="Database health/inspection")
        parser.add_argument("--list", action="store_true", help="List tables")
        parser.add_argument("--count", action="store_true", help="Count rows per table")
        parser.add_argument("--integrity", action="store_true", help="Run PRAGMA integrity_check")
        args = parser.parse_args()
        cmd = DBCheckCommand()
        if args.list or args.count or args.integrity:
            if args.list:
                cmd._list_tables()
            if args.count:
                cmd._count_rows()
            if args.integrity:
                cmd._integrity()
        else:
            cmd.run()
        return 0
    finally:
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main())
