from __future__ import annotations

import sqlite3
from typing import List, Tuple
from pathlib import Path

from config import settings
from core.logging.logger import get_logger
from application.services.data_persistence_service import DataPersistenceService


class DBCheckCommand:
    """Database health/inspection command."""

    def __init__(self) -> None:
        self.log = get_logger(__name__, service="db-cli")
        self.db_path = settings.DB_DIR / "scraper.sqlite"
        # Ensure schema and platform mappings are present
        try:
            DataPersistenceService(self.db_path)
        except Exception:
            pass

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def run(self) -> None:
        while True:
            print("\n=== DB Check ===", flush=True)
            print(f"Database: {self.db_path}", flush=True)
            print("1) List tables", flush=True)
            print("2) Count rows per table", flush=True)
            print("3) PRAGMA integrity_check", flush=True)
            print("4) Back", flush=True)
            choice = input("Choose: ").strip()
            if choice == "1":
                self._list_tables()
                input("Press Enter to return to DB menu...")
            elif choice == "2":
                self._count_rows()
                input("Press Enter to return to DB menu...")
            elif choice == "3":
                self._integrity()
                input("Press Enter to return to DB menu...")
            elif choice == "4":
                return
            else:
                print("Invalid option.", flush=True)

    def _list_tables(self) -> None:
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                rows = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            if not rows:
                print("No tables found.", flush=True)
                return
            print("\nTables:", flush=True)
            for (name,) in rows:
                print(f"- {name}", flush=True)
        except sqlite3.Error as e:
            self.log.error(lambda: f"db-list-failed {e}")
            print(f"Error: {e}", flush=True)

    def _count_rows(self) -> None:
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                tables = [r[0] for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()]
                if not tables:
                    print("No tables found.", flush=True)
                    return
                print("\nRow counts:", flush=True)
                for t in tables:
                    try:
                        cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                        print(f"- {t}: {cnt}", flush=True)
                    except sqlite3.Error:
                        print(f"- {t}: error", flush=True)
        except sqlite3.Error as e:
            self.log.error(lambda: f"db-count-failed {e}")
            print(f"Error: {e}", flush=True)

    def _integrity(self) -> None:
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                row = cur.execute("PRAGMA integrity_check").fetchone()
                result = row[0] if row else "unknown"
                print(f"integrity_check: {result}", flush=True)
        except sqlite3.Error as e:
            self.log.error(lambda: f"db-integrity-failed {e}")
            print(f"Error: {e}", flush=True)

    # Region groups summary removed as requested
