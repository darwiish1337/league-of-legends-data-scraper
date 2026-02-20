from __future__ import annotations

import asyncio
import socket
import time
from typing import Optional

from core.logging.logger import StructuredLogger
from .models import DNSCheckResult
from .timeout_config import TimeoutConfig


class DNSChecker:
    """DNS health check strategy."""

    def __init__(self, timeout: TimeoutConfig, logger: StructuredLogger) -> None:
        """Initialize DNS checker with timeouts and injected logger."""
        self.timeout = timeout
        self.logger = logger

    async def check(self, host: str) -> DNSCheckResult:
        """Resolve a hostname and measure latency."""
        start = time.perf_counter()
        self.logger.info(lambda: "dns-check-start", extra={"host": host, "platform": host})
        try:
            async def _resolve() -> list[tuple]:
                return await asyncio.to_thread(socket.getaddrinfo, host, None)

            await asyncio.wait_for(_resolve(), timeout=self.timeout.dns_timeout_ms / 1000.0)
            latency_ms = int((time.perf_counter() - start) * 1000.0)
            self.logger.success(lambda: "dns-check-ok", extra={"host": host, "platform": host, "latency": latency_ms})
            return DNSCheckResult(host=host, success=True, latency_ms=latency_ms)
        except asyncio.TimeoutError as e:
            latency_ms = int((time.perf_counter() - start) * 1000.0)
            self.logger.error(lambda: "dns-timeout", extra={"host": host, "platform": host, "latency": latency_ms, "error": "timeout"})
            return DNSCheckResult(host=host, success=False, latency_ms=latency_ms, error="timeout")
        except socket.gaierror as e:
            latency_ms = int((time.perf_counter() - start) * 1000.0)
            err = "nxdomain" if getattr(e, "errno", None) in (socket.EAI_NONAME, ) else "gaierror"
            self.logger.error(lambda: "dns-error", extra={"host": host, "platform": host, "latency": latency_ms, "error": err})
            return DNSCheckResult(host=host, success=False, latency_ms=latency_ms, error=err)
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000.0)
            self.logger.error(lambda: "dns-exception", extra={"host": host, "platform": host, "latency": latency_ms, "error": str(e)})
            return DNSCheckResult(host=host, success=False, latency_ms=latency_ms, error=str(e))
