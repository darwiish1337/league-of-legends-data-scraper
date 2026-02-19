from __future__ import annotations

import logging
from enum import IntEnum


class LogLevel(IntEnum):
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


def register_levels() -> None:
    if logging.getLevelName(LogLevel.TRACE) == "Level 5":
        logging.addLevelName(LogLevel.TRACE, "TRACE")
    if logging.getLevelName(LogLevel.SUCCESS) == "Level 25":
        logging.addLevelName(LogLevel.SUCCESS, "SUCCESS")


def to_level(value: int | str) -> int:
    if isinstance(value, int):
        return value
    name = value.upper()
    if name == "TRACE":
        return int(LogLevel.TRACE)
    if name == "SUCCESS":
        return int(LogLevel.SUCCESS)
    return logging.getLevelName(name) if isinstance(logging.getLevelName(name), int) else logging.INFO

