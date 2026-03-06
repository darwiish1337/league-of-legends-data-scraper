"""CLI command for targeted scraping modes."""
from __future__ import annotations

import asyncio
import shutil
from typing import List, Optional

from config import settings
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient
from infrastructure.health import DNSChecker
from application.services import DataPersistenceService, RegionScrapeRunner
from core.logging.logger import get_logger
from .scraping_command import (
    _g,
    _c,
    _y,
    _BOLD,
    _DIM,
    _RESET,
    _RegionProgress,
    _tick_spinner,
)


class TargetedScrapeCommand:
    def __init__(self) -> None:
        self._target = settings.MATCHES_PER_REGION
        self._log = get_logger(__name__, service="target-scrape-cli")
        self._progress: Optional[_RegionProgress] = None

    def _choose_region_ui(self) -> Region:
        regions = Region.all_regions()
        while True:
            print()
            print(f"  {_BOLD}TARGET SERVER SELECTION{_RESET}")
            for idx, region in enumerate(regions, start=1):
                code = region.platform_route.upper()
                friendly = region.friendly
                group = region.regional_route
                line = f"  {idx:2d})  {_c(code):6s} {friendly:<12} [{_DIM}{group}{_RESET}]"
                print(line)
            choice = input("\n  Enter number: ").strip()
            if not choice.isdigit():
                print(f"  {_y('Invalid choice. Enter a number.')}")
                continue
            index = int(choice)
            if index < 1 or index > len(regions):
                print(f"  {_y('Choice out of range.')}")
                continue
            return regions[index - 1]

    def _make_progress_cb(self, target: int, label: str):
        prog = _RegionProgress(target, label)
        self._progress = prog

        def _cb(current: int, _total: int) -> None:
            prog.update(current)

        return _cb

    async def _run_for_regions(self, regions: List[Region]) -> None:
        queues = QueueType.ranked_queues()
        db_path = settings.DB_DIR / "scraper.sqlite"
        persistence = DataPersistenceService(db_path)

        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div = "─" * min(cols, 60)
        print(f"\n{_g(div)}")
        print(f"  {_BOLD}TARGETED SCRAPE CONFIGURATION{_RESET}")
        print(_g(div))
        print(f"  Servers     : {_c(', '.join(r.friendly for r in regions))}")
        print(f"  Queues      : {_c(', '.join(q.queue_name for q in queues))}")
        print(f"  Patch       : {_c(settings.TARGET_PATCH)}")
        print(f"  Target/srv  : {_c(str(self._target))}")
        print(_g(div))
        print()

        async def _seed_bg() -> None:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, persistence.seed_static_data)
            except Exception:
                pass

        asyncio.create_task(_seed_bg())

        async with RiotAPIClient(settings.RIOT_API_KEY) as api:
            runner = RegionScrapeRunner(api, persistence)
            total_all = 0

            for idx, region in enumerate(regions):
                if region.value.lower() in settings.DISABLED_REGIONS:
                    print(f"  {_y('Skipping disabled:')} {region.friendly}")
                    continue

                region_target = self._target
                cols_local = shutil.get_terminal_size(fallback=(96, 20)).columns
                next_txt = (
                    f"   {_DIM}next → {regions[idx+1].friendly}{_RESET}"
                    if idx + 1 < len(regions)
                    else ""
                )
                print(f"\n{'─' * min(cols_local, 60)}")
                print(f"  {_BOLD}Server:{_RESET} {_g(region.friendly)}{next_txt}")
                print(f"  Target : {_c(f'{region_target:,} matches')}")

                candidates = DNSChecker.platform_candidates_for_region(region)
                platform_ok = any(
                    DNSChecker.resolves(f"{h}.api.riotgames.com") for h in candidates
                )
                regional_ok = DNSChecker.resolves(f"{region.regional_route}.api.riotgames.com")
                seeds_cfg = bool(settings.SEED_PUUIDS or settings.SEED_SUMMONERS)

                if region.regional_route == "sea" and not platform_ok:
                    if not regional_ok:
                        print(f"  {_y('DNS check failed for SEA. Skipping.')}")
                        self._log.warning(f"dns-skip-sea-all {region.value}")
                        continue
                    if not seeds_cfg:
                        print(
                            f"  {_y('DNS platform failed. Provide SEED_PUUIDS/SEED_SUMMONERS. Skipping.')}"
                        )
                        self._log.warning(f"dns-skip-sea-no-seeds {region.value}")
                        continue

                progress_cb = self._make_progress_cb(region_target, region.value.upper())
                prog = self._progress

                async def _run_with_spinner():
                    spinner = asyncio.create_task(_tick_spinner(prog))
                    try:
                        return await runner.run_region(
                            region=region,
                            queues=queues,
                            target=region_target,
                            progress_cb=progress_cb,
                        )
                    finally:
                        spinner.cancel()
                        try:
                            await spinner
                        except asyncio.CancelledError:
                            pass

                region_matches = await _run_with_spinner()

                if self._progress:
                    self._progress.finish()

                total_all += len(region_matches)
                self._log.success(
                    f"target-region-complete {region.value} count={len(region_matches)}"
                )

                print(f"\n  {_g('✓')} {region.friendly}: {_c(f'{len(region_matches):,}')} matches collected")
                print("  Saving to database…", end="", flush=True)
                persistence.save_raw_matches(region_matches)
                print(f" {_g('done')}")
                print("  Exporting CSV…", end="", flush=True)
                persistence.export_tables_csv(settings.CSV_DIR)
                print(f" {_g('done')}")

            cols_end = shutil.get_terminal_size(fallback=(96, 20)).columns
            print(f"\n{_g('═' * min(cols_end, 96))}")
            print(f"  {_BOLD}Targeted scrape complete{_RESET}  Total: {_g(f'{total_all:,}')} matches")
            print(f"  DB  : {_c(str(settings.DB_DIR))}")
            print(f"  CSV : {_c(str(settings.CSV_DIR))}")
            print(_g("═" * min(cols_end, 96)))
            self._log.info(f"target-all-done total={total_all}")
        # always close the persistence connection opened for this command
        try:
            persistence._conn.close()
        except Exception:
            pass

    async def _single_server(self) -> None:
        region = self._choose_region_ui()
        await self._run_for_regions([region])

    async def _start_from_server(self) -> None:
        all_regions = Region.all_regions()
        region = self._choose_region_ui()
        try:
            index = all_regions.index(region)
        except ValueError:
            index = 0
        slice_regions = all_regions[index:]
        await self._run_for_regions(slice_regions)

    async def run(self) -> None:
        settings.validate()
        settings.create_directories()
        while True:
            cols = shutil.get_terminal_size(fallback=(96, 20)).columns
            div = "─" * min(cols, 60)
            print(f"\n{_g(div)}")
            print(f"  {_BOLD}TARGETED SCRAPE{_RESET}")
            print(_g(div))
            print(f"  {_c('1')}  Single Server")
            print(f"  {_c('2')}  Start From Server")
            print(f"  {_c('0')}  Back")
            print(_g(div))
            choice = input("  Choose: ").strip()
            if choice == "1":
                await self._single_server()
            elif choice == "2":
                await self._start_from_server()
            elif choice == "0":
                break
            else:
                print(f"  {_y('Invalid option.')}")
