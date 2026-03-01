"""Riot Games API client."""
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
import httpx

from config import settings
from domain.enums import Region, QueueType
from .rate_limiter import EndpointRateLimiter

logger = logging.getLogger(__name__)


class RiotAPIClient:
    """Asynchronous Riot API client with correct rate limiting."""

    def __init__(self, api_key: str):
        self.api_key  = api_key
        self.session: Optional[httpx.AsyncClient] = None
        self.timeout  = settings.REQUEST_TIMEOUT
        self.last_status_code: Optional[int] = None
        self._endpoint_cooldown: dict[str, float] = {}

        self.rate_limiter = EndpointRateLimiter()
        self.rate_limiter.set_default_limiter(
            requests_per_1_sec=settings.RATE_LIMIT_PER_1_SEC,
            requests_per_2_min=settings.RATE_LIMIT_PER_2_MIN,
        )
        self._setup_endpoint_limiters()

    def _setup_endpoint_limiters(self) -> None:
        self.rate_limiter.add_endpoint_limiter(
            "match",
            requests_per_1_sec=settings.MATCH_RATE_LIMIT_PER_1_SEC,
            requests_per_2_min=settings.MATCH_RATE_LIMIT_PER_2_MIN,
        )
        self.rate_limiter.add_endpoint_limiter(
            "summoner",
            requests_per_1_sec=settings.SUMMONER_RATE_LIMIT_PER_1_SEC,
            requests_per_2_min=settings.SUMMONER_RATE_LIMIT_PER_2_MIN,
        )
        self.rate_limiter.add_endpoint_limiter(
            "league",
            requests_per_1_sec=settings.LEAGUE_RATE_LIMIT_PER_1_SEC,
            requests_per_2_min=settings.LEAGUE_RATE_LIMIT_PER_2_MIN,
        )

    async def __aenter__(self):
        http2 = False
        try:
            import h2  # type: ignore
            http2 = True
        except Exception:
            pass
        self.session = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"X-Riot-Token": self.api_key},
            http2=http2,
        )
        return self

    async def __aexit__(self, *_):
        if self.session:
            await self.session.aclose()

    def _get_platform_url(self, region: Region) -> str:
        return f"https://{region.platform_route}.api.riotgames.com"

    def _get_regional_url(self, region: Region) -> str:
        return f"https://{region.regional_route}.api.riotgames.com"

    def _platform_host_candidates(self, region: Region) -> list[str]:
        if region.regional_route == "sea":
            order = [region.platform_route, "sg2", "th2", "tw2", "vn2", "oc1"]
            seen: set = set()
            return [h for h in order if not (h in seen or seen.add(h))]  # type: ignore
        return [region.platform_route]

    async def _request_platform_with_fallback(
        self, region: Region, path_suffix: str, endpoint_type: str
    ) -> Optional[Dict[Any, Any]]:
        for host in self._platform_host_candidates(region):
            url  = f"https://{host}.api.riotgames.com{path_suffix}"
            data = await self._make_request(url, endpoint_type)
            if data is not None:
                return data
        return None

    async def _make_request(
        self,
        url: str,
        endpoint_type: str = "default",
        max_retries: int = None,
    ) -> Optional[Dict[Any, Any]]:
        if max_retries is None:
            max_retries = settings.MAX_RETRIES

        for attempt in range(max_retries + 1):
            try:
                # honour per-endpoint cooldown after 429
                cd = self._endpoint_cooldown.get(endpoint_type, 0.0)
                now = time.monotonic()
                if cd > now:
                    await asyncio.sleep(cd - now)

                await self.rate_limiter.acquire(endpoint_type)

                response = await self.session.get(url)
                self.last_status_code = response.status_code

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 401:
                    logger.error("401 Unauthorized — check RIOT_API_KEY")
                    return None

                if response.status_code == 404:
                    return None

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(f"429 rate-limited — waiting {retry_after}s")
                    self._endpoint_cooldown[endpoint_type] = time.monotonic() + retry_after
                    await self.rate_limiter.reset_endpoint(endpoint_type)
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    if attempt < max_retries:
                        wait = settings.RETRY_BACKOFF ** attempt
                        await asyncio.sleep(wait)
                        continue
                    return None

                logger.warning(f"HTTP {response.status_code} for {url}")
                return None

            except httpx.TimeoutException:
                if attempt < max_retries:
                    await asyncio.sleep(settings.RETRY_BACKOFF ** attempt)
                    continue
                return None

            except httpx.HTTPError as exc:
                logger.error(f"Network error: {exc}")
                if attempt < max_retries:
                    await asyncio.sleep(settings.RETRY_BACKOFF ** attempt)
                    continue
                return None

            except Exception as exc:
                logger.error(f"Unexpected error: {exc}")
                return None

        return None

    # ── Match API ──────────────────────────────────────────────────────

    async def get_match_ids_by_puuid(
        self,
        region: Region,
        puuid: str,
        queue: QueueType,
        start_time: Optional[int] = None,
        end_time:   Optional[int] = None,
        start: int = 0,
        count: int = 20,
    ) -> List[str]:
        base = self._get_regional_url(region)
        params = f"queue={queue.queue_id}&start={start}&count={min(count, 100)}"
        if start_time:
            params += f"&startTime={start_time}"
        if end_time:
            params += f"&endTime={end_time}"
        url    = f"{base}/lol/match/v5/matches/by-puuid/{puuid}/ids?{params}"
        result = await self._make_request(url, "match")
        return result if isinstance(result, list) else []

    async def get_match_by_id(self, region: Region, match_id: str) -> Optional[Dict]:
        base = self._get_regional_url(region)
        return await self._make_request(f"{base}/lol/match/v5/matches/{match_id}", "match")

    # ── Summoner API ───────────────────────────────────────────────────

    async def get_summoner_by_puuid(self, region: Region, puuid: str) -> Optional[Dict]:
        return await self._request_platform_with_fallback(
            region, f"/lol/summoner/v4/summoners/by-puuid/{puuid}", "summoner"
        )

    async def get_summoner_by_id(self, region: Region, summoner_id: str) -> Optional[Dict]:
        return await self._request_platform_with_fallback(
            region, f"/lol/summoner/v4/summoners/{summoner_id}", "summoner"
        )

    async def get_summoner_by_name(self, region: Region, name: str) -> Optional[Dict]:
        return await self._request_platform_with_fallback(
            region, f"/lol/summoner/v4/summoners/by-name/{name}", "summoner"
        )

    # ── League API ─────────────────────────────────────────────────────

    async def get_league_entries(
        self,
        region: Region,
        queue: QueueType,
        tier: str,
        division: str,
        page: int = 1,
    ) -> Optional[List[Dict]]:
        qname = queue.api_queue_name
        path  = f"/lol/league/v4/entries/{qname}/{tier}/{division}?page={page}"
        return await self._request_platform_with_fallback(region, path, "league")

    async def get_league_entries_by_summoner(
        self, region: Region, summoner_id: str
    ) -> Optional[List[Dict]]:
        return await self._request_platform_with_fallback(
            region, f"/lol/league/v4/entries/by-summoner/{summoner_id}", "league"
        )

    async def get_league_entries_by_puuid(
        self, region: Region, puuid: str
    ) -> Optional[List[Dict]]:
        return await self._request_platform_with_fallback(
            region, f"/lol/league/v4/entries/by-puuid/{puuid}", "league"
        )

    async def get_challenger_league(self, region: Region, queue: QueueType) -> Optional[Dict]:
        return await self._request_platform_with_fallback(
            region,
            f"/lol/league/v4/challengerleagues/by-queue/{queue.api_queue_name}",
            "league",
        )

    async def get_grandmaster_league(self, region: Region, queue: QueueType) -> Optional[Dict]:
        return await self._request_platform_with_fallback(
            region,
            f"/lol/league/v4/grandmasterleagues/by-queue/{queue.api_queue_name}",
            "league",
        )

    async def get_master_league(self, region: Region, queue: QueueType) -> Optional[Dict]:
        return await self._request_platform_with_fallback(
            region,
            f"/lol/league/v4/masterleagues/by-queue/{queue.api_queue_name}",
            "league",
        )