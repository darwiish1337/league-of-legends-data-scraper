from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from core.logging.logger import StructuredLogger


TransientPredicate = Callable[[BaseException | None, Optional[int]], bool]
Supplier = Callable[[], Awaitable[Any]]


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int
    backoff_base_ms: int
    backoff_factor: float
    jitter_ms: int = 0

    @classmethod
    def from_env(cls) -> "RetryPolicy":
        """Create policy from environment variables."""
        import os

        def _int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except Exception:
                return default

        def _float(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, str(default)))
            except Exception:
                return default

        return cls(
            max_attempts=_int("HEALTH_RETRY_ATTEMPTS", 3),
            backoff_base_ms=_int("HEALTH_RETRY_BACKOFF_MS", 200),
            backoff_factor=_float("HEALTH_RETRY_FACTOR", 2.0),
            jitter_ms=_int("HEALTH_RETRY_JITTER_MS", 0),
        )

    async def run(
        self,
        supplier: Supplier,
        *,
        is_transient: TransientPredicate,
        logger: StructuredLogger,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an async supplier with retry on transient errors."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                if attempt == 1:
                    logger.debug(lambda: "retry-start", extra={"context": context or {}})
                result = await supplier()
                return result
            except Exception as e:
                transient = is_transient(e, None)
                logger.warning(
                    lambda: f"retry-attempt {attempt} {'transient' if transient else 'terminal'}",
                    extra={"context": {**(context or {}), "error": str(e)}},
                )
                if attempt >= self.max_attempts or not transient:
                    raise
                backoff_ms = int(self.backoff_base_ms * math.pow(self.backoff_factor, attempt - 1)) + self.jitter_ms
                await asyncio.sleep(backoff_ms / 1000.0)


class AdaptiveRetryPolicy(RetryPolicy):
    @classmethod
    def from_env(cls) -> "AdaptiveRetryPolicy":
        import os
        def _int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except Exception:
                return default
        def _float(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, str(default)))
            except Exception:
                return default
        return cls(
            max_attempts=_int("HEALTH_RETRY_ATTEMPTS", 4),
            backoff_base_ms=_int("HEALTH_RETRY_BACKOFF_MS", 200),
            backoff_factor=_float("HEALTH_RETRY_FACTOR", 2.0),
            jitter_ms=_int("HEALTH_RETRY_JITTER_MS", 50),
        )

    async def run(
        self,
        supplier: Supplier,
        *,
        is_transient: TransientPredicate,
        logger: StructuredLogger,
        context: dict[str, Any] | None = None,
    ) -> Any:
        attempt = 1
        backoff_ms = self.backoff_base_ms
        while attempt <= self.max_attempts:
            try:
                if attempt == 1:
                    logger.debug(lambda: "adaptive-retry-start", extra={"context": context or {}})
                return await supplier()
            except Exception as e:
                transient = is_transient(e, None)
                if attempt >= self.max_attempts or not transient:
                    raise
                extra = {"context": {**(context or {}), "error": str(e), "attempt": attempt}}
                logger.warning(lambda: "adaptive-retry-attempt", extra=extra)
                if hasattr(e, "status_code"):
                    sc = getattr(e, "status_code")
                    if sc == 429:
                        ra = getattr(e, "retry_after_ms", None)
                        if isinstance(ra, int) and ra > 0:
                            backoff_ms = max(backoff_ms, ra)
                        else:
                            backoff_ms = int(backoff_ms * 1.5)
                    elif 500 <= sc < 600:
                        backoff_ms = int(backoff_ms * self.backoff_factor)
                elif isinstance(e, Exception):
                    backoff_ms = int(backoff_ms * self.backoff_factor)
                await asyncio.sleep(backoff_ms / 1000.0)
                attempt += 1
