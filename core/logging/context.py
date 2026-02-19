from __future__ import annotations

import contextvars
from typing import Any, Dict

_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("log_context", default={})


def get_context() -> Dict[str, Any]:
    return dict(_context.get())


def bind(**values: Any) -> None:
    current = dict(_context.get())
    current.update({k: v for k, v in values.items() if v is not None})
    _context.set(current)


def unbind(*keys: str) -> None:
    current = dict(_context.get())
    for k in keys:
        current.pop(k, None)
    _context.set(current)


class context(object):
    def __init__(self, **values: Any) -> None:
        self._values = values
        self._token = None

    def __enter__(self):
        current = dict(_context.get())
        current.update({k: v for k, v in self._values.items() if v is not None})
        self._token = _context.set(current)
        return current

    def __exit__(self, exc_type, exc, tb):
        if self._token is not None:
            _context.reset(self._token)
        return False

