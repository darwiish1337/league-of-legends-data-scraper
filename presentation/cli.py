"""CLI presentation layer for the Riot data scraper."""
from typing import List, Dict
import asyncio
from config import settings
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient, SummonerRepository
from application import ScrapeMatchesUseCase
from application.services import DataPersistenceService
from core.logging.logger import get_logger


class ScraperCLI:
    """Console UI orchestrator respecting single-responsibility and separation of concerns."""
    
    def __init__(self) -> None:
        self._target = settings.MATCHES_PER_REGION
        self._log = get_logger(__name__, service="cli")
    
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
        print(f"Server: {regions[0].friendly}")
        print(f"Queue Types: {', '.join(q.queue_name for q in queues)}")
        print(f"Patch Version: {settings.TARGET_PATCH}")
        print("="*57)
        print("\nStarting data collection...\n")
    
    def _make_progress_cb(self):
        width = 30
        def _progress(current: int, denom: int) -> None:
            total = denom or self._target
            filled = int(width * (current / total)) if total else 0
            bar = "█" * filled + "-" * (width - filled)
            if total:
                print(f"\rStart Scraping Data |{bar}| {current}/{total}", end="", flush=True)
            else:
                print(f"\rStart Scraping Data |{bar}| {current}", end="", flush=True)
        return _progress
    
    async def run(self) -> None:
        settings.validate()
        settings.create_directories()
        self._log.info("start")
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
        
        progress_cb = self._make_progress_cb()
        
        async with RiotAPIClient(settings.RIOT_API_KEY) as api:
            use_case = ScrapeMatchesUseCase(api, progress_callback=progress_cb, status_callback=lambda _: None)
            summoner_repo = SummonerRepository(api)
            total_all = 0
            
            for idx, region in enumerate(regions):
                self._target = settings.MATCHES_PER_REGION
                print("")
                print(f"Server: {region.friendly}", flush=True)
                self._log.info(f"region-start {region.value}")
                if idx + 1 < len(regions):
                    print(f"Next Server: {regions[idx + 1].friendly}", flush=True)
                width = 30
                print(f"Start Scraping Data |{'-'*width}| 0/{self._target}", end="\r", flush=True)
                
                puuids: List[str] = []
                for league_url in ("challenger", "grandmaster"):
                    try:
                        data = await (api.get_challenger_league(region, QueueType.RANKED_SOLO_5x5) if league_url == "challenger"
                                      else api.get_grandmaster_league(region, QueueType.RANKED_SOLO_5x5))
                        entries = (data or {}).get("entries", [])[:5]
                        tasks = []
                        for e in entries:
                            pu = e.get("puuid")
                            if pu:
                                puuids.append(pu)
                                continue
                            sid = e.get("summonerId")
                            name = e.get("summonerName")
                            if sid:
                                tasks.append(summoner_repo.get_summoner_by_id(region, sid))
                            elif name:
                                tasks.append(summoner_repo.get_summoner_by_name(region, name))
                        if tasks:
                            resolved = await asyncio.gather(*tasks, return_exceptions=True)
                            for rv in resolved:
                                if isinstance(rv, Exception) or rv is None:
                                    continue
                                if getattr(rv, "puuid", None):
                                    puuids.append(rv.puuid)
                    except Exception:
                        self._log.warning(f"seed-fetch-failed {region.value}")
                        pass
                    if len(puuids) >= 5:
                        break
                if len(puuids) < 5:
                    try:
                        data = await api.get_challenger_league(region, QueueType.RANKED_FLEX_SR)
                        entries = (data or {}).get("entries", [])[:5 - len(puuids)]
                        tasks = []
                        for e in entries:
                            sid = e.get("summonerId")
                            name = e.get("summonerName")
                            if sid:
                                tasks.append(summoner_repo.get_summoner_by_id(region, sid))
                            elif name:
                                tasks.append(summoner_repo.get_summoner_by_name(region, name))
                        if tasks:
                            resolved = await asyncio.gather(*tasks, return_exceptions=True)
                            for rv in resolved:
                                if isinstance(rv, Exception) or rv is None:
                                    continue
                                if getattr(rv, "puuid", None):
                                    puuids.append(rv.puuid)
                    except Exception:
                        self._log.warning(f"seed-flex-fallback-failed {region.value}")
                        pass
                seeds_for_region = list(dict.fromkeys(puuids))[:5]
                
                results = await use_case.execute(
                    regions=[region],
                    queue_types=queues,
                    matches_per_region=settings.MATCHES_PER_REGION,
                    matches_total=None,
                    seed_puuids_by_region={region: seeds_for_region}
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

