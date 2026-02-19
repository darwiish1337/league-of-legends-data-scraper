import sqlite3
import os
from pathlib import Path

def main():
    db_path = Path(__file__).resolve().parents[1] / 'data' / 'db' / 'scraper.sqlite'
    print('DB:', db_path)
    if not db_path.exists():
        print('DB file not found')
        return
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    for table in ['matches', 'participants', 'teams']:
        try:
            cnt = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            print(f'{table}:', cnt)
        except Exception as e:
            print(f'{table} error:', e)
    try:
        rows = cur.execute('SELECT match_id FROM matches LIMIT 5').fetchall()
        print('sample match_ids:', [r[0] for r in rows])
    except Exception as e:
        print('sample match_ids error:', e)
    try:
        rows = cur.execute('SELECT patch_version, COUNT(*) FROM matches GROUP BY patch_version ORDER BY COUNT(*) DESC LIMIT 10').fetchall()
        print('top patch_version counts:', rows)
    except Exception as e:
        print('patch_version counts error:', e)
    try:
        tp = os.environ.get('TARGET_PATCH', '26.01')
        rows = cur.execute('SELECT COUNT(*) FROM matches WHERE patch_version = ?', (tp,)).fetchone()
        print('target patch count:', tp, rows[0] if rows else 0)
        rows = cur.execute('SELECT match_id FROM matches WHERE patch_version = ? ORDER BY game_creation DESC LIMIT 5', (tp,)).fetchall()
        print('target patch sample ids:', [r[0] for r in rows])
    except Exception as e:
        print('target patch error:', e)
    conn.close()

if __name__ == '__main__':
    main()
