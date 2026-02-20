from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from core.logging.logger import StructuredLogger
from .models import HTTPCheckResult
from .retry_policy import RetryPolicy, AdaptiveRetryPolicy
from .timeout_config import TimeoutConfig
from .circuit_breaker import CircuitBreaker


class HTTPChecker:
    def __init__(
        self,
        timeout: TimeoutConfig,
        retry: RetryPolicy,
        logger: StructuredLogger,
        headers: Optional[Dict[str, str]] = None,
        circuit: Optional[CircuitBreaker] = None,
    ) -> None:
        self.timeout = timeout
        self.retry = retry
        self.logger = logger
        self.headers = headers or {}
        self.circuit = circuit

    async def check(self, url: str, *, method: str = "GET") -> HTTPCheckResult:
        self.logger.info(lambda: "http-check-start", extra={"host": self._host_from_url(url), "platform": self._host_from_url(url)})
        host = self._host_from_url(url)
        if self.circuit and not self.circuit.allow(host):
            return HTTPCheckResult(
                host=host,
                url=url,
                success=False,
                error="circuit-open",
            )

        def is_transient(exc: BaseException | None, status: Optional[int]) -> bool:
            if isinstance(exc, httpx.TimeoutException):
                return True
            if isinstance(exc, httpx.NetworkError):
                return True
            if hasattr(exc, "status_code"):
                sc = getattr(exc, "status_code")
                if sc == 429:
                    return True
                if isinstance(sc, int) and 500 <= sc < 600:
                    return True
            if status and 500 <= status < 600:
                return True
            return False

        class TransientHTTPError(Exception):
            def __init__(self, status_code: int, retry_after_ms: Optional[int] = None) -> None:
                super().__init__(f"http {status_code}")
                self.status_code = status_code
                self.retry_after_ms = retry_after_ms

        async def _request() -> HTTPCheckResult:
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(
                    headers=self.headers,
                    timeout=httpx.Timeout(
                        connect=self.timeout.http_connect_timeout_ms / 1000.0,
                        read=self.timeout.http_read_timeout_ms / 1000.0,
                        write=self.timeout.http_read_timeout_ms / 1000.0,
                        pool=self.timeout.http_total_timeout_ms / 1000.0,
                    ),
                    http2=False,
                ) as client:
                    resp = await client.request(method, url)
                    dur_ms = int((time.perf_counter() - start) * 1000.0)
                    status = resp.status_code
                    rate_limited = status == 429 or "Retry-After" in resp.headers
                    degraded = dur_ms >= self.timeout.http_degraded_ms
                    ok = 200 <= status < 300
                    if not ok and (status == 429 or 500 <= status < 600):
                        ra = None
                        try:
                            ra_val = resp.headers.get("Retry-After")
                            if ra_val:
                                ra = int(float(ra_val) * 1000)
                        except Exception:
                            ra = None
                        raise TransientHTTPError(status, ra)
                    self.logger.success(
                        lambda: "http-check-ok" if ok else "http-check-not-ok",
                        extra={
                            "host": self._host_from_url(url),
                            "platform": self._host_from_url(url),
                            "latency": dur_ms,
                            "status": status,
                        },
                    )
                    return HTTPCheckResult(
                        host=self._host_from_url(url),
                        url=url,
                        success=ok,
                        status_code=status,
                        response_time_ms=dur_ms,
                        rate_limited=rate_limited,
                        degraded=degraded,
                    )
            except Exception as e:
                dur_ms = int((time.perf_counter() - start) * 1000.0)
                self.logger.error(
                    lambda: "http-check-exception",
                    extra={
                        "host": self._host_from_url(url),
                        "platform": self._host_from_url(url),
                        "latency": dur_ms,
                        "error": str(e),
                    },
                )
                raise

        try:
            result: HTTPCheckResult = await self.retry.run(
                _request,
                is_transient=lambda exc, status: is_transient(exc, status),
                logger=self.logger,
                context={"url": url},
            )
            if self.circuit:
                if result.success:
                    self.circuit.record_success(host)
                else:
                    self.circuit.record_failure(host)
            return result
        except Exception as e:
            if self.circuit:
                self.circuit.record_failure(host)
            return HTTPCheckResult(
                host=self._host_from_url(url),
                url=url,
                success=False,
                error=str(e),
            )

    @staticmethod
    def _host_from_url(url: str) -> str:
        try:
            return httpx.URL(url).host
        except Exception:
            return "unknown"
