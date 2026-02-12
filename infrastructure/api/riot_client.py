"""Riot Games API client."""
import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx

from config import settings
from domain.enums import Region, QueueType
from .rate_limiter import EndpointRateLimiter

logger = logging.getLogger(__name__)


class RiotAPIClient:
    """Asynchronous client for Riot Games API."""
    
    def __init__(self, api_key: str):
        """
        Initialize Riot API client.
        
        Args:
            api_key: Riot Games API key
        """
        self.api_key = api_key
        self.session: Optional[httpx.AsyncClient] = None
        self.timeout = settings.REQUEST_TIMEOUT
        self.last_status_code: Optional[int] = None
        
        # Initialize rate limiter
        self.rate_limiter = EndpointRateLimiter()
        self.rate_limiter.set_default_limiter(
            requests_per_10_sec=settings.RATE_LIMIT_PER_10_SEC,
            requests_per_10_min=settings.RATE_LIMIT_PER_10_MIN
        )
        
        # Add specific endpoint rate limiters based on documentation
        self._setup_endpoint_limiters()
    
    def _setup_endpoint_limiters(self) -> None:
        """Setup rate limiters for specific endpoints."""
        self.rate_limiter.add_endpoint_limiter(
            "match",
            requests_per_10_sec=settings.RATE_LIMIT_PER_10_SEC,
            requests_per_10_min=settings.RATE_LIMIT_PER_10_MIN
        )
        self.rate_limiter.add_endpoint_limiter(
            "summoner",
            requests_per_10_sec=settings.RATE_LIMIT_PER_10_SEC,
            requests_per_10_min=settings.RATE_LIMIT_PER_10_MIN
        )
        self.rate_limiter.add_endpoint_limiter(
            "league",
            requests_per_10_sec=settings.RATE_LIMIT_PER_10_SEC,
            requests_per_10_min=settings.RATE_LIMIT_PER_10_MIN
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(timeout=self.timeout, headers={'X-Riot-Token': self.api_key})
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    def _get_platform_url(self, region: Region) -> str:
        """Get platform-specific base URL."""
        return f"https://{region.platform_route}.api.riotgames.com"
    
    def _get_regional_url(self, region: Region) -> str:
        """Get regional base URL for account/match APIs."""
        return f"https://{region.regional_route}.api.riotgames.com"
    
    async def _make_request(
        self,
        url: str,
        endpoint_type: str = "default",
        max_retries: int = None
    ) -> Optional[Dict[Any, Any]]:
        """
        Make an API request with retry logic.
        
        Args:
            url: Full URL to request
            endpoint_type: Type of endpoint for rate limiting
            max_retries: Maximum number of retries
            
        Returns:
            JSON response or None if failed
        """
        if max_retries is None:
            max_retries = settings.MAX_RETRIES
        
        for attempt in range(max_retries + 1):
            try:
                # Acquire rate limit permission
                await self.rate_limiter.acquire(endpoint_type)
                
                response = await self.session.get(url)
                self.last_status_code = response.status_code
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', '1'))
                    logger.warning(f"Rate limited. Retrying after {retry_after}s. URL: {url}")
                    await asyncio.sleep(retry_after)
                    continue
                if response.status_code == 404:
                    logger.debug(f"Resource not found (404): {url}")
                    return None
                if response.status_code >= 400:
                    logger.error(f"API error {response.status_code} for URL: {url}")
                    if attempt < max_retries:
                        wait_time = settings.RETRY_BACKOFF ** attempt
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    return None
                return response.json()
            
            except httpx.HTTPError as e:
                logger.error(f"Network error: {e}. URL: {url}")
                if attempt < max_retries:
                    wait_time = settings.RETRY_BACKOFF ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                return None
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}. URL: {url}")
                return None
        
        return None
    
    # ==================== Match API ====================
    
    async def get_match_ids_by_puuid(
        self,
        region: Region,
        puuid: str,
        queue: QueueType,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start: int = 0,
        count: int = 100
    ) -> List[str]:
        """
        Get match IDs for a summoner.
        
        Args:
            region: Server region
            puuid: Player UUID
            queue: Queue type (Solo/Duo or Flex)
            start_time: Epoch timestamp in seconds
            end_time: Epoch timestamp in seconds
            start: Starting index
            count: Number of matches to return (max 100)
            
        Returns:
            List of match IDs
        """
        base_url = self._get_regional_url(region)
        url = f"{base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        
        params = {
            'queue': queue.queue_id,
            'start': start,
            'count': min(count, 100)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        url_with_params = url + '?' + '&'.join(
            f"{k}={v}" for k, v in params.items()
        )
        
        result = await self._make_request(url_with_params, "match")
        return result if result else []
    
    async def get_match_by_id(
        self,
        region: Region,
        match_id: str
    ) -> Optional[Dict[Any, Any]]:
        """
        Get detailed match data by match ID.
        
        Args:
            region: Server region
            match_id: Match identifier
            
        Returns:
            Match data dictionary or None
        """
        base_url = self._get_regional_url(region)
        url = f"{base_url}/lol/match/v5/matches/{match_id}"
        
        return await self._make_request(url, "match")
    
    # ==================== Summoner API ====================
    
    async def get_summoner_by_puuid(
        self,
        region: Region,
        puuid: str
    ) -> Optional[Dict[Any, Any]]:
        """
        Get summoner data by PUUID.
        
        Args:
            region: Server region
            puuid: Player UUID
            
        Returns:
            Summoner data or None
        """
        base_url = self._get_platform_url(region)
        url = f"{base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        
        return await self._make_request(url, "summoner")
    
    async def get_summoner_by_id(
        self,
        region: Region,
        summoner_id: str
    ) -> Optional[Dict[Any, Any]]:
        base_url = self._get_platform_url(region)
        url = f"{base_url}/lol/summoner/v4/summoners/{summoner_id}"
        return await self._make_request(url, "summoner")
    
    async def get_summoner_by_name(
        self,
        region: Region,
        summoner_name: str
    ) -> Optional[Dict[Any, Any]]:
        base_url = self._get_platform_url(region)
        url = f"{base_url}/lol/summoner/v4/summoners/by-name/{summoner_name}"
        return await self._make_request(url, "summoner")
    
    # ==================== League API ====================
    
    async def get_league_entries_by_summoner(
        self,
        region: Region,
        summoner_id: str
    ) -> Optional[List[Dict[Any, Any]]]:
        """
        Get ranked league entries for a summoner.
        
        Args:
            region: Server region
            summoner_id: Summoner ID (encrypted)
            
        Returns:
            List of league entries or None
        """
        base_url = self._get_platform_url(region)
        url = f"{base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
        
        return await self._make_request(url, "league")
    
    async def get_league_entries_by_puuid(
        self,
        region: Region,
        puuid: str
    ) -> Optional[List[Dict[Any, Any]]]:
        """
        Get ranked league entries by PUUID.
        
        Args:
            region: Server region
            puuid: Player UUID
            
        Returns:
            List of league entries or None
        """
        base_url = self._get_platform_url(region)
        url = f"{base_url}/lol/league/v4/entries/by-puuid/{puuid}"
        
        return await self._make_request(url, "league")
    
    async def get_challenger_league(
        self,
        region: Region,
        queue: QueueType
    ) -> Optional[Dict[Any, Any]]:
        """
        Get challenger league for a queue.
        
        Args:
            region: Server region
            queue: Queue type
            
        Returns:
            Challenger league data or None
        """
        base_url = self._get_platform_url(region)
        queue_name = "RANKED_SOLO_5x5" if queue == QueueType.RANKED_SOLO_5x5 else "RANKED_FLEX_SR"
        url = f"{base_url}/lol/league/v4/challengerleagues/by-queue/{queue_name}"
        
        return await self._make_request(url, "league")
    
    async def get_grandmaster_league(
        self,
        region: Region,
        queue: QueueType
    ) -> Optional[Dict[Any, Any]]:
        """
        Get grandmaster league for a queue.
        
        Args:
            region: Server region
            queue: Queue type
            
        Returns:
            Grandmaster league data or None
        """
        base_url = self._get_platform_url(region)
        queue_name = "RANKED_SOLO_5x5" if queue == QueueType.RANKED_SOLO_5x5 else "RANKED_FLEX_SR"
        url = f"{base_url}/lol/league/v4/grandmasterleagues/by-queue/{queue_name}"
        
        return await self._make_request(url, "league")
    
    async def get_master_league(
        self,
        region: Region,
        queue: QueueType
    ) -> Optional[Dict[Any, Any]]:
        """
        Get master league for a queue.
        
        Args:
            region: Server region
            queue: Queue type
            
        Returns:
            Master league data or None
        """
        base_url = self._get_platform_url(region)
        queue_name = "RANKED_SOLO_5x5" if queue == QueueType.RANKED_SOLO_5x5 else "RANKED_FLEX_SR"
        url = f"{base_url}/lol/league/v4/masterleagues/by-queue/{queue_name}"
        
        return await self._make_request(url, "league")
