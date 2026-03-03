"""Simple HTTP health checker for Riot API endpoints."""
from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import httpx


class ApiChecker:
    """Performs basic GET requests against Riot API hosts."""

    def __init__(self, timeout: float = 5.0, headers: Optional[Dict[str, str]] = None) -> None:
        self._timeout = timeout
        self._headers = headers or {}

    async def check(self, host: str, path: str) -> Tuple[bool, str, int]:
        """
        Check a single API endpoint.

        Returns:
            (success, message, latency_ms)
        """
        url = f"https://{host}.api.riotgames.com{path}"
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
                resp = await client.get(url)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if resp.status_code == 200:
                return True, "ok", elapsed_ms
            return False, f"status={resp.status_code}", elapsed_ms
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return False, str(exc), elapsed_ms

