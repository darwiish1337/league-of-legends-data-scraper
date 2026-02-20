from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class TimeoutConfig:
    """Centralized timeout configuration with env overrides."""
    dns_timeout_ms: int
    http_connect_timeout_ms: int
    http_read_timeout_ms: int
    http_total_timeout_ms: int
    http_degraded_ms: int

    @classmethod
    def from_env(cls) -> "TimeoutConfig":
        """Build TimeoutConfig from environment variables."""
        def _int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except Exception:
                return default

        return cls(
            dns_timeout_ms=_int("HEALTH_DNS_TIMEOUT_MS", 1000),
            http_connect_timeout_ms=_int("HEALTH_HTTP_CONNECT_TIMEOUT_MS", 1000),
            http_read_timeout_ms=_int("HEALTH_HTTP_READ_TIMEOUT_MS", 2000),
            http_total_timeout_ms=_int("HEALTH_HTTP_TOTAL_TIMEOUT_MS", 3000),
            http_degraded_ms=_int("HEALTH_HTTP_DEGRADED_MS", 500),
        )
