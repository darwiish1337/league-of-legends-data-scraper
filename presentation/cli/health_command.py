from __future__ import annotations

import argparse
import json
import os
from typing import Iterable, List, Optional, Callable, Dict, Any

from core.logging.logger import get_logger, StructuredLogger
from domain.enums.region import Region
from application.services.health.timeout_config import TimeoutConfig
from application.services.health.retry_policy import AdaptiveRetryPolicy
from application.services.health.dns_checker import DNSChecker
from application.services.health.http_checker import HTTPChecker
from application.services.health.health_manager import HealthManager
from application.services.health.circuit_breaker import CircuitBreaker


def _parse_hosts_from_only(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip().lower() for v in value.split(",") if v.strip()]


def _sea_platforms() -> List[str]:
    return [r.platform_route for r in Region.all_regions() if r.regional_route == "sea"]


class HealthCommand:
    """Interactive health command with settings and optional metrics hook."""

    def __init__(self) -> None:
        self.logger: StructuredLogger = get_logger(__name__, service="health")
        self.timeout = TimeoutConfig.from_env()
        self.retry = AdaptiveRetryPolicy.from_env()
        self.headers: Dict[str, str] = {}
        api_key = os.getenv("RIOT_API_KEY", "")
        if api_key:
            self.headers["X-Riot-Token"] = api_key
        self.json_out: bool = False
        self.fail_fast: bool = False
        self.cache_ttl_s: int = int(os.getenv("HEALTH_CACHE_TTL_S", "30"))
        self.default_health_path: str = os.getenv("HEALTH_PATH", "/lol/status/v4/platform-data")
        self.metrics_enabled: bool = False

    def _metrics_hook(self) -> Optional[Callable[[str, Dict[str, Any]], None]]:
        if not self.metrics_enabled:
            return None
        def _hook(name: str, payload: Dict[str, Any]) -> None:
            self.logger.info(lambda: f"METRIC {name} {json.dumps(payload, separators=(',',':'))}")
        return _hook

    async def run_interactive(self) -> int:
        while True:
            print("\n=== Health Command ===")
            print("1) Check specific platforms")
            print(f"2) Toggle JSON output (currently: {'ON' if self.json_out else 'OFF'})")
            print(f"3) Toggle Fail-Fast (currently: {'ON' if self.fail_fast else 'OFF'})")
            print("4) Settings")
            print("5) Back")
            choice = input("Choose an option: ").strip()
            if choice == "1":
                chosen = self._choose_platforms_ui()
                if chosen:
                    await self._execute(["--only", ",".join(chosen)])
                else:
                    print("No platforms selected.")
            elif choice == "2":
                self.json_out = not self.json_out
                print(f"JSON output {'ENABLED' if self.json_out else 'DISABLED'}")
            elif choice == "3":
                self.fail_fast = not self.fail_fast
                print(f"Fail-Fast {'ENABLED' if self.fail_fast else 'DISABLED'}")
            elif choice == "4":
                self._settings_menu()
            elif choice == "5":
                return 0
            else:
                print("Invalid option.")
    
    def _choose_platforms_ui(self) -> List[str]:
        regions = Region.all_regions()
        rows = [(r.platform_route, r.friendly, r.regional_route) for r in regions]
        print("\nAvailable platforms:")
        for idx, (plat, friendly, regroute) in enumerate(rows, start=1):
            print(f"{idx:2d}) {plat:<4}  {friendly}  [{regroute}]")
        print("\nEnter numbers separated by commas (e.g., 1,3,10)")
        print("Type 'all' for all platforms, 'sea' for SEA only, or '0' to cancel.")
        sel = input("Select: ").strip().lower()
        if not sel or sel == "0":
            return []
        if sel == "all":
            return [plat for plat, _, _ in rows]
        if sel == "sea":
            return [plat for plat, _, regroute in rows if regroute == "sea"]
        chosen: List[str] = []
        parts = [p.strip() for p in sel.split(",") if p.strip()]
        for p in parts:
            try:
                i = int(p)
                if 1 <= i <= len(rows):
                    plat = rows[i - 1][0]
                    if plat not in chosen:
                        chosen.append(plat)
            except Exception:
                pass
        return chosen

    def _settings_menu(self) -> None:
        while True:
            print("\n--- Settings ---")
            print(f"1) Set health cache TTL (seconds) [current: {self.cache_ttl_s}]")
            print(f"2) Set default health path [current: {self.default_health_path}]")
            print(f"3) Toggle metrics hook (currently: {'ON' if self.metrics_enabled else 'OFF'})")
            print("4) Set circuit breaker failure threshold")
            print("5) Set circuit breaker reset window (seconds)")
            print("6) Back")
            s = input("Choose: ").strip()
            if s == "1":
                v = input("Enter TTL seconds: ").strip()
                try:
                    self.cache_ttl_s = max(0, int(v))
                    print(f"TTL set to {self.cache_ttl_s}")
                except Exception:
                    print("Invalid number.")
            elif s == "2":
                p = input("Enter health path (e.g., /lol/status/v4/platform-data): ").strip()
                if p.startswith("/"):
                    self.default_health_path = p
                    print(f"Path set to {self.default_health_path}")
                else:
                    print("Path must start with '/'.")
            elif s == "3":
                self.metrics_enabled = not self.metrics_enabled
                print(f"Metrics {'ENABLED' if self.metrics_enabled else 'DISABLED'}")
            elif s == "4":
                v = input("Enter circuit breaker failure threshold (>=1): ").strip()
                try:
                    self.breaker_threshold = max(1, int(v))
                    print(f"Breaker threshold set to {self.breaker_threshold}")
                except Exception:
                    print("Invalid number.")
            elif s == "5":
                v = input("Enter circuit breaker reset window seconds (>=1): ").strip()
                try:
                    self.breaker_reset_s = max(1, int(v))
                    print(f"Breaker reset window set to {self.breaker_reset_s}s")
                except Exception:
                    print("Invalid number.")
            elif s == "6":
                return
            else:
                print("Invalid option.")

    async def _execute(self, argv: List[str]) -> None:
        args_json = self.json_out or ("--json" in argv)
        args_fail_fast = self.fail_fast or ("--fail-fast" in argv)
        only_value = ""
        if "--only" in argv:
            idx = argv.index("--only")
            if idx + 1 < len(argv):
                only_value = argv[idx + 1]

        dns_checker = DNSChecker(timeout=self.timeout, logger=self.logger)
        if not hasattr(self, "breaker_threshold"):
            self.breaker_threshold = 3
        if not hasattr(self, "breaker_reset_s"):
            self.breaker_reset_s = 10
        http_checker = HTTPChecker(
            timeout=self.timeout,
            retry=self.retry,
            logger=self.logger,
            headers=self.headers,
            circuit=CircuitBreaker(failure_threshold=self.breaker_threshold, reset_timeout_s=self.breaker_reset_s),
        )
        disabled_env = os.getenv("DISABLED_REGIONS", "")
        blacklist = set([s.strip().lower() for s in disabled_env.split(",") if s.strip()])
        manager = HealthManager(
            dns_checker,
            http_checker,
            self.logger,
            blacklist=blacklist,
            metrics_hook=self._metrics_hook(),
            cache_ttl_s=self.cache_ttl_s,
            default_path=self.default_health_path,
        )

        candidates = _parse_hosts_from_only(only_value)
        if not candidates:
            print("No platforms provided. Please enter one or more platform codes.")
            return

        reports = await manager.check_many(candidates, fail_fast=args_fail_fast)
        if args_json:
            payload = [
                {
                    "host": r.host,
                    "healthy": r.healthy,
                    "cause": r.cause,
                    "dns": {
                        "success": r.dns.success,
                        "latency_ms": r.dns.latency_ms,
                        "error": r.dns.error,
                    },
                    "http": None
                    if not r.http
                    else {
                        "success": r.http.success,
                        "status_code": r.http.status_code,
                        "response_time_ms": r.http.response_time_ms,
                        "rate_limited": r.http.rate_limited,
                        "degraded": r.http.degraded,
                        "error": r.http.error,
                    },
                }
                for r in reports
            ]
            print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
        else:
            print("Results:")
            for r in reports:
                if r.healthy:
                    latency = r.http.response_time_ms if r.http else (r.dns.latency_ms or 0)
                    print(f"- {r.host}: healthy ({latency}ms)")
                else:
                    reason = r.cause or (r.http.error if (r.http and r.http.error) else "unhealthy")
                    print(f"- {r.host}: unhealthy ({reason})")


async def run(argv: Optional[Iterable[str]] = None) -> int:
    cmd = HealthCommand()
    await cmd._execute(list(argv or []))
    return 0
