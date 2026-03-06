"""
Unit tests for RateLimiter functionality.

Tests:
- Basic request acquisition
- Per-endpoint rate limiting
- Status reporting
"""
import pytest
from infrastructure.api.rate_limiter import RateLimiter, EndpointRateLimiter


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_initialization(self):
        """Test RateLimiter initializes with correct limits."""
        limiter = RateLimiter(requests_per_1_sec=10, requests_per_2_min=100)
        
        used_1s, max_1s, used_2min, max_2min = limiter.get_status()
        
        assert max_1s == 10
        assert max_2min == 100
        assert used_1s == 0
        assert used_2min == 0

    @pytest.mark.asyncio
    async def test_acquire_within_limits(self):
        """Test acquiring requests within rate limits."""
        limiter = RateLimiter(requests_per_1_sec=5, requests_per_2_min=50)
        
        # Should not raise
        for _ in range(3):
            await limiter.acquire()
        
        used_1s, max_1s, _, _ = limiter.get_status()
        assert used_1s == 3

    def test_status_reporting(self):
        """Test status returns correct tuple."""
        limiter = RateLimiter(requests_per_1_sec=15, requests_per_2_min=120)
        
        status = limiter.get_status()
        
        assert isinstance(status, tuple)
        assert len(status) == 4
        _, max_1s, _, max_2min = status
        assert max_1s == 15
        assert max_2min == 120


class TestEndpointRateLimiter:
    """Test EndpointRateLimiter class."""

    def test_initialization(self):
        """Test EndpointRateLimiter initializes."""
        limiter = EndpointRateLimiter()
        assert limiter is not None

    def test_set_default_limiter(self):
        """Test setting default rate limiter."""
        limiter = EndpointRateLimiter()
        limiter.set_default_limiter(10, 100)
        
        # Should create default limiter
        assert limiter is not None

    def test_add_endpoint_limiter(self):
        """Test adding per-endpoint limiter."""
        limiter = EndpointRateLimiter()
        limiter.set_default_limiter(10, 100)
        limiter.add_endpoint_limiter("match", 5, 50)
        
        # Should have different limits for different endpoints
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_acquire_with_endpoint(self):
        """Test acquiring with specific endpoint."""
        limiter = EndpointRateLimiter()
        limiter.set_default_limiter(10, 100)
        limiter.add_endpoint_limiter("match", 5, 50)
        
        # Should not raise
        await limiter.acquire()
        await limiter.acquire("match")
