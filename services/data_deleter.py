from __future__ import annotations

import re
import sqlite3
from typing import Callable, List


class DataDeleterError(Exception):
    """Base error for DataDeleter operations."""


class TableNotFoundError(DataDeleterError):
    """Raised when a target table does not exist."""


class DeletionNotConfirmedError(DataDeleterError):
    """Raised when deletion is attempted without explicit confirmation."""


class DataDeleter:
    """
    Programmatic, dependency-injected deletion utility for SQLite databases.
    
    This class:
    - Lists user tables (excluding SQLite internals)
    - Clears a specific table or all tables
    - Requires explicit confirmation flag
    - Is transaction-safe and validates inputs
    """

    _TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def list_tables(self) -> List[str]:
        try:
            with self._connection_factory() as conn:
                cur = conn.cursor()
                rows = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
                return [r[0] for r in rows]
        except sqlite3.Error as e:
            raise DataDeleterError(f"SQLite error while listing tables: {e}") from e

    def clear_table(self, table_name: str, *, confirm: bool = True) -> None:
        if not confirm:
            raise DeletionNotConfirmedError("Deletion requires confirm=True")
        self._validate_table_name(table_name)
        try:
            with self._connection_factory() as conn:
                cur = conn.cursor()
                if not self._table_exists(cur, table_name):
                    raise TableNotFoundError(f"Table '{table_name}' does not exist")
                cur.execute("PRAGMA foreign_keys=OFF")
                cur.execute(f'DELETE FROM "{table_name}"')
                cur.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error as e:
            raise DataDeleterError(f"SQLite error while clearing table '{table_name}': {e}") from e

    def clear_all(self, *, confirm: bool = True) -> None:
        if not confirm:
            raise DeletionNotConfirmedError("Deletion requires confirm=True")
        try:
            with self._connection_factory() as conn:
                cur = conn.cursor()
                tables = self.list_tables()
                cur.execute("PRAGMA foreign_keys=OFF")
                for t in tables:
                    cur.execute(f'DELETE FROM "{t}"')
                cur.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error as e:
            raise DataDeleterError(f"SQLite error while clearing all tables: {e}") from e

    @classmethod
    def _validate_table_name(cls, name: str) -> None:
        if not cls._TABLE_NAME_RE.match(name):
            raise ValueError("Invalid table name; must be alphanumeric/underscore and not start with a digit")

    @staticmethod
    def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
        row = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        return bool(row)

