from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from queue import Queue
from pathlib import Path
from typing import Optional

from .levels import register_levels, to_level
from .formatter import ConsoleFormatter, JSONFormatter

_listener: QueueListener | None = None


def bootstrap_logging(
    *,
    service: str = "app",
    level: str | int | None = None,
    log_dir: Optional[Path] = None,
    log_file_name: str = "app.log",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> None:
    global _listener
    try:
        register_levels()
        root = logging.getLogger()
        root.handlers.clear()
        lvl = to_level(level or os.getenv("LOG_LEVEL", "INFO"))
        root.setLevel(lvl)

        enable_console = os.getenv("LOG_CONSOLE", "false").strip().lower() == "true"
        console_level_str = os.getenv("LOG_CONSOLE_LEVEL", "")
        if enable_console:
            console = logging.StreamHandler()
            console_level = to_level(console_level_str) if console_level_str else lvl
            console.setLevel(console_level)
            console.setFormatter(ConsoleFormatter())
            root.addHandler(console)

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            json_handler = RotatingFileHandler(str(log_dir / log_file_name), maxBytes=max_bytes, backupCount=backup_count)
            json_handler.setLevel(lvl)
            json_handler.setFormatter(JSONFormatter())
            q: Queue[logging.LogRecord] = Queue(-1)
            qh = QueueHandler(q)
            root.addHandler(qh)
            _listener = QueueListener(q, json_handler, respect_handler_level=True)
            _listener.daemon = True
            _listener.start()

        logging.LoggerAdapter(logging.getLogger(), extra={"service": service})
    except Exception:
        try:
            logging.basicConfig(level=logging.INFO)
        except Exception:
            pass


def shutdown_logging() -> None:
    global _listener
    try:
        if _listener:
            _listener.stop()
            _listener = None
    except Exception:
        pass
