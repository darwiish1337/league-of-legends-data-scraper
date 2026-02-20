from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from core.logging.logger import StructuredLogger
from .dns_checker import DNSChecker
from .http_checker import HTTPChecker
from .models import DNSCheckResult, HTTPCheckResult, HealthReport


MetricsHook = Callable[[str, Dict[str, Any]], None]


@dataclass(slots=True)
class HealthCacheEntry:
    report: HealthReport
    expires_at: float


class HealthManager:
    """Orchestrates DNS and HTTP checks and produces health reports."""
    def __init__(
        self,
        dns_checker: DNSChecker,
        http_checker: HTTPChecker,
        logger: StructuredLogger,
        *,
        blacklist: Optional[set[str]] = None,
        metrics_hook: Optional[MetricsHook] = None,
        cache_ttl_s: Optional[int] = None,
        default_path: Optional[str] = None,
    ) -> None:
        """Initialize manager with strategies and options."""
        self.dns_checker = dns_checker
        self.http_checker = http_checker
        self.logger = logger
        self.blacklist = blacklist or set()
        self.metrics_hook = metrics_hook
        self.cache_ttl_s = cache_ttl_s if cache_ttl_s is not None else int(os.getenv("HEALTH_CACHE_TTL_S", "30"))
        self.default_path = default_path or os.getenv("HEALTH_PATH", "/lol/status/v4/platform-data")
        self._cache: Dict[str, HealthCacheEntry] = {}

    async def check_platform(self, host: str, *, path: Optional[str] = None) -> HealthReport:
        """Check a single platform host and return a HealthReport."""
        now = time.time()
        cached = self._cache.get(host)
        if cached and cached.expires_at > now:
            return cached.report

        if host in self.blacklist:
            report = HealthReport(host=host, dns=DNSCheckResult(host, False, None, "blacklisted"), http=None, healthy=False, cause="blacklisted")
            self._remember(host, report)
            return report

        dns = await self.dns_checker.check(f"{host}.api.riotgames.com")
        if not dns.success:
            report = HealthReport(host=host, dns=dns, http=None, healthy=False, cause=dns.error or "dns-failed")
            self._remember(host, report)
            self._metric("dns_failed", {"host": host, "error": dns.error, "latency_ms": dns.latency_ms})
            return report

        url = f"https://{host}.api.riotgames.com{path or self.default_path}"
        http = await self.http_checker.check(url)
        healthy = bool(http.success and not http.rate_limited)
        cause = None
        if not healthy:
            cause = http.error or f"status={http.status_code}"
        report = HealthReport(host=host, dns=dns, http=http, healthy=healthy, cause=cause)
        self._remember(host, report)
        self._metric("http_checked", {"host": host, "status": http.status_code, "latency_ms": http.response_time_ms, "rate_limited": http.rate_limited})
        return report

    async def check_many(self, hosts: Iterable[str], *, path: Optional[str] = None, fail_fast: bool = False) -> List[HealthReport]:
        """Check multiple hosts, optionally stopping on first failure."""
        results: List[HealthReport] = []
        for h in hosts:
            r = await self.check_platform(h, path=path)
            results.append(r)
            if fail_fast and not r.healthy:
                break
        return results

    async def first_healthy(self, hosts: Iterable[str], *, path: Optional[str] = None) -> Optional[HealthReport]:
        """Return the first healthy host in the sequence, if any."""
        for h in hosts:
            r = await self.check_platform(h, path=path)
            if r.healthy:
                return r
        return None

    def _remember(self, host: str, report: HealthReport) -> None:
        self._cache[host] = HealthCacheEntry(report=report, expires_at=time.time() + self.cache_ttl_s)

    def _metric(self, name: str, payload: Dict[str, Any]) -> None:
        if self.metrics_hook:
            try:
                self.metrics_hook(name, payload)
            except Exception:
                pass
