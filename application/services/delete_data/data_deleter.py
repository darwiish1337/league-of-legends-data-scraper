from __future__ import annotations

import sqlite3
from typing import Callable, List


class DataDeleterError(Exception):
    pass


class TableNotFoundError(DataDeleterError):
    pass


class DeletionNotConfirmedError(DataDeleterError):
    pass


class DataDeleter:
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

    def clear_table(self, table_name: str, *, confirm: bool) -> None:
        if not confirm:
            raise DeletionNotConfirmedError("Deletion not confirmed.")
        try:
            with self._connection_factory() as conn:
                cur = conn.cursor()
                # ensure existence
                tables = [r[0] for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()]
                if table_name not in tables:
                    raise TableNotFoundError(f"Table '{table_name}' not found.")
                cur.execute(f'DELETE FROM "{table_name}"')
                conn.commit()
        except sqlite3.Error as e:
            raise DataDeleterError(f"SQLite error while clearing table '{table_name}': {e}") from e

    def clear_all(self, *, confirm: bool) -> None:
        if not confirm:
            raise DeletionNotConfirmedError("Deletion not confirmed.")
        try:
            with self._connection_factory() as conn:
                cur = conn.cursor()
                tables = [r[0] for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()]
                for t in tables:
                    cur.execute(f'DELETE FROM "{t}"')
                conn.commit()
        except sqlite3.Error as e:
            raise DataDeleterError(f"SQLite error while clearing all tables: {e}") from e

