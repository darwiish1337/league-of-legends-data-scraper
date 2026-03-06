"""Region-level scrape orchestration."""
from __future__ import annotations

from typing import Callable, List, Optional

from config import settings
from domain.entities import Match
from domain.enums import QueueType, Region
from infrastructure import RiotAPIClient
from application.use_cases import ScrapeMatchesUseCase
from application.services.data_persistence_service import DataPersistenceService


ProgressCallback = Callable[[int, int], None]
SeedsReadyCallback = Optional[Callable[[Region, int], None]]


class RegionScrapeRunner:
    def __init__(self, api_client: RiotAPIClient, persistence: DataPersistenceService) -> None:
        self._api_client = api_client
        self._persistence = persistence

    async def run_region(
        self,
        region: Region,
        queues: List[QueueType],
        target: int,
        progress_cb: ProgressCallback,
        seeds_ready_cb: SeedsReadyCallback = None,
        session_id: str | None = None,
    ) -> List[Match]:
        db_seeds: List[str] = []
        try:
            db_seeds = self._persistence.get_existing_puuids_for_region(region.value)[:200]
        except Exception:
            db_seeds = []
        if seeds_ready_cb:
            seeds_ready_cb(region, len(db_seeds))
        seed_map = {region: db_seeds} if db_seeds else None
        use_case = ScrapeMatchesUseCase(
            self._api_client,
            progress_callback=progress_cb,
            status_callback=lambda _: None,
            persistence=self._persistence,
            session_id=session_id,
            # session rows store uppercase names (Region.name), not .value
            region_value=region.name,
        )
        results = await use_case.execute(
            regions=[region],
            queue_types=queues,
            matches_per_region=target,
            matches_total=None,
            seed_puuids_by_region=seed_map,
        )
        region_matches: List[Match] = []
        for region_data in results.values():
            for matches in region_data.values():
                region_matches.extend(matches)
        return region_matches

