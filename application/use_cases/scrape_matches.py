"""Use case for scraping match data - one continuous run per queue."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from domain.entities import Match
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient, MatchRepository, SummonerRepository
from application.services.data_scraper import DataScraperService
from config import settings

logger = logging.getLogger(__name__)


class ScrapeMatchesUseCase:
    """
    Runs each queue as a single continuous scrape until the region target
    is met.  No chunking — the DataScraperService loop handles everything
    internally and keeps discovering new PUUIDs automatically.
    """

    def __init__(
        self,
        api_client: RiotAPIClient,
        progress_callback=None,
        status_callback=None,
    ):
        self.api_client    = api_client
        self.match_repo    = MatchRepository(api_client)
        self.summoner_repo = SummonerRepository(api_client)
        self._progress_cb  = progress_callback
        self._status_cb    = status_callback

        # Shared sets — pre-loaded from DB so we never re-fetch old data
        self._scraped_match_ids: set = set()
        self._scraped_puuids:    set = set()
        try:
            from application.services.data_persistence_service import DataPersistenceService
            db_path = settings.DB_DIR / "scraper.sqlite"
            p = DataPersistenceService(db_path)
            self._scraped_match_ids.update(p.get_existing_match_ids())
            self._scraped_puuids.update(p.get_existing_puuids())
        except Exception:
            pass

    # ------------------------------------------------------------------ #

    async def execute(
        self,
        regions: List[Region] = None,
        queue_types: List[QueueType] = None,
        matches_per_region: int = 500,
        matches_total: int = None,
        seed_puuids_by_region: Dict[Region, List[str]] = None,
    ) -> Dict[str, Dict[str, List[Match]]]:

        if regions is None:
            regions = Region.all_regions()
        if queue_types is None:
            queue_types = QueueType.ranked_queues()

        results: Dict[str, Dict[str, List[Match]]] = {}
        total_collected = 0
        n_queues = max(1, len(queue_types))

        for region in regions:
            region_results: Dict[str, List[Match]] = {qt.queue_name: [] for qt in queue_types}

            # Each queue scrapes half the target concurrently
            per_queue_target = max(1, (matches_per_region + n_queues - 1) // n_queues)

            # Totals across queues — used for the single shared progress bar
            counts: Dict[str, int] = {qt.queue_name: 0 for qt in queue_types}

            def _make_cb(qname: str):
                def _cb(current: int, _total: int) -> None:
                    cur = max(0, int(current or 0))
                    if cur > counts[qname]:
                        counts[qname] = cur
                    if self._progress_cb:
                        combined = min(sum(counts.values()), matches_per_region)
                        self._progress_cb(combined, matches_per_region)
                return _cb

            # Build one DataScraperService per queue; share global id/puuid pools
            services: Dict[QueueType, DataScraperService] = {}
            for qt in queue_types:
                svc = DataScraperService(
                    self.match_repo,
                    self.summoner_repo,
                    progress_callback=_make_cb(qt.queue_name),
                    status_callback=self._status_cb,
                )
                # Share the global dedup pools
                svc.scraped_match_ids = self._scraped_match_ids
                svc.scraped_puuids    = self._scraped_puuids
                # Inject any external seeds
                if seed_puuids_by_region:
                    for p in seed_puuids_by_region.get(region, []):
                        if p and p not in self._scraped_puuids:
                            self._scraped_puuids.add(p)
                services[qt] = svc

            # Run all queues concurrently in a single gather — no outer loop
            tasks = [
                services[qt].scrape_matches_by_date_window(
                    region=region,
                    queue_type=qt,
                    max_matches=per_queue_target,
                )
                for qt in queue_types
            ]
            queue_results = await asyncio.gather(*tasks, return_exceptions=True)

            region_total = 0
            for qt, res in zip(queue_types, queue_results):
                if isinstance(res, Exception):
                    logger.error(f"Queue {qt.queue_name} error for {region.value}: {res}")
                    continue
                cap    = max(0, matches_per_region - region_total)
                sliced = res[:cap]
                region_results[qt.queue_name].extend(sliced)
                region_total    += len(sliced)
                total_collected += len(sliced)

            results[region.value] = region_results
            logger.info(f"region-done {region.value} collected={region_total}")

            if matches_total is not None and total_collected >= matches_total:
                break

        return results