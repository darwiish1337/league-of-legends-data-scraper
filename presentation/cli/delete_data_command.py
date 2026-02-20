from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

from config import settings
from core.logging.logger import get_logger
from application.services.delete_data import DataDeleter, DataDeleterError, TableNotFoundError, DeletionNotConfirmedError


class DeleteDataCommand:
    """Interactive delete-data command backed by DataDeleter."""

    def __init__(self) -> None:
        self.log = get_logger(__name__, service="delete-cli")
        self.db_path = settings.DB_DIR / "scraper.sqlite"
        self.deleter = DataDeleter(self._conn_factory)

    def _conn_factory(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def run(self) -> None:
        while True:
            print("\n=== Delete Data ===")
            print(f"Database: {self.db_path}")
            print("1) List tables")
            print("2) Clear specific table")
            print("3) Clear ALL tables")
            print("4) Back")
            choice = input("Choose: ").strip()
            if choice == "1":
                self._list_tables()
            elif choice == "2":
                self._clear_one()
            elif choice == "3":
                self._clear_all()
            elif choice == "4":
                return
            else:
                print("Invalid option.")

    def _list_tables(self) -> None:
        try:
            tables = self.deleter.list_tables()
            if not tables:
                print("No tables found.")
                return
            print("\nTables:")
            for t in tables:
                print(f"- {t}")
        except DataDeleterError as e:
            self.log.error(lambda: f"list-tables-failed {e}")
            print(f"Error: {e}")

    def _clear_one(self) -> None:
        table = input("Table name to clear: ").strip()
        confirm = input(f"Type 'YES' to confirm delete of table '{table}': ").strip()
        if confirm != "YES":
            print("Not confirmed.")
            return
        try:
            self.deleter.clear_table(table, confirm=True)
            print(f"Cleared table {table}")
            self.log.success(lambda: f"clear-one-ok {table}")
        except (TableNotFoundError, DataDeleterError, DeletionNotConfirmedError) as e:
            self.log.error(lambda: f"clear-one-failed {e}")
            print(f"Error: {e}")

    def _clear_all(self) -> None:
        confirm = input("Type 'NUKE' to clear ALL tables: ").strip()
        if confirm != "NUKE":
            print("Not confirmed.")
            return
        try:
            self.deleter.clear_all(confirm=True)
            print("All tables cleared.")
            self.log.success(lambda: "clear-all-ok")
        except DataDeleterError as e:
            self.log.error(lambda: f"clear-all-failed {e}")
            print(f"Error: {e}")
