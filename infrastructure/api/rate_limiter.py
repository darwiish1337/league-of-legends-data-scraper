"""Rate limiter matching Riot API's actual documented limits."""
import asyncio
import time
from collections import deque
from typing import Deque, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding-window rate limiter with two windows:
      - Short  : N requests per 1 second
      - Long   : N requests per 120 seconds  ← Riot's ACTUAL 2-min window
                 (NOT 600s — using 600s causes 10-min stalls!)
    """

    def __init__(
        self,
        requests_per_1_sec: int  = 18,
        requests_per_2_min: int  = 90,
    ):
        self.requests_per_1_sec = requests_per_1_sec
        self.requests_per_2_min = requests_per_2_min

        self._times_1s:   Deque[float] = deque()
        self._times_2min: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()

                # clean 1-second window
                while self._times_1s and now - self._times_1s[0] > 1.0:
                    self._times_1s.popleft()

                # clean 120-second window
                while self._times_2min and now - self._times_2min[0] > 120.0:
                    self._times_2min.popleft()

                ok_1s   = len(self._times_1s)   < self.requests_per_1_sec
                ok_2min = len(self._times_2min) < self.requests_per_2_min

                if ok_1s and ok_2min:
                    self._times_1s.append(now)
                    self._times_2min.append(now)
                    return

                wait = 0.05
                if not ok_1s and self._times_1s:
                    wait = max(wait, 1.0   - (now - self._times_1s[0])   + 0.01)
                if not ok_2min and self._times_2min:
                    wait = max(wait, 120.0 - (now - self._times_2min[0]) + 0.01)

                logger.debug(f"Rate limit — waiting {wait:.2f}s")
                await asyncio.sleep(wait)

    def get_status(self) -> Tuple[int, int, int, int]:
        now = time.monotonic()
        used_1s   = sum(1 for t in self._times_1s   if now - t <= 1.0)
        used_2min = sum(1 for t in self._times_2min if now - t <= 120.0)
        return used_1s, self.requests_per_1_sec, used_2min, self.requests_per_2_min

    async def reset(self) -> None:
        async with self._lock:
            self._times_1s.clear()
            self._times_2min.clear()


class EndpointRateLimiter:
    """Per-endpoint rate limiters with a shared default."""

    def __init__(self):
        self.limiters: dict[str, RateLimiter] = {}
        self._default: RateLimiter | None = None

    def set_default_limiter(
        self,
        requests_per_1_sec: int = 18,
        requests_per_2_min: int = 90,
    ) -> None:
        self._default = RateLimiter(requests_per_1_sec, requests_per_2_min)

    def add_endpoint_limiter(
        self,
        endpoint: str,
        requests_per_1_sec: int,
        requests_per_2_min: int,
    ) -> None:
        self.limiters[endpoint] = RateLimiter(requests_per_1_sec, requests_per_2_min)

    async def acquire(self, endpoint: str = "default") -> None:
        limiter = self.limiters.get(endpoint, self._default)
        if limiter:
            await limiter.acquire()

    async def reset_endpoint(self, endpoint: str = "default") -> None:
        limiter = self.limiters.get(endpoint, self._default)
        if limiter:
            await limiter.reset()