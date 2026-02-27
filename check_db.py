import sqlite3
from pathlib import Path


def main() -> None:
    db_path = Path("data/db/scraper.sqlite")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        print("Tables:", tables)
        for name in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {name}")
                count = cur.fetchone()[0]
                print(f"{name}: {count}")
            except Exception as exc:
                print(f"{name}: error: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

