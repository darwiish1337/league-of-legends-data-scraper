"""Scraping CLI command - logo, animated spinner, accurate progress bar."""
from __future__ import annotations

import asyncio
import os
import random
import shutil
import socket
import time
from typing import List, Optional

from config import settings
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient, SummonerRepository
from application.use_cases import ScrapeMatchesUseCase
from application.services.data_persistence_service import DataPersistenceService
from application.services.seed import SeedDiscoveryService
from core.logging.logger import get_logger

# ── ANSI ─────────────────────────────────────────────────────────────────────
_BRIGHT_GREEN = "\033[1;92m"
_CYAN         = "\033[96m"
_YELLOW       = "\033[93m"
_RESET        = "\033[0m"
_BOLD         = "\033[1m"
_DIM          = "\033[2m"

def _g(s: str) -> str: return f"{_BRIGHT_GREEN}{s}{_RESET}"
def _c(s: str) -> str: return f"{_CYAN}{s}{_RESET}"
def _y(s: str) -> str: return f"{_YELLOW}{s}{_RESET}"

# ── Logo ──────────────────────────────────────────────────────────────────────
_LOGO = r"""
  ██████╗ ██╗ ██████╗ ████████╗    ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗
  ██╔══██╗██║██╔═══██╗╚══██╔══╝    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
  ██████╔╝██║██║   ██║   ██║       ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
  ██╔══██╗██║██║   ██║   ██║       ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
  ██║  ██║██║╚██████╔╝   ██║       ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
  ╚═╝  ╚═╝╚═╝ ╚═════╝    ╚═╝       ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
"""
_SUBTITLE     = "  League of Legends Ranked Match Data Collector"
_DIVIDER_CHAR = "═"

def _print_logo() -> None:
    cols = shutil.get_terminal_size(fallback=(100, 20)).columns
    div  = _DIVIDER_CHAR * min(cols, 96)
    print(_g(div))
    for line in _LOGO.splitlines():
        print(_g(line))
    print(_c(_SUBTITLE))
    print(_g(div))


# ── Spinner (shown while count == 0) ─────────────────────────────────────────
_SPIN_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

class _RegionProgress:
    """
    Progress bar that animates a spinner while current == 0 (warm-up / seed
    discovery phase) so the terminal never looks frozen.
    """

    def __init__(self, target: int, label: str) -> None:
        self.target   = max(1, target)
        self.label    = label
        self._start   = time.monotonic()
        self._current = 0
        self._spin_i  = 0
        self._spin_task: Optional[asyncio.Task] = None

    # called by the async scrape loop
    def update(self, current: int) -> None:
        new = max(self._current, int(current or 0))
        if new > self.target:
            self.target = new
        self._current = new
        self._render()

    def finish(self) -> None:
        self._current = self.target
        self._render()
        print()   # newline after bar

    def _render(self) -> None:
        try:
            cols = shutil.get_terminal_size(fallback=(80, 20)).columns
        except Exception:
            cols = 80

        elapsed = max(0.0, time.monotonic() - self._start)

        if self._current == 0:
            # ── spinner mode ──────────────────────────────────────────
            frame = _SPIN_FRAMES[self._spin_i % len(_SPIN_FRAMES)]
            self._spin_i += 1
            elapsed_str = f"{int(elapsed)}s"
            msg = (
                f"  {_CYAN}{self.label}{_RESET} │"
                f" {_g(frame)} {_DIM}discovering seeds…{_RESET}"
                f" {_y(elapsed_str)}"
            )
            print(f"\r{msg:<{cols}}", end="", flush=True)
        else:
            # ── bar mode ──────────────────────────────────────────────
            pct = self._current / self.target
            if pct > 0:
                eta_s = int(elapsed * (1.0 - pct) / pct)
            else:
                eta_s = 0
            mm, ss = divmod(eta_s, 60)
            hh, mm = divmod(mm, 60)
            eta_str = f"ETA {hh:02d}:{mm:02d}:{ss:02d}" if hh else f"ETA {mm:02d}:{ss:02d}"
            info    = f"{self._current:,}/{self.target:,}  {int(pct*100):3d}%  {eta_str}"

            prefix_len = 2 + len(self.label) + 1
            bar_space  = max(10, min(50, cols - prefix_len - len(info) - 6))
            filled     = int(bar_space * pct)
            bar        = _g("█" * filled) + _DIM + "─" * (bar_space - filled) + _RESET
            prefix     = f"  {_CYAN}{self.label}{_RESET} "
            line       = f"\r{prefix}│{bar}│ {_y(info)}"
            print(line, end="", flush=True)


