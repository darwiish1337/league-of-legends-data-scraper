"""Scraping CLI command - spinner, accurate progress bar, NO logo (shown in main menu only)."""
from __future__ import annotations

import asyncio
import os
import random
import shutil
import socket
import time
from typing import List, Optional, Dict

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

_DIVIDER_CHAR = "═"

# ── Region lookup — hardcoded for reliability ─────────────────────────────────
# Maps every reasonable short code → platform_route value (lowercase)
_REGION_ALIASES: Dict[str, str] = {
    # short      platform_route
    "euw":       "euw1",
    "euw1":      "euw1",
    "eune":      "eun1",
    "eun1":      "eun1",
    "na":        "na1",
    "na1":       "na1",
    "br":        "br1",
    "br1":       "br1",
    "lan":       "la1",
    "la1":       "la1",
    "las":       "la2",
    "la2":       "la2",
    "kr":        "kr",
    "jp":        "jp1",
    "jp1":       "jp1",
    "oce":       "oc1",
    "oc1":       "oc1",
    "ph":        "ph2",
    "ph2":       "ph2",
    "sg":        "sg2",
    "sg2":       "sg2",
    "th":        "th2",
    "th2":       "th2",
    "tw":        "tw2",
    "tw2":       "tw2",
    "vn":        "vn2",
    "vn2":       "vn2",
    "tr":        "tr1",
    "tr1":       "tr1",
    "ru":        "ru",
    "me":        "me1",
    "me1":       "me1",
}


def _parse_regions(env_str: str) -> List[Region]:
    """Parse REGIONS env var into Region objects using flexible alias matching."""
    codes    = [c.strip().lower() for c in env_str.split(",") if c.strip()]
    plat_map = {r.platform_route.lower(): r for r in Region.all_regions()}
    # also add r.value.lower() as key
    for r in Region.all_regions():
        plat_map[r.value.lower()] = r

    regions: List[Region] = []
    unmatched: List[str]  = []

    for code in codes:
        # direct hit
        region = plat_map.get(code)
        # try alias
        if region is None:
            plat = _REGION_ALIASES.get(code)
            if plat:
                region = plat_map.get(plat)
        if region is not None:
            if region not in regions:
                regions.append(region)
        else:
            unmatched.append(code)

    if unmatched:
        print(f"  {_y('WARNING: unknown region codes skipped:')} {', '.join(unmatched)}")

    return regions


# ── Progress bar / spinner ────────────────────────────────────────────────────
_SPIN_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]


class _RegionProgress:
    def __init__(self, target: int, label: str) -> None:
        self.target   = max(1, target)
        self.label    = label
        self._start   = time.monotonic()
        self._current = 0
        self._spin_i  = 0

    def update(self, current: int) -> None:
        new = max(self._current, int(current or 0))
        if new > self.target:
            self.target = new
        self._current = new
        self._render()

    def finish(self) -> None:
        self._current = self.target
        self._render()
        print()

    def _render(self) -> None:
        try:
            cols = shutil.get_terminal_size(fallback=(80, 20)).columns
        except Exception:
            cols = 80
        elapsed = max(0.0, time.monotonic() - self._start)

        if self._current == 0:
            frame = _SPIN_FRAMES[self._spin_i % len(_SPIN_FRAMES)]
            self._spin_i += 1
            msg = (f"  {_CYAN}{self.label}{_RESET} │"
                   f" {_g(frame)} {_DIM}discovering seeds…{_RESET}"
                   f" {_y(f'{int(elapsed)}s')}")
            print(f"\r{msg:<{cols}}", end="", flush=True)
        else:
            pct     = self._current / self.target
            eta_s   = int(elapsed * (1.0 - pct) / pct) if pct > 0 else 0
            mm, ss  = divmod(eta_s, 60)
            hh, mm  = divmod(mm, 60)
            eta_str = f"ETA {hh:02d}:{mm:02d}:{ss:02d}" if hh else f"ETA {mm:02d}:{ss:02d}"
            info    = f"{self._current:,}/{self.target:,}  {int(pct*100):3d}%  {eta_str}"

            prefix_len = 2 + len(self.label) + 1
            bar_space  = max(10, min(50, cols - prefix_len - len(info) - 6))
            filled     = int(bar_space * pct)
            bar        = _g("█" * filled) + _DIM + "─" * (bar_space - filled) + _RESET
            print(f"\r  {_CYAN}{self.label}{_RESET} │{bar}│ {_y(info)}", end="", flush=True)


