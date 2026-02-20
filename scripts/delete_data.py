from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.logging.config import bootstrap_logging, shutdown_logging
from config import settings
from presentation.cli import DeleteDataCommand


def main() -> int:
    bootstrap_logging(service="delete", level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, log_file_name="delete.jsonl")
    try:
        DeleteDataCommand().run()
        return 0
    finally:
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main())
