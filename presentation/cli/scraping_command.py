"""Scraping CLI command – runs the main scraping flow from the menu."""
from __future__ import annotations

import asyncio
import os
import random
import re
import shutil
import time
import uuid
from typing import Any, Dict, List, Optional

from config import settings
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient
from infrastructure.health import DNSChecker
from application.services import DataPersistenceService, RegionScrapeRunner
from infrastructure.notifications import Notifier
from core.logging.logger import get_logger

_BRIGHT_GREEN = "\033[1;92m"
_CYAN         = "\033[96m"
_YELLOW       = "\033[93m"
_RESET        = "\033[0m"
_BOLD         = "\033[1m"
_DIM          = "\033[2m"

# Detect if running in test mode and disable Unicode to avoid encoding errors
_TESTING = os.getenv("TESTING", "").lower() == "true"

def _ascii_safe(s: str) -> str:
    """Replace Unicode characters with ASCII equivalents in test mode."""
    if not _TESTING:
        return s
    replacements = {
        '─': '-',
        '┌': '[',
        '└': '[',
        '┐': ']',
        '┘': ']',
        '█': '#',
        '✓': '*',
        '⠋': '.',
        '⠙': '.',
        '⠹': '.',
        '⠸': '.',
        '⠼': '.',
        '⠴': '.',
        '⠦': '.',
        '⠧': '.',
        '⠇': '.',
        '⠏': '.',
    }
    for unicode_char, ascii_char in replacements.items():
        s = s.replace(unicode_char, ascii_char)
    return s

def _g(s: str) -> str: return f"{_BRIGHT_GREEN}{_ascii_safe(s)}{_RESET}"
def _c(s: str) -> str: return f"{_CYAN}{_ascii_safe(s)}{_RESET}"
def _y(s: str) -> str: return f"{_YELLOW}{_ascii_safe(s)}{_RESET}"

_DIVIDER_CHAR = "=" if _TESTING else "═"
_SPIN_FRAMES = ["."] * 10 if _TESTING else ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

_REGION_ALIASES: Dict[str, str] = {
    "euw":  "euw1", "euw1": "euw1",
    "eune": "eun1", "eun1": "eun1",
    "na":   "na1",  "na1":  "na1",
    "br":   "br1",  "br1":  "br1",
    "lan":  "la1",  "la1":  "la1",
    "las":  "la2",  "la2":  "la2",
    "kr":   "kr",
    "jp":   "jp1",  "jp1":  "jp1",
    "oce":  "oc1",  "oc1":  "oc1",
    "ph":   "ph2",  "ph2":  "ph2",
    "sg":   "sg2",  "sg2":  "sg2",
    "th":   "th2",  "th2":  "th2",
    "tw":   "tw2",  "tw2":  "tw2",
    "vn":   "vn2",  "vn2":  "vn2",
    "tr":   "tr1",  "tr1":  "tr1",
    "ru":   "ru",
    "me":   "me1",  "me1":  "me1",
}


def _parse_regions(env_str: str) -> List[Region]:
    codes    = [c.strip().lower() for c in env_str.split(",") if c.strip()]
    plat_map = {r.platform_route.lower(): r for r in Region.all_regions()}
    for r in Region.all_regions():
        plat_map[r.value.lower()] = r
    regions:   List[Region] = []
    unmatched: List[str]    = []
    for code in codes:
        region = plat_map.get(code)
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


