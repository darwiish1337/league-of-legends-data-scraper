"""Data scraper service for collecting match data."""
import asyncio
import logging
from datetime import datetime, timedelta
import os
from typing import List, Set, Optional
from pathlib import Path

from domain.entities import Match
from domain.enums import Region, QueueType
from infrastructure import MatchRepository, SummonerRepository
from config import settings

logger = logging.getLogger(__name__)


class DataScraperService:
    """Service for scraping match data from Riot API."""
    
    def __init__(
        self,
        match_repo: MatchRepository,
        summoner_repo: SummonerRepository,
        progress_callback=None,
        status_callback=None
    ):
        """
        Initialize data scraper service.
        
        Args:
            match_repo: Match repository instance
            summoner_repo: Summoner repository instance
        """
        self.match_repo = match_repo
        self.summoner_repo = summoner_repo
        self.scraped_match_ids: Set[str] = set()
        self.scraped_puuids: Set[str] = set()
        self.processed_puuids: Set[str] = set()
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self._match_sem = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
    
    async def scrape_matches_by_date_window(
        self,
        region: Region,
        queue_type: QueueType,
        max_matches: Optional[int] = None,
        seed_puuids: Optional[List[str]] = None
    ) -> List[Match]:
        """
        Scrape matches constrained by date or patch window.
        
        Args:
            region: Server region to scrape
            queue_type: Queue type (Solo/Duo or Flex)
            max_matches: Maximum number of matches to scrape within window
            
        Returns:
            List of scraped Match entities
        """
        matches: List[Match] = []
        puuid_queue = list(self.scraped_puuids)
        if seed_puuids:
            for p in seed_puuids:
                if p not in self.scraped_puuids and p not in puuid_queue:
                    puuid_queue.append(p)
                    self.scraped_puuids.add(p)
        if puuid_queue:
            puuid_queue = puuid_queue[:100]
        processed_count = 0
        
        if not puuid_queue:
            seed_names = settings.SEED_SUMMONERS
            if seed_names:
                names = [n.strip() for n in seed_names.split(",") if n.strip()]
                tasks = [self.summoner_repo.get_summoner_by_name(region, n) for n in names]
                res = await asyncio.gather(*tasks, return_exceptions=True)
                puuid_queue = [r.puuid for r in res if not isinstance(r, Exception) and r]
            if not puuid_queue:
                seed_puuids = settings.SEED_PUUIDS
                if seed_puuids:
                    puuid_queue = [p.strip() for p in seed_puuids.split(",") if p.strip()]
            if not puuid_queue:
                try:
                    puuid_queue = await self._discover_seed_puuids_neutral(region, queue_type, count=5)
                except Exception:
                    puuid_queue = []
            if not puuid_queue:
                raise ValueError("No seed PUUIDs available. Provide SEED_PUUIDS or SEED_SUMMONERS, or run once to populate DB.")
        
        while puuid_queue:
            batch_size = min(settings.MAX_CONCURRENT_REQUESTS, len(puuid_queue))
            batch_puuids = [puuid_queue.pop(0) for _ in range(batch_size)]
            
            limit = min(settings.MATCHES_PER_SUMMONER, max(1, (max_matches - len(matches)) if max_matches else settings.MATCHES_PER_SUMMONER))
            tasks = [self._scrape_matches_for_puuid(region, puuid, queue_type, limit) for puuid in batch_puuids]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in batch processing: {result}")
                    continue
                
                if result:
                    new_matches, new_puuids = result
                    if max_matches is not None and len(matches) >= max_matches:
                        break
                    room = None
                    if max_matches is not None:
                        room = max(0, max_matches - len(matches))
                    if room is not None:
                        matches.extend(new_matches[:room])
                    else:
                        matches.extend(new_matches)
                    if self.progress_callback:
                        self.progress_callback(len(matches), 0)
                    if self.status_callback:
                        self.status_callback(self.match_repo.api_client.last_status_code)
                    
                    for puuid in new_puuids:
                        if puuid not in self.scraped_puuids and puuid not in puuid_queue:
                            puuid_queue.append(puuid)
                            self.scraped_puuids.add(puuid)
            
            processed_count += batch_size
            if max_matches is not None and len(matches) >= max_matches:
                break
            if not puuid_queue and (max_matches is None or len(matches) < max_matches):
                try:
                    extra = await self._discover_seed_puuids_neutral(region, queue_type, count=50)
                    for pu in extra:
                        if pu not in self.scraped_puuids:
                            puuid_queue.append(pu)
                except Exception:
                    pass
        
        return matches
    
    async def scrape_matches_unbounded(
        self,
        region: Region,
        queue_type: QueueType,
        max_matches: Optional[int] = None
    ) -> List[Match]:
        """
        Scrape matches without date/patch constraints (bootstrap mode).
        Returns a list of matches and discovers additional PUUIDs while scraping.
        """
        matches: List[Match] = []
        puuid_queue = list(self.scraped_puuids)
        if not puuid_queue:
            raise ValueError("No seed PUUIDs available for unbounded scrape.")
        while puuid_queue:
            batch_size = min(settings.MAX_CONCURRENT_REQUESTS, len(puuid_queue))
            batch_puuids = [puuid_queue.pop(0) for _ in range(batch_size)]
            tasks = [
                self._scrape_matches_for_puuid_unbounded(
                    region,
                    puuid,
                    queue_type,
                    min(settings.MATCHES_PER_SUMMONER, max(1, (max_matches - len(matches)) if max_matches else settings.MATCHES_PER_SUMMONER))
                )
                for puuid in batch_puuids
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, Exception) or not result:
                    continue
                new_matches, new_puuids = result
                if max_matches is not None and len(matches) >= max_matches:
                    break
                room = None
                if max_matches is not None:
                    room = max(0, max_matches - len(matches))
                if room is not None:
                    matches.extend(new_matches[:room])
                else:
                    matches.extend(new_matches)
                for pu in new_puuids:
                    if pu not in self.scraped_puuids and pu not in puuid_queue:
                        puuid_queue.append(pu)
                        self.scraped_puuids.add(pu)
            if max_matches is not None and len(matches) >= max_matches:
                break
        return matches

    async def _scrape_matches_for_puuid_unbounded(
        self,
        region: Region,
        puuid: str,
        queue_type: QueueType,
        limit: int
    ) -> Optional[tuple[List[Match], List[str]]]:
        """
        Scrape matches for a specific PUUID without date/patch filtering.
        """
        if puuid in self.processed_puuids:
            return None
        self.processed_puuids.add(puuid)
        try:
            match_ids = await self.match_repo.get_match_ids_by_puuid(
                region=region,
                puuid=puuid,
                queue_type=queue_type,
                start_time=None,
                end_time=None,
                start=0,
                count=min(settings.IDS_PER_PUUID, limit)
            )
            if not match_ids:
                return ([], [])
            new_match_ids = [mid for mid in match_ids if mid not in self.scraped_match_ids]
            if not new_match_ids:
                return ([], [])
            matches: List[Match] = []
            new_puuids: List[str] = []
            select_ids = new_match_ids[:min(settings.IDS_PER_PUUID, limit)]
            tasks = [self._get_match_with_limit(region, mid) for mid in select_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for mid, match in zip(select_ids, results):
                if isinstance(match, Exception) or not match:
                    continue
                pv = getattr(match, "patch_version", "") or ""
                tp = settings.TARGET_PATCH or ""
                patch_ok = (
                    not tp
                    or tp.lower() in ("any", "all", "*")
                    or pv == tp
                    or pv.startswith(tp)
                )
                if not patch_ok:
                    continue
                self.scraped_match_ids.add(mid)
                matches.append(match)
                for participant in match.participants:
                    if participant.puuid not in self.scraped_puuids:
                        new_puuids.append(participant.puuid)
            return (matches, new_puuids)
        except Exception as e:
            logger.error(f"Error scraping unbounded for PUUID {puuid}: {e}")
            return None
    
    async def _scrape_matches_for_puuid(
        self,
        region: Region,
        puuid: str,
        queue_type: QueueType,
        limit: int
    ) -> Optional[tuple[List[Match], List[str]]]:
        """
        Scrape matches for a specific PUUID.
        
        Args:
            region: Server region
            puuid: Player UUID
            queue_type: Queue type
            max_matches: Maximum matches to return
            
        Returns:
            Tuple of (matches, new_puuids) or None
        """
        if puuid in self.processed_puuids:
            return None
        self.processed_puuids.add(puuid)
        
        try:
            # Calculate time range for patch 26.01
            start_time, end_time = self._get_patch_time_range()
            
            # Get match IDs for this player
            match_ids = await self.match_repo.get_match_ids_by_puuid(
                region=region,
                puuid=puuid,
                queue_type=queue_type,
                start_time=start_time,
                end_time=end_time,
                start=0,
                count=min(settings.IDS_PER_PUUID, limit)
            )
            
            if not match_ids:
                return ([], [])
            
            # Filter out already scraped matches
            new_match_ids = [
                mid for mid in match_ids 
                if mid not in self.scraped_match_ids
            ]
            
            if not new_match_ids:
                return ([], [])
            
            matches = []
            new_puuids = []
            select_ids = new_match_ids[:min(settings.IDS_PER_PUUID, limit)]
            tasks = [self._get_match_with_limit(region, mid) for mid in select_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for mid, match in zip(select_ids, results):
                if isinstance(match, Exception) or not match:
                    continue
                pv = getattr(match, "patch_version", "") or ""
                tp = settings.TARGET_PATCH or ""
                patch_ok = (
                    not tp
                    or tp.lower() in ("any", "all", "*")
                    or pv == tp
                    or pv.startswith(tp)
                )
                if not patch_ok:
                    continue
                self.scraped_match_ids.add(mid)
                matches.append(match)
                for participant in match.participants:
                    if participant.puuid not in self.scraped_puuids:
                        new_puuids.append(participant.puuid)
            
            return (matches, new_puuids)
        
        except Exception as e:
            logger.error(f"Error scraping matches for PUUID {puuid}: {e}")
            return None
    
    async def _get_match_with_limit(self, region: Region, mid: str):
        async with self._match_sem:
            return await self.match_repo.get_match_by_id(region, mid)
    
    
    def _get_patch_time_range(self) -> tuple[int, Optional[int]]:
        """
        Get Unix timestamp range for target patch.
        
        Returns:
            Tuple of (start_time, end_time) in seconds
        """
        # Optional single-day override via settings
        day = settings.SCRAPE_DATE
        if day:
            try:
                d = datetime.strptime(day, "%Y-%m-%d")
                start_time = int(d.timestamp())
                end_time = int((d + timedelta(days=1)).timestamp())
                return (start_time, end_time)
            except Exception:
                pass
        # Patch window default
        start_date = datetime.strptime(settings.PATCH_START_DATE, "%Y-%m-%d")
        start_time = int(start_date.timestamp())
        end_time = None
        if settings.PATCH_END_DATE:
            end_date = datetime.strptime(settings.PATCH_END_DATE, "%Y-%m-%d")
            end_time = int(end_date.timestamp())
        return (start_time, end_time)

    async def _discover_seed_puuids_neutral(
        self,
        region: Region,
        queue_type: QueueType,
        count: int = 50
    ) -> List[str]:
        tiers = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND"]
        divisions = ["I", "II", "III", "IV"]
        summoner_ids: List[str] = []
        try:
            for t in tiers:
                for d in divisions:
                    entries = await self.match_repo.api_client.get_league_entries(region, queue_type, t, d, page=1)
                    if not entries:
                        continue
                    for e in entries:
                        sid = e.get("summonerId")
                        if sid:
                            summoner_ids.append(sid)
                            if len(summoner_ids) >= count:
                                break
                    if len(summoner_ids) >= count:
                        break
                if len(summoner_ids) >= count:
                    break
            tasks = [self.summoner_repo.get_summoner_by_id(region, sid) for sid in summoner_ids[:count]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            puuids: List[str] = []
            for r in results:
                if isinstance(r, Exception) or r is None:
                    continue
                puuids.append(r.puuid)
            return puuids[:count]
        except Exception:
            return []
