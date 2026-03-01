"""Data scraper service - single continuous loop per region/queue."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Set, Optional, Tuple

from domain.entities import Match
from domain.enums import Region, QueueType
from infrastructure import MatchRepository, SummonerRepository
from application.services.seed import SeedDiscoveryService
from config import settings

logger = logging.getLogger(__name__)


class DataScraperService:
    """
    Scrapes matches for one region+queue until max_matches is reached.

    Design:
    - Maintains a puuid_queue (FIFO).
    - Pops batches of MAX_CONCURRENT_REQUESTS puuids, fetches their
      match IDs, downloads match details concurrently.
    - Newly discovered participant PUUIDs are appended to the queue.
    - When the queue runs dry it asks SeedDiscoveryService for more.
    - Never returns early unless truly exhausted after multiple retries.
    """

    def __init__(
        self,
        match_repo: MatchRepository,
        summoner_repo: SummonerRepository,
        progress_callback=None,
        status_callback=None,
        seed_service: SeedDiscoveryService | None = None,
    ):
        self.match_repo     = match_repo
        self.summoner_repo  = summoner_repo
        self.progress_cb    = progress_callback
        self.status_cb      = status_callback
        self._match_sem     = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)
        self.seed_service   = seed_service or SeedDiscoveryService(
            self.match_repo.api_client, self.summoner_repo
        )

        # These are shared with the use-case (assigned after __init__)
        self.scraped_match_ids: Set[str] = set()
        self.scraped_puuids:    Set[str] = set()
        self.processed_puuids:  Set[str] = set()

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    async def scrape_matches_by_date_window(
        self,
        region: Region,
        queue_type: QueueType,
        max_matches: Optional[int] = None,
        seed_puuids: Optional[List[str]] = None,
    ) -> List[Match]:
        """Run until max_matches collected or all sources exhausted."""

        # Add caller-supplied seeds
        if seed_puuids:
            for p in seed_puuids:
                if p and p not in self.scraped_puuids:
                    self.scraped_puuids.add(p)

        # Build initial queue from unprocessed known puuids
        puuid_queue: List[str] = self._fresh_puuids()

        # Bootstrap if empty
        if not puuid_queue:
            puuid_queue = await self._bootstrap(region, queue_type)
            if not puuid_queue:
                raise ValueError(
                    "No seed PUUIDs available. "
                    "Set SEED_PUUIDS / SEED_SUMMONERS or run once to populate DB."
                )

        matches:      List[Match] = []
        empty_rounds: int         = 0
        MAX_EMPTY                 = 5   # give up after 5 consecutive dry rounds

        while True:
            # ── stop condition ────────────────────────────────────────
            if max_matches is not None and len(matches) >= max_matches:
                break

            # ── refill queue if needed ────────────────────────────────
            if not puuid_queue:
                empty_rounds += 1
                if empty_rounds >= MAX_EMPTY:
                    logger.warning(
                        f"Exhausted after {MAX_EMPTY} dry rounds "
                        f"({region.value}/{queue_type.queue_name}). "
                        f"Collected {len(matches)}/{max_matches}."
                    )
                    break
                logger.debug(f"Queue dry ({empty_rounds}/{MAX_EMPTY}), fetching seeds…")
                fresh = await self.seed_service.discover_seed_puuids(
                    region, queue_type, count=50
                )
                for p in fresh:
                    if p not in self.scraped_puuids and p not in self.processed_puuids:
                        self.scraped_puuids.add(p)
                        puuid_queue.append(p)
                if not puuid_queue:
                    continue   # try again (up to MAX_EMPTY times)
                # Seeds found → reset counter
                empty_rounds = 0

            # ── pop a batch ───────────────────────────────────────────
            batch_size = min(settings.MAX_CONCURRENT_REQUESTS, len(puuid_queue))
            batch      = [puuid_queue.pop(0) for _ in range(batch_size)]

            room  = max(1, max_matches - len(matches)) if max_matches is not None else settings.MATCHES_PER_SUMMONER
            limit = min(settings.MATCHES_PER_SUMMONER, room)

            tasks   = [self._scrape_puuid(region, p, queue_type, limit) for p in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_new = 0
            for res in results:
                if isinstance(res, Exception) or not res:
                    continue
                new_matches, new_puuids = res

                cap    = (max_matches - len(matches)) if max_matches is not None else len(new_matches)
                chunk  = new_matches[:max(0, cap)]
                matches.extend(chunk)
                batch_new += len(chunk)

                if self.progress_cb:
                    self.progress_cb(len(matches), 0)
                if self.status_cb:
                    self.status_cb(self.match_repo.api_client.last_status_code)

                # Enqueue newly discovered participant PUUIDs
                for p in new_puuids:
                    if p not in self.scraped_puuids and p not in self.processed_puuids:
                        self.scraped_puuids.add(p)
                        puuid_queue.append(p)

                if max_matches is not None and len(matches) >= max_matches:
                    break

            # A batch that yielded nothing at all counts toward empty rounds
            if batch_new == 0:
                empty_rounds += 1
            else:
                empty_rounds = 0

        return matches

    # ------------------------------------------------------------------ #
    # Per-PUUID worker
    # ------------------------------------------------------------------ #

    async def _scrape_puuid(
        self,
        region: Region,
        puuid: str,
        queue_type: QueueType,
        limit: int,
    ) -> Optional[Tuple[List[Match], List[str]]]:
        if puuid in self.processed_puuids:
            return None
        self.processed_puuids.add(puuid)

        try:
            start_time, end_time = self._patch_time_range()
            match_ids = await self.match_repo.get_match_ids_by_puuid(
                region=region,
                puuid=puuid,
                queue_type=queue_type,
                start_time=start_time,
                end_time=end_time,
                start=0,
                count=min(settings.IDS_PER_PUUID, limit),
            )
            if not match_ids:
                return ([], [])

            new_ids = [m for m in match_ids if m not in self.scraped_match_ids]
            if not new_ids:
                return ([], [])

            return await self._fetch_match_details(region, new_ids[:limit])

        except Exception as exc:
            logger.error(f"Error scraping PUUID {puuid}: {exc}")
            return None

    async def _fetch_match_details(
        self, region: Region, match_ids: List[str]
    ) -> Tuple[List[Match], List[str]]:
        tasks   = [self._get_match(region, mid) for mid in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        matches:    List[Match] = []
        new_puuids: List[str]   = []
        target_patch = (settings.TARGET_PATCH or "").lower()

        for mid, match in zip(match_ids, results):
            if isinstance(match, Exception) or not match:
                continue
            pv = (getattr(match, "patch_version", "") or "").lower()
            if target_patch and target_patch not in ("any", "all", "*"):
                if not (pv == target_patch or pv.startswith(target_patch)):
                    continue
            self.scraped_match_ids.add(mid)
            matches.append(match)
            for participant in match.participants:
                p = participant.puuid
                if p and p not in self.scraped_puuids:
                    new_puuids.append(p)

        return (matches, new_puuids)

    async def _get_match(self, region: Region, mid: str):
        async with self._match_sem:
            return await self.match_repo.get_match_by_id(region, mid)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _fresh_puuids(self) -> List[str]:
        """Return known puuids not yet processed."""
        return [p for p in self.scraped_puuids if p not in self.processed_puuids]

    async def _bootstrap(self, region: Region, queue_type: QueueType) -> List[str]:
        """Try every seed source in order."""
        queue: List[str] = []

        # 1. SEED_SUMMONERS env var
        raw_names = settings.SEED_SUMMONERS
        if raw_names:
            names   = [n.strip() for n in raw_names.split(",") if n.strip()]
            results = await asyncio.gather(
                *[self.summoner_repo.get_summoner_by_name(region, n) for n in names],
                return_exceptions=True,
            )
            for r in results:
                if not isinstance(r, Exception) and r:
                    p = r.puuid
                    if p and p not in self.scraped_puuids:
                        self.scraped_puuids.add(p)
                        queue.append(p)

        # 2. SEED_PUUIDS env var
        if not queue:
            for p in (settings.SEED_PUUIDS or "").split(","):
                p = p.strip()
                if p and p not in self.scraped_puuids:
                    self.scraped_puuids.add(p)
                    queue.append(p)

        # 3. League discovery
        if not queue:
            discovered = await self.seed_service.discover_seed_puuids(
                region, queue_type, count=50
            )
            for p in discovered:
                if p not in self.scraped_puuids:
                    self.scraped_puuids.add(p)
                    queue.append(p)

        return queue

    def _patch_time_range(self):
        day = settings.SCRAPE_DATE
        if day:
            try:
                d = datetime.strptime(day, "%Y-%m-%d")
                return int(d.timestamp()), int((d + timedelta(days=1)).timestamp())
            except Exception:
                pass
        start = int(datetime.strptime(settings.PATCH_START_DATE, "%Y-%m-%d").timestamp())
        end   = None
        if settings.PATCH_END_DATE:
            end = int(datetime.strptime(settings.PATCH_END_DATE, "%Y-%m-%d").timestamp())
        return start, end

    # ------------------------------------------------------------------ #
    # Kept for backwards compatibility (unbounded mode)
    # ------------------------------------------------------------------ #

    async def scrape_matches_unbounded(
        self,
        region: Region,
        queue_type: QueueType,
        max_matches: Optional[int] = None,
    ) -> List[Match]:
        matches:    List[Match] = []
        puuid_queue = self._fresh_puuids()
        if not puuid_queue:
            raise ValueError("No seed PUUIDs for unbounded scrape.")

        while puuid_queue:
            if max_matches is not None and len(matches) >= max_matches:
                break
            batch_size  = min(settings.MAX_CONCURRENT_REQUESTS, len(puuid_queue))
            batch       = [puuid_queue.pop(0) for _ in range(batch_size)]
            limit       = min(settings.MATCHES_PER_SUMMONER, max(1, (max_matches - len(matches)) if max_matches else settings.MATCHES_PER_SUMMONER))
            tasks       = [self._scrape_puuid(region, p, queue_type, limit) for p in batch]
            results     = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception) or not res:
                    continue
                new_matches, new_puuids = res
                room = max(0, max_matches - len(matches)) if max_matches is not None else len(new_matches)
                matches.extend(new_matches[:room])
                for p in new_puuids:
                    if p not in self.scraped_puuids and p not in self.processed_puuids:
                        self.scraped_puuids.add(p)
                        puuid_queue.append(p)
            if max_matches is not None and len(matches) >= max_matches:
                break
        return matches