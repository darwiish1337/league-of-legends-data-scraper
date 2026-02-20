from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class _State:
    failures: int = 0
    opened_until: float = 0.0
    half_open: bool = False


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, reset_timeout_s: int = 10) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.reset_timeout_s = max(1, reset_timeout_s)
        self._states: Dict[str, _State] = {}

    def allow(self, key: str) -> bool:
        st = self._states.get(key)
        if not st:
            return True
        now = time.time()
        if st.opened_until > now:
            return False
        if st.opened_until > 0 and st.opened_until <= now:
            st.half_open = True
            return True
        return True

    def record_success(self, key: str) -> None:
        st = self._states.get(key)
        if not st:
            return
        st.failures = 0
        st.opened_until = 0.0
        st.half_open = False

    def record_failure(self, key: str) -> None:
        st = self._states.setdefault(key, _State())
        st.failures += 1
        if st.failures >= self.failure_threshold:
            dur = self.reset_timeout_s * (2 if st.half_open else 1)
            st.opened_until = time.time() + dur
            st.half_open = False
