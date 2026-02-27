"""Rate limiter for Riot API requests."""
import asyncio
import time
from collections import deque
from typing import Deque, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with multiple time windows.
    Handles Riot API rate limits (per 10 seconds and per 10 minutes).
    """
    
    def __init__(
        self, 
        requests_per_10_sec: int = 20,
        requests_per_10_min: int = 100
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_10_sec: Maximum requests allowed per 10 seconds
            requests_per_10_min: Maximum requests allowed per 10 minutes (600 seconds)
        """
        self.requests_per_10_sec = requests_per_10_sec
        self.requests_per_10_min = requests_per_10_min
        
        # Track request timestamps
        self.request_times_10_sec: Deque[float] = deque()
        self.request_times_10_min: Deque[float] = deque()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(
            f"RateLimiter initialized: "
            f"{requests_per_10_sec} req/10s, {requests_per_10_min} req/10min"
        )
    
    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Blocks until rate limit allows the request.
        """
        async with self._lock:
            while True:
                current_time = time.time()
                
                # Clean up old timestamps (10 seconds window)
                while (self.request_times_10_sec and 
                       current_time - self.request_times_10_sec[0] > 10):
                    self.request_times_10_sec.popleft()
                
                # Clean up old timestamps (10 minutes = 600 seconds window)
                while (self.request_times_10_min and 
                       current_time - self.request_times_10_min[0] > 600):
                    self.request_times_10_min.popleft()
                
                # Check if we can make a request
                can_request_10_sec = len(self.request_times_10_sec) < self.requests_per_10_sec
                can_request_10_min = len(self.request_times_10_min) < self.requests_per_10_min
                
                if can_request_10_sec and can_request_10_min:
                    # Record the request
                    self.request_times_10_sec.append(current_time)
                    self.request_times_10_min.append(current_time)
                    return
                
                # Calculate wait time
                wait_time = 0.1  # Default small wait
                
                if not can_request_10_sec and self.request_times_10_sec:
                    # Wait until oldest request in 10-sec window expires
                    wait_time_10_sec = 10 - (current_time - self.request_times_10_sec[0])
                    wait_time = max(wait_time, wait_time_10_sec)
                
                if not can_request_10_min and self.request_times_10_min:
                    # Wait until oldest request in 10-min window expires
                    wait_time_10_min = 600 - (current_time - self.request_times_10_min[0])
                    wait_time = max(wait_time, wait_time_10_min)
                
                logger.debug(f"Rate limit reached. Waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    def get_status(self) -> Tuple[int, int, int, int]:
        """
        Get current rate limiter status.
        
        Returns:
            Tuple of (used_10_sec, limit_10_sec, used_10_min, limit_10_min)
        """
        current_time = time.time()
        
        # Count requests in last 10 seconds
        used_10_sec = sum(
            1 for t in self.request_times_10_sec 
            if current_time - t <= 10
        )
        
        # Count requests in last 10 minutes
        used_10_min = sum(
            1 for t in self.request_times_10_min 
            if current_time - t <= 600
        )
        
        return (
            used_10_sec, 
            self.requests_per_10_sec,
            used_10_min, 
            self.requests_per_10_min
        )
    
    async def reset(self) -> None:
        """Reset the rate limiter (clear all tracked requests)."""
        async with self._lock:
            self.request_times_10_sec.clear()
            self.request_times_10_min.clear()
            logger.info("Rate limiter reset")


class EndpointRateLimiter:
    """
    Manages rate limiters for different API endpoints.
    Each endpoint may have different rate limits.
    """
    
    def __init__(self):
        """Initialize endpoint rate limiter manager."""
        self.limiters: dict[str, RateLimiter] = {}
        self._default_limiter: RateLimiter = None
    
    def set_default_limiter(
        self, 
        requests_per_10_sec: int = 20,
        requests_per_10_min: int = 100
    ) -> None:
        """Set default rate limiter for all endpoints."""
        self._default_limiter = RateLimiter(
            requests_per_10_sec=requests_per_10_sec,
            requests_per_10_min=requests_per_10_min
        )
    
    def add_endpoint_limiter(
        self,
        endpoint: str,
        requests_per_10_sec: int,
        requests_per_10_min: int
    ) -> None:
        """Add specific rate limiter for an endpoint."""
        self.limiters[endpoint] = RateLimiter(
            requests_per_10_sec=requests_per_10_sec,
            requests_per_10_min=requests_per_10_min
        )
        logger.info(f"Added rate limiter for endpoint: {endpoint}")
    
    async def acquire(self, endpoint: str = "default") -> None:
        """Acquire permission for an endpoint request."""
        limiter = self.limiters.get(endpoint, self._default_limiter)
        if limiter:
            await limiter.acquire()
    
    async def reset_endpoint(self, endpoint: str = "default") -> None:
        """Reset a specific endpoint limiter (clear tracked requests)."""
        limiter = self.limiters.get(endpoint, self._default_limiter)
        if limiter:
            await limiter.reset()
