"""Windows toast + sound notifications for long scrapes."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from config import settings

try:
    from winotify import Notification  # type: ignore
except Exception:  # pragma: no cover
    Notification = None  # type: ignore

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None  # type: ignore


class Notifier:
    """
    Sends Windows toast notifications and plays a sound.
    Fails silently if not on Windows or if dependencies missing.
    """

    def __init__(self) -> None:
        self._enabled = True
        self._sound_enabled = True
        self._load_flags()

    def _config_path(self) -> Path:
        return settings.DATA_DIR / "notifications.json"

    def _load_flags(self) -> None:
        try:
            p = self._config_path()
            if not p.exists():
                return
            data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            self._enabled = bool(data.get("notifications", True))
            self._sound_enabled = bool(data.get("sound", True))
        except Exception:
            self._enabled = True
            self._sound_enabled = True

    def _can_notify(self) -> bool:
        return sys.platform == "win32" and self._enabled

    def _beep(self, kind: int) -> None:
        if not self._sound_enabled or winsound is None:
            return
        try:
            winsound.MessageBeep(kind)
        except Exception:
            pass

    def _toast(self, title: str, msg: str) -> None:
        if Notification is None:
            return
        try:
            toast = Notification(app_id="LoL Scraper", title=title, msg=msg)
            toast.show()
        except Exception:
            pass

    def notify_region_complete(self, region_name: str, matches: int, elapsed_str: str) -> None:
        if not self._can_notify():
            return
        try:
            title = "✓ Region Complete"
            body = f"{region_name} — {matches:,} matches in {elapsed_str}"
            self._toast(title, body)
            self._beep(getattr(winsound, "MB_OK", 0x00000000) if winsound else 0x00000000)
        except Exception:
            pass

    def notify_all_complete(self, total_matches: int, total_elapsed_str: str) -> None:
        if not self._can_notify():
            return
        try:
            title = "🏆 Scrape Complete"
            body = f"{total_matches:,} matches collected in {total_elapsed_str}"
            kind = getattr(winsound, "MB_ICONASTERISK", 0x00000040) if winsound else 0x00000040
            self._toast(title, body)
            self._beep(kind)
        except Exception:
            pass

    def notify_error(self, region_name: str, error: str) -> None:
        if not self._can_notify():
            return
        try:
            title = "⚠ Scrape Error"
            body = f"{region_name} failed: {error}"
            kind = getattr(winsound, "MB_ICONHAND", 0x00000010) if winsound else 0x00000010
            self._toast(title, body)
            self._beep(kind)
        except Exception:
            pass