async def _tick_spinner(prog: _RegionProgress, interval: float = 0.12) -> None:
    while prog._current == 0:
        prog._render()
        await asyncio.sleep(interval)


# ── Main command ──────────────────────────────────────────────────────────────

class ScrapingCommand:

    def __init__(self) -> None:
        self._target   = settings.MATCHES_PER_REGION
        self._log      = get_logger(__name__, service="scrape-cli")
        self._progress: Optional[_RegionProgress] = None

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

    def _make_progress_cb(self, region_target: int, label: str):
        prog = _RegionProgress(region_target, label)
        self._progress = prog
        def _cb(current: int, _total: int) -> None:
            prog.update(current)
        return _cb

    @staticmethod
    def _dns_resolves(host: str) -> bool:
        try:
            socket.getaddrinfo(host, None)
            return True
        except Exception:
            return False

    @staticmethod
    def _sea_candidates(region: Region) -> List[str]:
        if region.regional_route == "sea":
            order = [region.platform_route, "sg2", "th2", "tw2", "vn2", "oc1"]
            seen: set = set()
            return [h for h in order if not (h in seen or seen.add(h))]  # type: ignore
        return [region.platform_route]

    async def run(self) -> None:
        settings.validate()
        settings.create_directories()
        self._log.info("start")

        # ── Parse regions ──────────────────────────────────────────────────
        env_regions = os.getenv("REGIONS", "").strip().lower()
        if env_regions and env_regions != "all":
            regions = _parse_regions(env_regions)
            if not regions:
                print(f"  {_y('No valid regions found in REGIONS env — using all regions')}")
                regions = Region.all_regions()
        else:
            regions = Region.all_regions()

        queues = QueueType.ranked_queues()

        db_path     = settings.DB_DIR / "scraper.sqlite"
        persistence = DataPersistenceService(db_path)

        # ── Print config (NO logo here — already shown in main menu) ───────
        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div  = _DIVIDER_CHAR * min(cols, 96)
        print()
        print(f"  {_BOLD}Patch:{_RESET}  {_g(settings.TARGET_PATCH)}"
              f"   {_DIM}|{_RESET}  "
              f"{_BOLD}Date range:{_RESET}  {_c(settings.PATCH_START_DATE)}"
              + (f" → {_c(settings.PATCH_END_DATE)}" if settings.PATCH_END_DATE else ""))
        print(_g(div))

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

                region_target = (
                    random.randint(
                        max(1, settings.RANDOM_REGION_TARGET_MIN),
                        max(1, settings.RANDOM_REGION_TARGET_MAX),
                    )
                    if settings.RANDOM_SCRAPE
                    else settings.MATCHES_PER_REGION
                )
                self._target = region_target

                cols     = shutil.get_terminal_size(fallback=(96, 20)).columns
                next_txt = (f"   {_DIM}next → {regions[idx+1].friendly}{_RESET}"
                            if idx + 1 < len(regions) else "")
                print(f"\n{'─' * min(cols, 60)}")
                print(f"  {_BOLD}Server:{_RESET} {_g(region.friendly)}{next_txt}")
                print(f"  Target : {_c(f'{region_target:,} matches')}")

                # DNS check
                candidates  = self._sea_candidates(region)
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

                # Region-specific seeds from DB only (no blocking API calls)
                db_seeds: List[str] = []
                try:
                    db_seeds = persistence.get_existing_puuids_for_region(region.value)[:200]
                except Exception:
                    pass
                seed_map = {region: db_seeds} if db_seeds else None

                progress_cb = self._make_progress_cb(region_target, region.value.upper())
                use_case    = ScrapeMatchesUseCase(
                    api,
                    progress_callback=progress_cb,
                    status_callback=lambda _: None,
                )

                prog = self._progress

                async def _run_with_spinner():
                    spinner = asyncio.create_task(_tick_spinner(prog))
                    try:
                        return await use_case.execute(
                            regions=[region],
                            queue_types=queues,
                            matches_per_region=region_target,
                            matches_total=None,
                            seed_puuids_by_region=seed_map,
                        )
                    finally:
                        spinner.cancel()
                        try:
                            await spinner
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