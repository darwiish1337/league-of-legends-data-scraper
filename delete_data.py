from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

from services.data_deleter import DataDeleter, DataDeleterError, TableNotFoundError, DeletionNotConfirmedError
from config import settings


def _connection_factory() -> sqlite3.Connection:
    db_file = settings.DB_DIR / "scraper.sqlite"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_file))


def main() -> None:
    deleter = DataDeleter(_connection_factory)
    try:
        choice = input("Delete all tables or a specific table? (all/specific): ").strip().lower()
        if choice not in ("all", "specific"):
            print("Aborted: invalid choice.")
            return
        if choice == "all":
            confirm = input("Type 'yes' to confirm deletion of ALL tables: ").strip().lower() in ("y", "yes")
            if not confirm:
                print("Aborted.")
                return
            deleter.clear_all(confirm=True)
            print("Success: all tables cleared.")
            return
        tables = deleter.list_tables()
        if not tables:
            print("No tables found.")
            return
        print("Select a table to delete:")
        for idx, name in enumerate(tables, start=1):
            print(f"{idx}. {name}")
        try:
            sel = int(input("Enter number: ").strip())
        except ValueError:
            print("Aborted: invalid number.")
            return
        if sel < 1 or sel > len(tables):
            print("Aborted: number out of range.")
            return
        table = tables[sel - 1]
        confirm = input(f"Type 'yes' to confirm deletion of '{table}': ").strip().lower() in ("y", "yes")
        if not confirm:
            print("Aborted.")
            return
        deleter.clear_table(table, confirm=True)
        print(f"Success: table '{table}' cleared.")
    except TableNotFoundError as e:
        print(f"Error: {e}")
    except DeletionNotConfirmedError as e:
        print(f"Aborted: {e}")
    except DataDeleterError as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
