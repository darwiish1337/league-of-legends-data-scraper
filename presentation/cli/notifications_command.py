"""Notification settings CLI."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, Any

from config import settings
from infrastructure.notifications import Notifier

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


class NotificationsCommand:
    """CLI for toggling desktop notifications."""

    def __init__(self) -> None:
        self._path: Path = settings.DATA_DIR / "notifications.json"
        self._enabled: bool = True
        self._sound: bool = True
        self._load()

    def _load(self) -> None:
        try:
            if not self._path.exists():
                return
            data: Dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))
            self._enabled = bool(data.get("notifications", True))
            self._sound = bool(data.get("sound", True))
        except Exception:
            self._enabled = True
            self._sound = True

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"notifications": self._enabled, "sound": self._sound}
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _print_header(self) -> None:
        cols = shutil.get_terminal_size(fallback=(96, 20)).columns
        div = "─" * min(cols, 60)
        print(f"\n{_g(div)}")
        print(f"  {_BOLD}NOTIFICATION SETTINGS{_RESET}")
        print(_g(div))
        print(f"  Notifications are currently: {_c('ON' if self._enabled else 'OFF')}")
        print(f"  Sound is currently        : {_c('ON' if self._sound else 'OFF')}")
        print(_g(div))

    def run(self) -> None:
        while True:
            self._print_header()
            print(f"  {_c('1')}  Toggle notifications")
            print(f"  {_c('2')}  Toggle sound")
            print(f"  {_c('3')}  Test notification")
            print(f"  {_c('4')}  Back")
            choice = input("  Choose: ").strip()
            if choice == "1":
                self._enabled = not self._enabled
                self._save()
            elif choice == "2":
                self._sound = not self._sound
                self._save()
            elif choice == "3":
                self._save()
                notifier = Notifier()
                notifier.notify_all_complete(12345, "00h 10m")
            elif choice == "4":
                return
            else:
                print(f"  {_y('Invalid option.')}")

