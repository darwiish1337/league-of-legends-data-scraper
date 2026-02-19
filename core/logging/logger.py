from __future__ import annotations

import functools
import logging
import os
import time
from typing import Any, Callable, Dict, Optional, Protocol

from .context import bind as bind_ctx, get_context
from .levels import LogLevel


class SupportsStr(Protocol):
    def __str__(self) -> str: ...


class StructuredLogger:
    def __init__(self, logger: logging.Logger, service: Optional[str] = None) -> None:
        self._logger = logger
        self._service = service

    def bind(self, **values: Any) -> "StructuredLogger":
        bind_ctx(**values)
        return self

    def _log(self, level: int, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        if not self._logger.isEnabledFor(level):
            return
        try:
            message = msg() if callable(msg) else msg
        except Exception:
            message = "<lazy message failed>"
        extra = kwargs.pop("extra", {})
        if self._service and "service" not in extra:
            extra["service"] = self._service
        try:
            self._logger.log(level, str(message), *args, extra=extra, **kwargs)
        except Exception:
            try:
                self._logger.log(level, "log failed", *args)
            except Exception:
                pass

    def trace(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(int(LogLevel.TRACE), msg, *args, **kwargs)

    def debug(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, *args, **kwargs)

    def success(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(int(LogLevel.SUCCESS), msg, *args, **kwargs)

    def warning(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: SupportsStr | Callable[[], SupportsStr], *args: Any, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, msg, *args, **kwargs)


def get_logger(name: str, *, service: Optional[str] = None) -> StructuredLogger:
    logger = logging.getLogger(name)
    return StructuredLogger(logger, service=service)


def traceable(fn: Callable[..., Any]) -> Callable[..., Any]:
    debug_trace = os.getenv("DEBUG_TRACE", "").lower() == "true"
    if not debug_trace:
        return fn

    logger = get_logger(fn.__module__, service="trace")

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        logger.trace(lambda: f"enter {fn.__qualname__}")
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(lambda: f"exception in {fn.__qualname__}: {e}")
            raise
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            logger.trace(lambda: f"exit {fn.__qualname__}", extra={"execution_time_ms": round(dur_ms, 2)})

    return wrapper

