from __future__ import annotations

from typing import List
import asyncio
import os
import random
import socket
from config import settings
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient, SummonerRepository
from application.use_cases import ScrapeMatchesUseCase
from application.services.data_persistence_service import DataPersistenceService
from application.services.seed import SeedDiscoveryService
from core.logging.logger import get_logger


class ScrapingCommand:
    """Scraping command with progress UI and SEA DNS safeguards."""

    def __init__(self) -> None:
        self._target = settings.MATCHES_PER_REGION
        self._log = get_logger(__name__, service="scrape-cli")

    def _print_banner(self) -> None:
        print("""
╔═════════════════════════════════════════╗
║                                         ║
║    RIOT GAMES LOL RANKED GAMES DATA SCRAPER - PATCH {patch}
║                                         ║
╚═════════════════════════════════════════╝
        """.format(patch=settings.TARGET_PATCH))

    def _print_summary(self, regions: List[Region], queues: List[QueueType]) -> None:
        print("\n" + "="*57)
        print("CONFIGURATION SUMMARY")
        print("="*57)
        if len(regions) == 1:
            print(f"Server: {regions[0].friendly}")
        else:
            print(f"Servers: {', '.join(r.friendly for r in regions)}")
        print(f"Queue Types: {', '.join(q.queue_name for q in queues)}")
        print(f"Patch Version: {settings.TARGET_PATCH}")
        print("="*57)
        print("\nStarting data collection...\n")

    def _make_progress_cb(self, region_target: int, label: str):
        width = 30
        def _progress(current: int, denom: int) -> None:
            total = denom if isinstance(denom, int) and denom > 0 else region_target
            cur = max(0, int(current or 0))
            if total:
                cur = min(cur, total)
                filled = int(width * (cur / total))
            else:
                filled = 0
            bar = "█" * filled + "-" * (width - filled)
            if total:
                print(f"\r{label} | {bar} | {cur}/{total}", end="", flush=True)
            else:
                print(f"\r{label} | {bar} | {cur}", end="", flush=True)
        return _progress

    @staticmethod
    def _dns_resolves(host: str) -> bool:
        try:
            socket.getaddrinfo(host, None)
            return True
        except Exception:
            return False

    @staticmethod
    def _sea_platform_candidates(region: Region) -> List[str]:
        if region.regional_route == "sea":
            order = [region.platform_route, "sg2", "th2", "tw2", "vn2", "oc1"]
            seen = set()
            return [h for h in order if not (h in seen or seen.add(h))]
        return [region.platform_route]

    async def run(self) -> None:
        settings.validate()
        settings.create_directories()
        self._log.info("start")
        env_regions = os.getenv("REGIONS", "").strip().lower()
        if env_regions and env_regions != "all":
            codes = [c.strip() for c in env_regions.split(",") if c.strip()]
            all_map = {r.value: r for r in Region.all_regions()}
            regions = [all_map[c] for c in codes if c in all_map] or Region.all_regions()
        else:
            regions = Region.all_regions()
        queues = QueueType.ranked_queues()

        db_path = settings.DB_DIR / "scraper.sqlite"
        p = DataPersistenceService(db_path)
        try:
            p.seed_static_data()
        except Exception:
            pass

        self._print_banner()
        self._print_summary(regions, queues)

        async with RiotAPIClient(settings.RIOT_API_KEY) as api:
            total_all = 0

            for idx, region in enumerate(regions):
                if region.value.lower() in settings.DISABLED_REGIONS:
                    print(f"Skipping disabled region: {region.friendly}")
                    continue

                if settings.RANDOM_SCRAPE:
                    rt_min = max(1, settings.RANDOM_REGION_TARGET_MIN)
                    rt_max = max(rt_min, settings.RANDOM_REGION_TARGET_MAX)
                    region_target = random.randint(rt_min, rt_max)
                else:
                    region_target = settings.MATCHES_PER_REGION
                self._target = region_target
                print("")
                print(f"Server: {region.friendly}", flush=True)
                self._log.info(f"region-start {region.value}")
                if idx + 1 < len(regions):
                    print(f"Next Server: {regions[idx + 1].friendly}", flush=True)

                progress_cb = self._make_progress_cb(region_target, region.value)
                use_case = ScrapeMatchesUseCase(api, progress_callback=progress_cb, status_callback=lambda _: None)

                # SEA DNS safeguard
                candidates = self._sea_platform_candidates(region)
                platform_ok = any(self._dns_resolves(f"{h}.api.riotgames.com") for h in candidates)
                regional_ok = self._dns_resolves(f"{region.regional_route}.api.riotgames.com")
                seeds_configured = bool(settings.SEED_PUUIDS or settings.SEED_SUMMONERS)

                if region.regional_route == "sea" and not platform_ok:
                    if not regional_ok:
                        print(f"DNS check failed for SEA platform and regional hosts for {region.friendly}. Skipping this server.", flush=True)
                        self._log.warning(f"dns-skip-sea-all {region.value}")
                        continue
                    if not seeds_configured:
                        print(f"DNS platform check failed for {region.friendly}. Provide SEED_PUUIDS or SEED_SUMMONERS to proceed via regional route. Skipping.", flush=True)
                        self._log.warning(f"dns-skip-sea-no-seeds {region.value}")
                        continue
                    else:
                        self._log.info(f"sea-platform-down-using-seeds {region.value}")
                else:
                    self._log.info(f"platform-ok {region.value}")

                seed_map = None
                try:
                    seed_service = SeedDiscoveryService(api, SummonerRepository(api))
                    unique_seeds = []
                    try:
                        db_seeds = p.get_existing_puuids()
                        for s in db_seeds[:50]:
                            if s and s not in unique_seeds:
                                unique_seeds.append(s)
                    except Exception:
                        pass
                    for q in queues:
                        extra = await seed_service.discover_seed_puuids(region, q, count=50)
                        for p in extra:
                            if p and p not in unique_seeds:
                                unique_seeds.append(p)
                    if unique_seeds:
                        seed_map = {region: unique_seeds}
                except Exception:
                    seed_map = None
                results = await use_case.execute(
                    regions=[region],
                    queue_types=queues,
                    matches_per_region=region_target,
                    matches_total=None,
                    seed_puuids_by_region=seed_map
                )

                region_matches = []
                for region_data in results.values():
                    for matches in region_data.values():
                        region_matches.extend(matches)
                total_all += len(region_matches)
                self._log.success(f"region-complete {region.value} count={len(region_matches)}")
                print("")
                print(f"\nData collection complete for {region.value}! Collected {len(region_matches)} matches")
                print("Saving matches to database...")
                p.save_raw_matches(region_matches)
                print("Exporting tables to CSV...")
                p.export_tables_csv(settings.CSV_DIR)

            self._log.info(f"all-done total={total_all}")
            print(f"\nAll done! Total collected: {total_all}. Check the 'data/db' and 'data/csv' directories for results.")

    def _choose_regions_ui(self) -> List[Region]:
        regions = Region.all_regions()
        rows = [(r, r.platform_route, r.friendly, r.regional_route) for r in regions]
        print("\nSelect servers to scrape:")
        for i, (_, plat, friendly, reg) in enumerate(rows, start=1):
            print(f"{i:2d}) {plat:<4} {friendly} [{reg}]")
        print("\nEnter numbers separated by commas (e.g., 1,3,10)")
        print("Type 'all' to scrape all servers, 'sea' for SEA only, or '0' to cancel.")
        sel = input("Select: ").strip().lower()
        if not sel or sel == "0":
            return []
        if sel == "all":
            return [r for r, *_ in rows]
        if sel == "sea":
            return [r for r, plat, _, reg in rows if reg == "sea"]
        chosen: List[Region] = []
        parts = [p.strip() for p in sel.split(",") if p.strip()]
        for p in parts:
            try:
                i = int(p)
                if 1 <= i <= len(rows):
                    region = rows[i - 1][0]
                    if region not in chosen:
                        chosen.append(region)
            except Exception:
                continue
        return chosen

