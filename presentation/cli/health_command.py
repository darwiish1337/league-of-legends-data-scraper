from __future__ import annotations

import os
import shutil
from typing import Iterable, List, Optional

from core.logging.logger import get_logger, StructuredLogger
from domain.enums import Region
from infrastructure.health import DNSChecker, ApiChecker, PlatformChecker

_BRIGHT_GREEN = "\033[1;92m"
_CYAN = "\033[96m"
_YELLOW = "\033[93m"
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"


def _g(s: str) -> str:
    return f"{_BRIGHT_GREEN}{s}{_RESET}"


def _c(s: str) -> str:
    return f"{_CYAN}{s}{_RESET}"


def _y(s: str) -> str:
    return f"{_YELLOW}{s}{_RESET}"


class HealthCommand:
    """Interactive health command for DNS and API checks."""

    def __init__(self) -> None:
        self.logger: StructuredLogger = get_logger(__name__, service="health")
        api_key = os.getenv("RIOT_API_KEY", "")
        headers = {"X-Riot-Token": api_key} if api_key else {}
        self._has_key = bool(api_key)
        self._api = ApiChecker(timeout=5.0, headers=headers)
        self._dns = DNSChecker()

    async def run_interactive(self) -> int:
        while True:
            cols = shutil.get_terminal_size(fallback=(96, 20)).columns
            div = "─" * min(cols, 60)
            print(f"\n{_g(div)}")
            print(f"  {_BOLD}HEALTH CHECK{_RESET}")
            print(_g(div))
            print(f"  {_c('1')}  Check API key / status")
            print(f"  {_c('2')}  Check Riot DNS")
            print(f"  {_c('3')}  Check specific platforms")
            print(f"  {_c('0')}  Back")
            print(_g(div))
            choice = input("  Choose: ").strip()
            if choice == "1":
                await self._check_api_ui()
            elif choice == "2":
                self._check_platform_ui()
            elif choice == "3":
                self._check_dns_ui()
            elif choice == "0":
                return 0
            else:
                print(f"  {_y('Invalid option.')}")

    def _choose_platforms_ui(self) -> List[str]:
        rows = PlatformChecker.all_platform_rows()
        print()
        print(f"  {_BOLD}PLATFORMS{_RESET}")
        for idx, (plat, friendly, regroute) in enumerate(rows, start=1):
            print(f"  {idx:2d}) {_c(plat):4s} {friendly:<10} [{_DIM}{regroute}{_RESET}]")
        print()
        print("  Enter numbers separated by commas (1,3,10),")
        print("  Type 'all' for all platforms,")
        print("  For Cancel Press 0.")
        sel = input("  Select: ").strip().lower()
        if sel == "0":
            return []
        if not sel or sel == "all":
            return [plat for plat, _, _ in rows]
        chosen: List[str] = []
        parts = [p.strip() for p in sel.split(",") if p.strip()]
        for p in parts:
            try:
                i = int(p)
                if 1 <= i <= len(rows):
                    plat = rows[i - 1][0]
                    if plat not in chosen:
                        chosen.append(plat)
            except Exception:
                continue
        return chosen

    async def _check_api_ui(self) -> None:
        if not self._has_key:
            print(f"  {_y('RIOT_API_KEY is not set in config/.env')}")
            print(f"  {_y('Set a valid key and retry API status check.')}")
            return
        # Use a small fixed set of canonical platforms to test the key.
        hosts = ["euw1", "eun1", "na1"]
        path = "/lol/status/v4/platform-data"
        print(f"\n  {_BOLD}API STATUS ({path}){_RESET}")
        summary: List[tuple[str, bool, str, int]] = []
        for h in hosts:
            ok, msg, ms = await self._api.check(h, path)
            summary.append((h, ok, msg, ms))
            if ok:
                print(f"  - {_c(h)}: {_g('OK')} ({ms}ms)")
            else:
                print(f"  - {_c(h)}: {_y('ERROR')} ({msg})")
        if summary:
            all_401 = all((not ok and msg.startswith("status=401")) for _, ok, msg, _ in summary)
            any_ok = any(ok for _, ok, _, _ in summary)
            print()
            if any_ok:
                print(f"  {_g('API key appears valid (at least one region returned 200).')}")
            elif all_401:
                print(f"  {_y('All regions returned 401 – API key is invalid or expired.')}")
            else:
                print(f"  {_y('API key check inconclusive – see errors above.')}")

    def _check_platform_ui(self) -> None:
        rows = PlatformChecker.all_platform_rows()
        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div = "─" * min(cols, 60)
        print(f"\n{_g(div)}")
        print(f"  {_BOLD}RIOT DNS HOSTS{_RESET}")
        print(_g(div))
        hosts = [
            "api.riotgames.com",
            "europe.api.riotgames.com",
            "americas.api.riotgames.com",
            "asia.api.riotgames.com",
        ]
        for plat, _, _ in rows:
            hosts.append(f"{plat}.api.riotgames.com")
        seen: set[str] = set()
        ordered = []
        for h in hosts:
            if h not in seen:
                seen.add(h)
                ordered.append(h)
        for h in ordered:
            ok = self._dns.resolves(h)
            if ok:
                print(f"  - {_c(h)}: {_g('resolves')}")
            else:
                print(f"  - {_c(h)}: {_y('no DNS record')}")
        print(_g(div))

    def _check_dns_ui(self) -> None:
        hosts = self._choose_platforms_ui()
        if not hosts:
            print(f"  {_y('No platforms selected.')}")
            return
        print(f"\n  {_BOLD}DNS CHECK (platform.api.riotgames.com){_RESET}")
        for h in hosts:
            host = f"{h}.api.riotgames.com"
            ok = self._dns.resolves(host)
            if ok:
                print(f"  - {_c(host)}: {_g('resolves')}")
            else:
                print(f"  - {_c(host)}: {_y('no DNS record')}")


async def run(argv: Optional[Iterable[str]] = None) -> int:
    cmd = HealthCommand()
    await cmd.run_interactive()
    return 0