# ── Async spinner ticker ──────────────────────────────────────────────────────

async def _tick_spinner(prog: _RegionProgress, interval: float = 0.12) -> None:
    """Keep the spinner animating while seeds are being discovered."""
    while prog._current == 0:
        prog._render()
        await asyncio.sleep(interval)


# ── Main command ──────────────────────────────────────────────────────────────

class ScrapingCommand:

    def __init__(self) -> None:
        self._target   = settings.MATCHES_PER_REGION
        self._log      = get_logger(__name__, service="scrape-cli")
        self._progress: Optional[_RegionProgress] = None

    # ── banners ───────────────────────────────────────────────────────

    def _print_banner(self) -> None:
        _print_logo()
        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div  = _DIVIDER_CHAR * min(cols, 96)
        print()
        patch_range = f"  {_BOLD}Patch:{_RESET}  {_g(settings.TARGET_PATCH)}   {_DIM}|{_RESET}  {_BOLD}Date range:{_RESET}  {_c(settings.PATCH_START_DATE)}"
        if settings.PATCH_END_DATE:
            patch_range += f" → {_c(settings.PATCH_END_DATE)}"
        print(patch_range)
        print(_g(div))

    def _print_summary(self, regions: List[Region], queues: List[QueueType]) -> None:
        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div  = "─" * min(cols, 60)
        print(f"\n{_g(div)}")
        print(f"  {_BOLD}CONFIGURATION SUMMARY{_RESET}")
        print(_g(div))
        region_str = regions[0].friendly if len(regions) == 1 else f"{len(regions)} servers"
        print(f"  Servers     : {_c(region_str)}")
        print(f"  Queues      : {_c(', '.join(q.queue_name for q in queues))}")
        print(f"  Patch       : {_c(settings.TARGET_PATCH)}")
        print(f"  Target/srv  : {_c(f'{self._target:,}')}")
        print(_g(div))
        print()

    # ── progress helpers ──────────────────────────────────────────────

    def _make_progress_cb(self, region_target: int, label: str):
        prog = _RegionProgress(region_target, label)
        self._progress = prog

        def _cb(current: int, _total: int) -> None:
            prog.update(current)

        return _cb

    # ── DNS helpers ───────────────────────────────────────────────────

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
            seen: set = set()
            return [h for h in order if not (h in seen or seen.add(h))]  # type: ignore
        return [region.platform_route]

    # ── main run ──────────────────────────────────────────────────────

    async def run(self) -> None:
        settings.validate()
        settings.create_directories()
        self._log.info("start")

        env_regions = os.getenv("REGIONS", "").strip().lower()
        if env_regions and env_regions != "all":
            codes   = [c.strip() for c in env_regions.split(",") if c.strip()]
            all_map = {r.value: r for r in Region.all_regions()}
            regions = [all_map[c] for c in codes if c in all_map] or Region.all_regions()
        else:
            regions = Region.all_regions()

        queues = QueueType.ranked_queues()

        db_path     = settings.DB_DIR / "scraper.sqlite"
        persistence = DataPersistenceService(db_path)   # schema only, no network

        self._print_banner()
        self._print_summary(regions, queues)

        # seed_static_data in background — never blocks scrape
        async def _seed_bg() -> None:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, persistence.seed_static_data)
            except Exception:
                pass

        asyncio.create_task(_seed_bg())

        async with RiotAPIClient(settings.RIOT_API_KEY) as api:
            total_all = 0

            for idx, region in enumerate(regions):
                if region.value.lower() in settings.DISABLED_REGIONS:
                    print(f"  {_y('Skipping disabled:')} {region.friendly}")
                    continue

                if settings.RANDOM_SCRAPE:
                    rt_min        = max(1, settings.RANDOM_REGION_TARGET_MIN)
                    rt_max        = max(rt_min, settings.RANDOM_REGION_TARGET_MAX)
                    region_target = random.randint(rt_min, rt_max)
                else:
                    region_target = settings.MATCHES_PER_REGION
                self._target = region_target

                cols = shutil.get_terminal_size(fallback=(96, 20)).columns
                print(f"\n{'─' * min(cols, 60)}")
                next_txt = f"   {_DIM}next → {regions[idx+1].friendly}{_RESET}" if idx + 1 < len(regions) else ""
                print(f"  {_BOLD}Server:{_RESET} {_g(region.friendly)}{next_txt}")
                print(f"  Target : {_c(f'{region_target:,} matches')}")

                # DNS check
                candidates  = self._sea_platform_candidates(region)
                platform_ok = any(self._dns_resolves(f"{h}.api.riotgames.com") for h in candidates)
                regional_ok = self._dns_resolves(f"{region.regional_route}.api.riotgames.com")
                seeds_cfg   = bool(settings.SEED_PUUIDS or settings.SEED_SUMMONERS)

                if region.regional_route == "sea" and not platform_ok:
                    if not regional_ok:
                        print(f"  {_y('DNS check failed for SEA. Skipping.')}")
                        self._log.warning(f"dns-skip-sea-all {region.value}")
                        continue
                    if not seeds_cfg:
                        print(f"  {_y('DNS platform failed. Provide SEED_PUUIDS/SEED_SUMMONERS. Skipping.')}")
                        self._log.warning(f"dns-skip-sea-no-seeds {region.value}")
                        continue

                # Only supply already-known PUUIDs — no blocking pre-flight API calls
                db_seeds: List[str] = []
                try:
                    db_seeds = persistence.get_existing_puuids()[:200]
                except Exception:
                    pass
                seed_map = {region: db_seeds} if db_seeds else None

                progress_cb = self._make_progress_cb(region_target, region.value.upper())
                use_case    = ScrapeMatchesUseCase(
                    api,
                    progress_callback=progress_cb,
                    status_callback=lambda _: None,
                )

                # ── Launch spinner + scrape concurrently ──────────────
                # The spinner animates the progress bar while current==0.
                # As soon as the first match arrives the bar switches to
                # normal mode automatically.
                prog = self._progress

                async def _run_with_spinner():
                    spinner_task = asyncio.create_task(_tick_spinner(prog))
                    try:
                        return await use_case.execute(
                            regions=[region],
                            queue_types=queues,
                            matches_per_region=region_target,
                            matches_total=None,
                            seed_puuids_by_region=seed_map,
                        )
                    finally:
                        spinner_task.cancel()
                        try:
                            await spinner_task
                        except asyncio.CancelledError:
                            pass

                results = await _run_with_spinner()

                if self._progress:
                    self._progress.finish()

                region_matches: list = []
                for region_data in results.values():
                    for matches in region_data.values():
                        region_matches.extend(matches)

                total_all += len(region_matches)
                self._log.success(f"region-complete {region.value} count={len(region_matches)}")

                print(f"\n  {_g('✓')} {region.friendly}: {_c(f'{len(region_matches):,}')} matches collected")
                print(f"  Saving to database…", end="", flush=True)
                persistence.save_raw_matches(region_matches)
                print(f" {_g('done')}")
                print(f"  Exporting CSV…", end="", flush=True)
                persistence.export_tables_csv(settings.CSV_DIR)
                print(f" {_g('done')}")

            cols = shutil.get_terminal_size(fallback=(96, 20)).columns
            print(f"\n{_g('═' * min(cols, 96))}")
            print(f"  {_BOLD}All done!{_RESET}  Total: {_g(f'{total_all:,}')} matches")
            print(f"  DB  : {_c(str(settings.DB_DIR))}")
            print(f"  CSV : {_c(str(settings.CSV_DIR))}")
            print(_g("═" * min(cols, 96)))
            self._log.info(f"all-done total={total_all}")