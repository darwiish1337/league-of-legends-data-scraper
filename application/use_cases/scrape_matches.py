"""Use case for scraping match data sequentially by region."""
import logging
import asyncio
from typing import Dict, List

from domain.entities import Match
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient, MatchRepository, SummonerRepository
from application.services import DataScraperService
from config import settings

logger = logging.getLogger(__name__)


class ScrapeMatchesUseCase:
    """Coordinates match scraping: sequential by region, concurrent per queue."""
    
    def __init__(self, api_client: RiotAPIClient, progress_callback=None, status_callback=None):
        """
        Initialize use case.
        
        Args:
            api_client: Riot API client instance
        """
        self.api_client = api_client
        self.match_repo = MatchRepository(api_client)
        self.summoner_repo = SummonerRepository(api_client)
        self.scraper_service = DataScraperService(
            self.match_repo,
            self.summoner_repo,
            progress_callback=progress_callback,
            status_callback=status_callback
        )
        try:
            from application.services import DataPersistenceService
            db_path = settings.DB_DIR / "scraper.sqlite"
            p = DataPersistenceService(db_path)
            existing_ids = p.get_existing_match_ids()
            existing_puuids = p.get_existing_puuids()
            self.scraper_service.scraped_match_ids.update(existing_ids)
            self.scraper_service.scraped_puuids.update(existing_puuids)
        except Exception:
            pass
    
    async def execute(
        self,
        regions: List[Region] = None,
        queue_types: List[QueueType] = None,
        matches_per_region: int = 500,
        matches_total: int = None,
        seed_puuids_by_region: Dict[Region, List[str]] = None
    ) -> Dict[str, Dict[str, List[Match]]]:
        """
        Execute the scraping process.
        
        Args:
            regions: List of regions to scrape (defaults to all)
            queue_types: List of queue types to scrape (defaults to both ranked)
            matches_per_region: Number of matches to scrape per region
            
        Returns:
            Dictionary mapping region -> queue_type -> matches
        """
        # Default to all regions if not specified
        if regions is None:
            regions = Region.all_regions()
        
        # Default to both ranked queues if not specified
        if queue_types is None:
            queue_types = QueueType.ranked_queues()
        
        logger.info(
            f"Starting scrape for {len(regions)} regions, "
            f"{len(queue_types)} queue types"
        )
        
        results = {}
        total_collected = 0
        
        for idx, region in enumerate(regions):
            region_results = {}
            next_region = regions[idx + 1] if idx + 1 < len(regions) else None
            # Announce region once, not per-queue
            if self.scraper_service.status_callback:
                self.scraper_service.status_callback(("server", region, next_region))
            # Initialize region-level progress line
            if self.scraper_service.progress_callback:
                self.scraper_service.progress_callback(0, matches_per_region or 0)
            # Run queues concurrently in chunks until region reaches target
            outer_progress_cb = self.scraper_service.progress_callback
            local_services = {}
            counts = {"solo": 0, "flex": 0}
            def mk_progress(label: str):
                def _cb(c, _t):
                    counts[label] = max(0, c or 0)
                    if outer_progress_cb:
                        total = counts["solo"] + counts["flex"]
                        if matches_per_region is not None:
                            total = min(total, matches_per_region)
                        outer_progress_cb(total, matches_per_region or 0)
                return _cb
            for queue_type in queue_types:
                label = "solo" if queue_type == QueueType.RANKED_SOLO_5x5 else "flex"
                local_services[queue_type] = DataScraperService(
                    self.match_repo,
                    self.summoner_repo,
                    progress_callback=mk_progress(label),
                    status_callback=self.scraper_service.status_callback
                )
            region_total = 0
            no_progress_loops = 0
            while region_total < (matches_per_region or 0):
                remaining = (matches_per_region or 0) - region_total
                if remaining <= 0:
                    break
                qn = max(1, len(queue_types) if queue_types else 1)
                per_queue_chunk = max(1, min((remaining + qn - 1) // qn, 500))
                tasks = []
                for queue_type in queue_types:
                    tasks.append(local_services[queue_type].scrape_matches_by_date_window(
                        region=region,
                        queue_type=queue_type,
                        max_matches=per_queue_chunk,
                        seed_puuids=(seed_puuids_by_region.get(region) if seed_puuids_by_region else None)
                    ))
                try:
                    before = region_total
                    queues_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for queue_type, res in zip(queue_types, queues_results):
                        if isinstance(res, Exception):
                            logger.error(f"Error scraping {region.value} - {queue_type.queue_name}: {res}")
                            region_results.setdefault(queue_type.queue_name, [])
                        else:
                            region_results.setdefault(queue_type.queue_name, [])
                            take = max(0, (matches_per_region or 0) - region_total)
                            if take > 0:
                                sliced = res[:take]
                                region_results[queue_type.queue_name].extend(sliced)
                                total_collected += len(sliced)
                                region_total += len(sliced)
                    if outer_progress_cb:
                        outer_progress_cb(region_total, 0)
                    if region_total <= before:
                        no_progress_loops += 1
                    else:
                        no_progress_loops = 0
                    if no_progress_loops >= 2:
                        try:
                            for qt in queue_types:
                                extra = await local_services[qt]._discover_seed_puuids_neutral(region, qt, count=50)
                                for pu in extra:
                                    if pu not in local_services[qt].scraped_puuids:
                                        local_services[qt].scraped_puuids.add(pu)
                            no_progress_loops = 0
                        except Exception:
                            break
                except Exception as e:
                    logger.error(f"Error scraping {region.value}: {e}")
                    break
            
            results[region.value] = region_results
            # Optional global cap across all regions
            if matches_total is not None and total_collected >= matches_total:
                logger.info(f"Reached overall total guideline: {total_collected}")
                break
        
        # Log summary
        logger.info(f"Scraping complete!")
        return results
        
