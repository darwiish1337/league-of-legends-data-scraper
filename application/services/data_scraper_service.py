"""Data scraper service for collecting match data."""
import asyncio
import logging
from datetime import datetime
from typing import List, Set, Optional
from pathlib import Path

from domain.entities import Match
from domain.enums import Region, QueueType
from infrastructure import MatchRepository, SummonerRepository
from config import settings
from domain.enums import Rank

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
        self.progress_callback = progress_callback
        self.status_callback = status_callback
    
    async def scrape_matches_from_high_elo(
        self,
        region: Region,
        queue_type: QueueType,
        max_matches: int = 1000
    ) -> List[Match]:
        """
        Scrape matches starting from high ELO players.
        
        Args:
            region: Server region to scrape
            queue_type: Queue type (Solo/Duo or Flex)
            max_matches: Maximum number of matches to scrape
            
        Returns:
            List of scraped Match entities
        """
        logger.info(
            f"Starting scrape for {region.value} - {queue_type.queue_name} "
            f"(target: {max_matches} matches)"
        )
        
        matches: List[Match] = []
        
        # Get seed PUUIDs from high ELO leagues
        seed_puuids = await self._get_high_elo_puuids(region, queue_type)
        logger.info(f"Found {len(seed_puuids)} high ELO players as seeds")
        
        # Queue of PUUIDs to process
        puuid_queue = list(seed_puuids)
        processed_count = 0
        
        while len(matches) < max_matches and puuid_queue:
            # Take batch of PUUIDs to process concurrently
            batch_size = min(settings.MAX_CONCURRENT_REQUESTS, len(puuid_queue))
            batch_puuids = [puuid_queue.pop(0) for _ in range(batch_size)]
            
            # Process batch concurrently
            tasks = [
                self._scrape_matches_for_puuid(
                    region, puuid, queue_type, max_matches - len(matches)
                )
                for puuid in batch_puuids
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in batch processing: {result}")
                    continue
                
                if result:
                    new_matches, new_puuids = result
                    matches.extend(new_matches)
                    if self.progress_callback:
                        self.progress_callback(len(matches), max_matches)
                    if self.status_callback:
                        self.status_callback(self.match_repo.api_client.last_status_code)
                    
                    # Add new PUUIDs to queue
                    for puuid in new_puuids:
                        if puuid not in self.scraped_puuids and puuid not in puuid_queue:
                            puuid_queue.append(puuid)
            
            processed_count += batch_size
            logger.info(
                f"Progress: {len(matches)}/{max_matches} matches, "
                f"{processed_count} players processed, "
                f"{len(puuid_queue)} in queue"
            )
            
            # Break if we've reached target
            if len(matches) >= max_matches:
                break
        
        logger.info(
            f"Scraping complete: {len(matches)} matches from "
            f"{region.value} - {queue_type.queue_name}"
        )
        
        return matches[:max_matches]
    
    async def _get_high_elo_puuids(
        self,
        region: Region,
        queue_type: QueueType,
        count: int = 50
    ) -> List[str]:
        """
        Get PUUIDs of high ELO players (Challenger, Grandmaster, Master).
        
        Args:
            region: Server region
            queue_type: Queue type
            count: Target number of PUUIDs to get
            
        Returns:
            List of PUUIDs
        """
        puuids = []
        summoner_ids = []
        summoner_names = []
        
        try:
            # Get Challenger league
            challenger = await self.match_repo.api_client.get_challenger_league(
                region, queue_type
            )
            if challenger and 'entries' in challenger:
                for entry in challenger['entries'][:count // 3]:
                    pu = entry.get('puuid')
                    if pu:
                        puuids.append(pu)
                        continue
                    sid = entry.get('summonerId')
                    name = entry.get('summonerName')
                    if sid:
                        summoner_ids.append(sid)
                    elif name:
                        summoner_names.append(name)
            
            # Get Grandmaster league
            grandmaster = await self.match_repo.api_client.get_grandmaster_league(
                region, queue_type
            )
            if grandmaster and 'entries' in grandmaster:
                for entry in grandmaster['entries'][:count // 3]:
                    pu = entry.get('puuid')
                    if pu:
                        puuids.append(pu)
                        continue
                    sid = entry.get('summonerId')
                    name = entry.get('summonerName')
                    if sid:
                        summoner_ids.append(sid)
                    elif name:
                        summoner_names.append(name)
            
            # Get Master league
            master = await self.match_repo.api_client.get_master_league(
                region, queue_type
            )
            if master and 'entries' in master:
                for entry in master['entries'][:count // 3]:
                    pu = entry.get('puuid')
                    if pu:
                        puuids.append(pu)
                        continue
                    sid = entry.get('summonerId')
                    name = entry.get('summonerName')
                    if sid:
                        summoner_ids.append(sid)
                    elif name:
                        summoner_names.append(name)
            
            tasks = []
            for sid in summoner_ids[:count]:
                tasks.append(self.summoner_repo.get_summoner_by_id(region, sid))
            for name in summoner_names[:max(0, count - len(tasks))]:
                tasks.append(self.summoner_repo.get_summoner_by_name(region, name))
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception) or res is None:
                        continue
                    puuids.append(res.puuid)
        
        except Exception as e:
            logger.error(f"Error getting high ELO players: {e}")
        
        return puuids[:count]
    
    async def _scrape_matches_for_puuid(
        self,
        region: Region,
        puuid: str,
        queue_type: QueueType,
        max_matches: int
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
        if puuid in self.scraped_puuids:
            return None
        
        self.scraped_puuids.add(puuid)
        
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
                count=min(100, settings.MATCHES_PER_SUMMONER)
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
            
            # Fetch matches (limit to avoid too many at once)
            matches = []
            new_puuids = []
            
            for match_id in new_match_ids[:min(10, max_matches)]:
                match = await self.match_repo.get_match_by_id(region, match_id)
                
                if match and (not settings.TARGET_PATCH or settings.TARGET_PATCH.lower() in ("any", "all", "*") or match.patch_version == settings.TARGET_PATCH):
                    if settings.ENRICH_RANKS:
                        try:
                            await self._enrich_participants_rank(region, match, queue_type)
                        except Exception as e:
                            logger.debug(f"Rank enrichment failed for match {match_id}: {e}")
                    self.scraped_match_ids.add(match_id)
                    matches.append(match)
                    
                    # Collect PUUIDs from match participants
                    for participant in match.participants:
                        if participant.puuid not in self.scraped_puuids:
                            new_puuids.append(participant.puuid)
            
            return (matches, new_puuids)
        
        except Exception as e:
            logger.error(f"Error scraping matches for PUUID {puuid}: {e}")
            return None
    
    async def _enrich_participants_rank(self, region: Region, match: Match, queue_type: QueueType) -> None:
        tasks = []
        for p in match.participants:
            tasks.append(self.summoner_repo.get_summoner_rank_info_flexible(region, p.puuid, p.summoner_id))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for p, rank_info in zip(match.participants, results):
            if isinstance(rank_info, Exception) or not rank_info:
                p.rank_tier = Rank.UNRANKED
                p.rank_division = ""
                continue
            if queue_type == QueueType.RANKED_SOLO_5x5 and 'solo' in rank_info:
                entry = rank_info['solo']
            elif queue_type == QueueType.RANKED_FLEX_SR and 'flex' in rank_info:
                entry = rank_info['flex']
            else:
                entry = rank_info.get('solo') or rank_info.get('flex')
            if entry:
                p.rank_tier = Rank.from_string(entry.get('tier', 'UNRANKED'))
                p.rank_division = entry.get('rank', '')
            else:
                p.rank_tier = Rank.UNRANKED
                p.rank_division = ""
    
    def _get_patch_time_range(self) -> tuple[int, Optional[int]]:
        """
        Get Unix timestamp range for target patch.
        
        Returns:
            Tuple of (start_time, end_time) in seconds
        """
        # Parse patch start date
        start_date = datetime.strptime(
            settings.PATCH_START_DATE, 
            "%Y-%m-%d"
        )
        start_time = int(start_date.timestamp())
        
        # Parse patch end date (if specified)
        end_time = None
        if settings.PATCH_END_DATE:
            end_date = datetime.strptime(
                settings.PATCH_END_DATE,
                "%Y-%m-%d"
            )
            end_time = int(end_date.timestamp())
        
        return (start_time, end_time)
    
    async def scrape_all_regions(
        self,
        queue_type: QueueType,
        matches_per_region: int = 500
    ) -> dict[str, List[Match]]:
        """
        Scrape matches from all regions.
        
        Args:
            queue_type: Queue type to scrape
            matches_per_region: Matches to scrape per region
            
        Returns:
            Dictionary mapping region name to matches
        """
        results = {}
        
        for region in Region.all_regions():
            logger.info(f"Starting scrape for region: {region.value}")
            
            try:
                matches = await self.scrape_matches_from_high_elo(
                    region=region,
                    queue_type=queue_type,
                    max_matches=matches_per_region
                )
                results[region.value] = matches
                
                logger.info(
                    f"Completed {region.value}: {len(matches)} matches"
                )
            
            except Exception as e:
                logger.error(f"Error scraping {region.value}: {e}")
                results[region.value] = []
            
            # Small delay between regions
            await asyncio.sleep(2)
        
        return results