class _RegionProgress:
    def __init__(self, target: int, label: str) -> None:
        self.target   = max(1, target)
        self.label    = label
        self._start   = time.monotonic()
        self._current = 0
        self._spin_i  = 0
        self._phase   = "seeds"

    def set_processing(self, *args, **kwargs) -> None:
        # callback used by the scraper when seed PUUIDs are ready; some callers
        # pass (region, count) which previously raised a TypeError. Accept any
        # arguments and ignore them so the CLI does not crash and prematurely
        # skip regions.
        if self._phase == "seeds":
            self._phase = "processing"

    def update(self, current: int) -> None:
        new = max(self._current, int(current or 0))
        if new > self.target:
            self.target = new
        self._current = new
        if new > 0:
            self._phase = "running"
        self._render()

    def finish(self) -> None:
        self._current = self.target
        self._phase   = "running"
        self._render()
        print()

    def _render(self) -> None:
        try:
            cols = shutil.get_terminal_size(fallback=(80, 20)).columns
        except Exception:
            cols = 80
        elapsed = max(0.0, time.monotonic() - self._start)
        
        pipe_char = "|" if _TESTING else "│"
        fill_char = "#" if _TESTING else "█"
        dash_char = "-" if _TESTING else "─"

        if self._phase in ("seeds", "processing"):
            frame  = _SPIN_FRAMES[self._spin_i % len(_SPIN_FRAMES)]
            self._spin_i += 1
            label2 = "discovering seeds…" if self._phase == "seeds" else "processing players…"
            msg    = (f"  {_CYAN}{self.label}{_RESET} {pipe_char}"
                      f" {_g(frame)} {_DIM}{label2}{_RESET}"
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
            bar        = _g(fill_char * filled) + _DIM + dash_char * (bar_space - filled) + _RESET
            # FIX: pad to full terminal width to erase leftover chars from previous render
            line        = f"  {_CYAN}{self.label}{_RESET} {pipe_char}{bar}{pipe_char} {_y(info)}"
            visible_len = len(re.sub(r"\033\[[0-9;]*m", "", line))
            padding     = max(0, cols - visible_len - 1)
            print(f"\r{line}{' ' * padding}", end="", flush=True)


async def _tick_spinner(prog: _RegionProgress, interval: float = 0.12) -> None:
    while prog._phase in ("seeds", "processing"):
        prog._render()
        await asyncio.sleep(interval)


class ScrapingCommand:

    def __init__(self) -> None:
        self._target   = settings.MATCHES_PER_REGION
        self._log      = get_logger(__name__, service="scrape-cli")
        self._progress: Optional[_RegionProgress] = None
        self._notifier = Notifier()

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

    async def run(self) -> None:
        settings.validate()
        settings.create_directories()
        self._log.info("start")

        env_regions = os.getenv("REGIONS", "").strip().lower()
        if env_regions and env_regions != "all":
            regions = _parse_regions(env_regions)
            if not regions:
                print(f"  {_y('No valid regions found in REGIONS env — using all regions')}")
                regions = Region.all_regions()
        else:
            regions = Region.all_regions()

        queues      = QueueType.ranked_queues()
        db_path     = settings.DB_DIR / "scraper.sqlite"
        persistence = DataPersistenceService(db_path)

        session_id:      Optional[str]             = None
        session_regions: Dict[str, Dict[str, Any]] = {}

        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div  = _DIVIDER_CHAR * min(cols, 96)
        print()
        print(f"  {_BOLD}Patch:{_RESET}  {_g(settings.TARGET_PATCH)}"
              f"   {_DIM}|{_RESET}  "
              f"{_BOLD}Date range:{_RESET}  {_c(settings.PATCH_START_DATE)}"
              + (f" → {_c(settings.PATCH_END_DATE)}" if settings.PATCH_END_DATE else ""))
        print(_g(div))

        # ── Resume support ─────────────────────────────────────────────────
        incomplete = persistence.get_incomplete_sessions()
        if incomplete:
            latest   = incomplete[0]
            sess_id  = latest["session_id"]
            reg_rows = persistence.get_session_regions(sess_id)
            # heuristic: if no progress was ever recorded (all matches_collected==0)
            # treat the session as unusable so user doesn't resume a corrupt run.
            has_progress = any(r.get("matches_collected", 0) > 0 for r in reg_rows)
            if not has_progress:
                print(_y("\nNOTE: previous session contains no collected matches – starting fresh\n"))
                # drop the incomplete session and fall through as if none existed
                persistence.update_session_status(sess_id, "interrupted")
                incomplete = []

        if incomplete:
            latest   = incomplete[0]
            sess_id  = latest["session_id"]
            reg_rows = persistence.get_session_regions(sess_id)
            # treat skipped rows as "done" for summary purposes since they will not
            # be re-scraped on resume; this also covers the pre‑patch bug where all
            # regions were erroneously marked skipped.
            done     = [r["region"] for r in reg_rows if r["status"] in ("completed","skipped")]
            cols_box = shutil.get_terminal_size(fallback=(96, 20)).columns
            div_char = "-" if _TESTING else "─"
            div_box  = div_char * min(cols_box, 57)
            
            if _TESTING:
                # ASCII-safe output for test mode
                print(f"\n[={div_box}=]")
                print(f"  INCOMPLETE SESSION FOUND")
            else:
                print(f"\n{_g('┌' + div_box + '┐')}")
                print(f"  {_BOLD}INCOMPLETE SESSION FOUND{_RESET}")
            
            print(f"  Started : {latest['started_at']}  Patch: {latest['patch']}")
            if done:
                preview = ", ".join(done[:3])
                more    = max(0, len(reg_rows) - len(done))
                tail    = f"  ({more} remaining)" if more else ""
                checkmark = "*" if _TESTING else "✓"
                print(f"  Done    : {_g(preview + ' ' + checkmark)}{tail}")
            remaining_count = len([r for r in reg_rows if r["status"] not in ("completed","skipped")])
            print(f"  Pending : {_c(str(remaining_count))} regions")
            print()
            print(f"  {_c('R')}  Resume latest    {_c('N')}  Start fresh    {_c('0')}  Cancel")
            
            if _TESTING:
                print(f"[={div_box}=]")
            else:
                print(_g("└" + div_box + "┘"))
            
            choice = input("  Choose: ").strip().lower()
            if choice == "0":
                return
            elif choice == "r":
                session_id      = sess_id
                session_regions = {r["region"]: r for r in reg_rows}
                # reconstruct the original ordering from the session record (comma list)
                orig_order = [r for r in latest["regions"].split(",") if r]
                # select those regions not yet done/skipped
                regions = [Region[name] for name in orig_order
                           if session_regions.get(name, {}).get("status") not in ("completed","skipped")]
                self._target    = int(latest["target"])
                if not regions:
                    # nothing left to resume – probably an old session where everything
                    # was marked skipped (pre-fix). fall back to starting fresh. make
                    # sure we reset the regions list to the original selection so the
                    # CLI actually runs something.
                    print(f"  {_y('No unfinished regions found – starting a fresh session.')}")
                    session_id = None
                    session_regions = {}
                    regions = Region.all_regions()
            elif choice == "n":
                persistence.update_session_status(sess_id, "interrupted")

        self._print_summary(regions, queues)

        async def _seed_bg() -> None:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, persistence.seed_static_data)
            except Exception:
                pass
        asyncio.create_task(_seed_bg())

        async with RiotAPIClient(settings.RIOT_API_KEY) as api:
            runner      = RegionScrapeRunner(api, persistence)
            total_all   = 0
            started_any = False
            start_ts    = time.monotonic()

            if session_id is None:
                session_id = str(uuid.uuid4())
                persistence.create_session(
                    session_id,
                    [r.name for r in regions],
                    self._target,
                    settings.TARGET_PATCH,
                )

            try:
                for idx, region in enumerate(regions):

                    if region.value.lower() in settings.DISABLED_REGIONS:
                        print(f"  {_y('Skipping disabled:')} {region.friendly}")
                        persistence.mark_region_skipped(session_id, region.name)
                        continue

                    region_info = session_regions.get(region.name)
                    if region_info and region_info.get("status") == "completed":
                        mc = int(region_info.get("matches_collected") or 0)
                        print(f"  {_g('✓')} {region.friendly}  "
                              f"already completed ({mc:,} matches) — skipping")
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
                    arrow_char = ">" if _TESTING else "→"
                    next_txt = (
                        f"   {_DIM}next {arrow_char} {regions[idx+1].friendly}{_RESET}"
                        if idx + 1 < len(regions) else ""
                    )
                    div_char_region = "-" if _TESTING else "─"
                    print(f"\n{div_char_region * min(cols, 60)}")
                    print(f"  {_BOLD}Server:{_RESET} {_g(region.friendly)}{next_txt}")
                    print(f"  Target : {_c(f'{region_target:,} matches')}")

                    candidates  = DNSChecker.platform_candidates_for_region(region)
                    platform_ok = any(
                        DNSChecker.resolves(f"{h}.api.riotgames.com") for h in candidates
                    )
                    regional_ok = DNSChecker.resolves(
                        f"{region.regional_route}.api.riotgames.com"
                    )
                    seeds_cfg = bool(settings.SEED_PUUIDS or settings.SEED_SUMMONERS)

                    if region.regional_route == "sea" and not platform_ok:
                        if not regional_ok:
                            print(f"  {_y('DNS check failed for SEA. Skipping.')}")
                            self._log.warning(f"dns-skip-sea-all {region.value}")
                            persistence.mark_region_skipped(session_id, region.name)
                            continue
                        if not seeds_cfg:
                            print(f"  {_y('DNS platform failed. Provide SEED_PUUIDS/SEED_SUMMONERS. Skipping.')}")
                            self._log.warning(f"dns-skip-sea-no-seeds {region.value}")
                            persistence.mark_region_skipped(session_id, region.name)
                            continue

                    persistence.mark_region_running(session_id, region.name)

                    progress_cb  = self._make_progress_cb(region_target, region.value.upper())
                    prog         = self._progress
                    region_start = time.monotonic()

                    async def _run_with_spinner(
                        _prog=prog, _region=region, _region_target=region_target
                    ):
                        spinner = asyncio.create_task(_tick_spinner(_prog))
                        try:
                            return await runner.run_region(
                                region=_region,
                                queues=queues,
                                target=_region_target,
                                progress_cb=progress_cb,
                                seeds_ready_cb=_prog.set_processing,
                                session_id=session_id,
                            )
                        finally:
                            spinner.cancel()
                            try:
                                await spinner
                            except asyncio.CancelledError:
                                pass

                    try:
                        region_matches = await _run_with_spinner()
                    except Exception as exc:
                        # any failure during a region should abort the overall session
                        # so that remaining servers stay in pending/running state and
                        # we can resume cleanly later. Previously we marked the
                        # region skipped and kept iterating, which meant a long
                        # outage could lead to every region being skipped and the
                        # resume DB state became useless (0 matches all round).
                        self._log.error(f"region-error {region.value} {exc}")
                        # update the session status so it appears in the resume
                        # prompt and we can pick up where we left off. we do not
                        # mark the region skipped, leaving it as 'running' so the
                        # next run will retry it from scratch.
                        persistence.update_session_status(session_id, "interrupted")
                        self._notifier.notify_error(region.value, str(exc))
                        # re‑raise to break out of the region loop and stop the run
                        raise

                    if self._progress:
                        self._progress.finish()

                    elapsed_s   = max(0.0, time.monotonic() - region_start)
                    mm, ss      = divmod(int(elapsed_s), 60)
                    hh, mm      = divmod(mm, 60)
                    elapsed_str = f"{hh}h {mm}m {ss}s" if hh else f"{mm}m {ss}s"

                    total_all   += len(region_matches)
                    started_any  = True
                    self._log.success(
                        f"region-complete {region.value} count={len(region_matches)}"
                    )

                    print(f"\n  {_g('✓')} {region.friendly}: "
                          f"{_c(f'{len(region_matches):,}')} matches collected")
                    print("  Saving to database…", end="", flush=True)
                    persistence.save_raw_matches(region_matches)
                    print(f" {_g('done')}")
                    print("  Exporting CSV…", end="", flush=True)
                    persistence.export_tables_csv(settings.CSV_DIR)
                    print(f" {_g('done')}")

                    persistence.mark_region_completed(
                        session_id, region.name, len(region_matches)
                    )
                    self._notifier.notify_region_complete(
                        region.value, len(region_matches), elapsed_str
                    )

                if started_any:
                    persistence.update_session_status(session_id, "completed")

            except KeyboardInterrupt:
                persistence.update_session_status(session_id, "interrupted")
                self._log.warning("scrape interrupted by user")
                raise
            except Exception as exc:
                # generic failure, make sure we record interrupted state so
                # resume logic can pick up where we left off
                persistence.update_session_status(session_id, "interrupted")
                self._log.error(f"scrape aborted: {exc}")
                raise
            finally:
                # always close the DB connection opened here so tests (and real
                # runs) don't leave the file locked after the command finishes.
                try:
                    persistence._conn.close()
                except Exception:
                    pass
