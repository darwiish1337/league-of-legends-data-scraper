from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class DNSCheckResult:
    """DNS check outcome."""
    host: str
    success: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HTTPCheckResult:
    """HTTP check outcome."""
    host: str
    url: str
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    rate_limited: bool = False
    degraded: bool = False
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HealthReport:
    """Aggregated health report for a platform host."""
    host: str
    dns: DNSCheckResult
    http: Optional[HTTPCheckResult]
    healthy: bool
    cause: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

