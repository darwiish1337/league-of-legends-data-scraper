from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from .context import get_context

_LEVEL_COLORS = {
    "TRACE": "\033[90m",
    "DEBUG": "\033[37m",
    "INFO": "\033[36m",
    "SUCCESS": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET = "\033[0m"


def _record_metadata(record: logging.LogRecord) -> Dict[str, Any]:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
        "level": record.levelname,
        "service": getattr(record, "service", None),
        "module": record.module,
        "class": getattr(record, "classname", None),
        "function": record.funcName,
        "line_number": record.lineno,
        "thread_id": record.thread,
        "process_id": record.process,
    }


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            md = _record_metadata(record)
            ctx = get_context()
            msg = record.getMessage()
            lvl = record.levelname
            color = _LEVEL_COLORS.get(lvl, "")
            parts = [
                f"{md['timestamp']}",
                f"{lvl}",
                f"{md['service'] or '-'}",
                f"{md['module']}:{md['function']}:{md['line_number']}",
                msg,
            ]
            exec_ms = getattr(record, "execution_time_ms", None)
            if exec_ms is not None:
                parts.append(f"t={exec_ms}ms")
            if ctx:
                parts.append(f"{ctx}")
            if record.exc_info:
                parts.append(self.formatException(record.exc_info))
            line = " | ".join(parts)
            return f"{color}{line}{_RESET}"
        except Exception:
            try:
                return record.getMessage()
            except Exception:
                return "<log format error>"


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            payload: Dict[str, Any] = _record_metadata(record)
            payload["message"] = record.getMessage()
            ctx = get_context()
            if ctx:
                payload["context"] = ctx
            exec_ms = getattr(record, "execution_time_ms", None)
            if exec_ms is not None:
                payload["execution_time_ms"] = exec_ms
            if record.exc_info:
                try:
                    payload["exception"] = self.formatException(record.exc_info)
                except Exception:
                    payload["exception"] = "unavailable"
            return json.dumps(payload, default=str, separators=(",", ":"))
        except Exception:
            return json.dumps({"message": "log format error"}, separators=(",", ":"))

