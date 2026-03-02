import sqlite3
from pathlib import Path
import csv
from typing import List, Dict, Any
import httpx
from domain.entities import Match
from domain.enums import Role
from domain.enums.region import Region


class DataPersistenceService:
    """Lightweight persistence layer for SQLite + CSV exports."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS matches (match_id TEXT PRIMARY KEY, region TEXT, platform_id TEXT, region_group TEXT, queue_id INTEGER, queue_type TEXT, game_version TEXT, patch_version TEXT, game_creation INTEGER, game_start_timestamp INTEGER, game_end_timestamp INTEGER, game_duration INTEGER, match_date TEXT, match_date_simple TEXT, duration_mmss TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS platforms (platform_id TEXT PRIMARY KEY, friendly_name TEXT, region_group TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS teams (match_id TEXT, team_id INTEGER, win INTEGER, dragon_kills INTEGER, baron_kills INTEGER, tower_kills INTEGER, inhibitor_kills INTEGER, champion_kills INTEGER, atakhan_kills INTEGER, horde_kills INTEGER, total_gold INTEGER, total_experience INTEGER, PRIMARY KEY(match_id, team_id), FOREIGN KEY(match_id) REFERENCES matches(match_id))"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS participants (match_id TEXT, participant_id INTEGER, puuid TEXT, summoner_name TEXT, summoner_id TEXT, team_id INTEGER, champion_id INTEGER, champion_name TEXT, individual_position TEXT, rank_tier TEXT, rank_division TEXT, summoner1_id INTEGER, summoner2_id INTEGER, summoner1_name TEXT, summoner2_name TEXT, item0 INTEGER, item1 INTEGER, item2 INTEGER, item3 INTEGER, item4 INTEGER, item5 INTEGER, item6 INTEGER, win INTEGER, kills INTEGER, deaths INTEGER, assists INTEGER, gold_earned INTEGER, champion_experience INTEGER, total_damage_dealt_to_champions INTEGER, PRIMARY KEY(match_id, participant_id), FOREIGN KEY(match_id) REFERENCES matches(match_id))"
        )
        cur.execute("CREATE TABLE IF NOT EXISTS champions (champion_id INTEGER PRIMARY KEY, champion_name TEXT, champion_roles TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY, item_name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS summoner_spells (spell_id INTEGER PRIMARY KEY, spell_name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS participant_items (match_id TEXT, participant_id INTEGER, slot INTEGER, item_id INTEGER, PRIMARY KEY(match_id, participant_id, slot), FOREIGN KEY(match_id, participant_id) REFERENCES participants(match_id, participant_id), FOREIGN KEY(item_id) REFERENCES items(item_id))")
        cur.execute("CREATE TABLE IF NOT EXISTS participant_summoner_spells (match_id TEXT, participant_id INTEGER, slot INTEGER, spell_id INTEGER, PRIMARY KEY(match_id, participant_id, slot), FOREIGN KEY(match_id, participant_id) REFERENCES participants(match_id, participant_id), FOREIGN KEY(spell_id) REFERENCES summoner_spells(spell_id))")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_participants_puuid ON participants(puuid)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_participants_match ON participants(match_id)")
        self._conn.commit()
        try:
            cols = {c[1] for c in cur.execute("PRAGMA table_info(matches)").fetchall()}
            for col in ["match_date", "match_date_simple", "duration_mmss", "region_group"]:
                if col not in cols:
                    cur.execute(f"ALTER TABLE matches ADD COLUMN {col} TEXT")
            pcols = {c[1] for c in cur.execute("PRAGMA table_info(participants)").fetchall()}
            for name, typ in [
                ("summoner1_id", "INTEGER"), ("summoner2_id", "INTEGER"),
                ("summoner1_name", "TEXT"),  ("summoner2_name", "TEXT"),
                ("item0", "INTEGER"), ("item1", "INTEGER"), ("item2", "INTEGER"),
                ("item3", "INTEGER"), ("item4", "INTEGER"), ("item5", "INTEGER"),
                ("item6", "INTEGER"),
            ]:
                if name not in pcols:
                    cur.execute(f"ALTER TABLE participants ADD COLUMN {name} {typ}")
            ccols = {c[1] for c in cur.execute("PRAGMA table_info(champions)").fetchall()}
            if "champion_roles" not in ccols:
                cur.execute("ALTER TABLE champions ADD COLUMN champion_roles TEXT")
            icols = {c[1] for c in cur.execute("PRAGMA table_info(items)").fetchall()}
            if "item_name" not in icols:
                cur.execute("ALTER TABLE items ADD COLUMN item_name TEXT")
            self._conn.commit()
        except Exception:
            pass
        self._seed_platforms()
        self._ensure_matches_column_order()

    def _seed_platforms(self) -> None:
        cur = self._conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS platforms (platform_id TEXT PRIMARY KEY, friendly_name TEXT, region_group TEXT)")
        existing = {r[0] for r in cur.execute("SELECT platform_id FROM platforms").fetchall()}
        rows = []
        for r in Region.all_regions():
            if r.platform_route not in existing:
                rows.append((r.platform_route, r.friendly, r.regional_route))
        if rows:
            cur.executemany("INSERT OR IGNORE INTO platforms(platform_id, friendly_name, region_group) VALUES(?, ?, ?)", rows)
            self._conn.commit()

    def _ensure_matches_column_order(self) -> None:
        try:
            cur = self._conn.cursor()
            cols = [c[1] for c in cur.execute("PRAGMA table_info(matches)").fetchall()]
            desired = ["match_id", "region", "platform_id", "region_group", "queue_id",
                       "queue_type", "game_version", "patch_version", "game_creation",
                       "game_start_timestamp", "game_end_timestamp", "game_duration",
                       "match_date", "match_date_simple", "duration_mmss"]
            if cols == desired:
                return
            cur.execute("ALTER TABLE matches RENAME TO matches_old")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS matches (match_id TEXT PRIMARY KEY, region TEXT, platform_id TEXT, region_group TEXT, queue_id INTEGER, queue_type TEXT, game_version TEXT, patch_version TEXT, game_creation INTEGER, game_start_timestamp INTEGER, game_end_timestamp INTEGER, game_duration INTEGER, match_date TEXT, match_date_simple TEXT, duration_mmss TEXT)"
            )
            old_set = set(cols)
            exprs   = [c if c in old_set else "NULL" for c in desired]
            cur.execute(f"INSERT INTO matches ({', '.join(desired)}) SELECT {', '.join(exprs)} FROM matches_old")
            cur.execute("DROP TABLE matches_old")
            self._conn.commit()
        except Exception:
            pass

    def save_raw_matches(self, matches: List[Match]) -> None:
        cur = self._conn.cursor()
        match_rows, team_rows, participant_rows = [], [], []
        champion_rows, part_item_rows, part_spell_rows = [], [], []
        item_rows: set = set()
        spell_rows: dict = {}
        spell_names = {1:"Cleanse",3:"Exhaust",4:"Flash",6:"Ghost",7:"Heal",
                       11:"Smite",12:"Teleport",13:"Clarity",14:"Ignite",21:"Barrier"}

        for m in matches:
            simple_date = f"{m.game_date.day}/{m.game_date.month}/{m.game_date.year}"
            mm, ss = int(m.game_duration // 60), int(m.game_duration % 60)
            match_rows.append((
                m.match_id, m.region.value, m.platform_id,
                m.region.regional_route if hasattr(m.region, "regional_route") else None,
                m.queue_id, m.queue_type.queue_name, m.game_version, m.patch_version,
                m.game_creation, m.game_start_timestamp, m.game_end_timestamp,
                m.game_duration, m.game_date.isoformat(), simple_date, f"{mm:02d}:{ss:02d}",
            ))
            for team in (m.team_100, m.team_200):
                team_rows.append((
                    m.match_id, team.team_id, 1 if team.win else 0,
                    team.dragon_kills, team.baron_kills, team.tower_kills,
                    team.inhibitor_kills, team.champion_kills, team.atakhan_kills,
                    team.horde_kills, team.total_gold, team.total_experience,
                ))
            for p in m.participants:
                pos       = p.individual_position.value if p.individual_position else None
                rank_tier = p.rank_tier.value if p.rank_tier else "UNRANKED"
                participant_rows.append((
                    m.match_id, p.participant_id, p.puuid, p.summoner_name, p.summoner_id,
                    p.team_id, p.champion_id, p.champion_name, pos,
                    rank_tier, p.rank_division or "",
                    p.summoner1_id, p.summoner2_id, p.summoner1_name, p.summoner2_name,
                    p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6,
                    1 if p.win else 0, p.kills, p.deaths, p.assists,
                    p.gold_earned, p.champion_experience, p.total_damage_dealt_to_champions,
                ))
                champion_rows.append((p.champion_id, p.champion_name))
                for idx, item_id in enumerate(p.items_list):
                    if item_id and item_id > 0:
                        item_rows.add(item_id)
                        part_item_rows.append((m.match_id, p.participant_id, idx, item_id))
                for slot, spell_id in enumerate([p.summoner1_id, p.summoner2_id], start=1):
                    if spell_id and spell_id > 0:
                        spell_rows[spell_id] = spell_names.get(spell_id)
                        part_spell_rows.append((m.match_id, p.participant_id, slot, spell_id))

        cur.executemany(
            """INSERT INTO matches(match_id,region,platform_id,region_group,queue_id,queue_type,
               game_version,patch_version,game_creation,game_start_timestamp,game_end_timestamp,
               game_duration,match_date,match_date_simple,duration_mmss)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(match_id) DO UPDATE SET
               region=excluded.region,platform_id=excluded.platform_id,
               region_group=excluded.region_group,queue_id=excluded.queue_id,
               queue_type=excluded.queue_type,game_version=excluded.game_version,
               patch_version=excluded.patch_version,game_creation=excluded.game_creation,
               game_start_timestamp=excluded.game_start_timestamp,
               game_end_timestamp=excluded.game_end_timestamp,
               game_duration=excluded.game_duration,match_date=excluded.match_date,
               match_date_simple=excluded.match_date_simple,duration_mmss=excluded.duration_mmss""",
            match_rows,
        )
        self._conn.commit()

        inserted_ids = {r[0] for r in match_rows}
        existing_ids: set = set()
        if inserted_ids:
            ph   = ",".join(["?"] * len(inserted_ids))
            rows = cur.execute(f"SELECT match_id FROM matches WHERE match_id IN ({ph})", list(inserted_ids)).fetchall()
            existing_ids = {r[0] for r in rows}

        if existing_ids:
            team_rows        = [r for r in team_rows        if r[0] in existing_ids]
            participant_rows = [r for r in participant_rows if r[0] in existing_ids]
            part_item_rows   = [r for r in part_item_rows   if r[0] in existing_ids]
            part_spell_rows  = [r for r in part_spell_rows  if r[0] in existing_ids]

        part_keys = {(r[0], r[1]) for r in participant_rows}
        part_item_rows  = [r for r in part_item_rows  if (r[0], r[1]) in part_keys]
        part_spell_rows = [r for r in part_spell_rows if (r[0], r[1]) in part_keys]

        def _safe_many(sql, rows):
            try:
                cur.executemany(sql, rows)
            except sqlite3.IntegrityError:
                for r in rows:
                    try:
                        cur.execute(sql, r)
                    except sqlite3.IntegrityError:
                        continue

        _safe_many(
            """INSERT INTO teams(match_id,team_id,win,dragon_kills,baron_kills,tower_kills,
               inhibitor_kills,champion_kills,atakhan_kills,horde_kills,total_gold,total_experience)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(match_id,team_id) DO UPDATE SET win=excluded.win,
               dragon_kills=excluded.dragon_kills,baron_kills=excluded.baron_kills,
               tower_kills=excluded.tower_kills,inhibitor_kills=excluded.inhibitor_kills,
               champion_kills=excluded.champion_kills,atakhan_kills=excluded.atakhan_kills,
               horde_kills=excluded.horde_kills,total_gold=excluded.total_gold,
               total_experience=excluded.total_experience""",
            team_rows,
        )
        _safe_many(
            """INSERT INTO participants(match_id,participant_id,puuid,summoner_name,summoner_id,
               team_id,champion_id,champion_name,individual_position,rank_tier,rank_division,
               summoner1_id,summoner2_id,summoner1_name,summoner2_name,
               item0,item1,item2,item3,item4,item5,item6,
               win,kills,deaths,assists,gold_earned,champion_experience,
               total_damage_dealt_to_champions)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(match_id,participant_id) DO UPDATE SET
               puuid=excluded.puuid,summoner_name=excluded.summoner_name,
               summoner_id=excluded.summoner_id,team_id=excluded.team_id,
               champion_id=excluded.champion_id,champion_name=excluded.champion_name,
               individual_position=excluded.individual_position,
               rank_tier=excluded.rank_tier,rank_division=excluded.rank_division,
               summoner1_id=excluded.summoner1_id,summoner2_id=excluded.summoner2_id,
               summoner1_name=excluded.summoner1_name,summoner2_name=excluded.summoner2_name,
               item0=excluded.item0,item1=excluded.item1,item2=excluded.item2,
               item3=excluded.item3,item4=excluded.item4,item5=excluded.item5,item6=excluded.item6,
               win=excluded.win,kills=excluded.kills,deaths=excluded.deaths,
               assists=excluded.assists,gold_earned=excluded.gold_earned,
               champion_experience=excluded.champion_experience,
               total_damage_dealt_to_champions=excluded.total_damage_dealt_to_champions""",
            participant_rows,
        )

        if champion_rows:
            cur.executemany("INSERT OR IGNORE INTO champions(champion_id,champion_name) VALUES(?,?)", champion_rows)
        if item_rows:
            cur.executemany("INSERT OR IGNORE INTO items(item_id) VALUES(?)", [(i,) for i in sorted(item_rows)])
        if spell_rows:
            cur.executemany("INSERT OR IGNORE INTO summoner_spells(spell_id,spell_name) VALUES(?,?)",
                            [(sid, sn) for sid, sn in spell_rows.items() if sn])

        if existing_ids:
            ph   = ",".join(["?"] * len(existing_ids))
            rows = cur.execute(
                f"SELECT match_id,participant_id FROM participants WHERE match_id IN ({ph})",
                list(existing_ids),
            ).fetchall()
            db_keys         = {(r[0], r[1]) for r in rows}
            part_item_rows  = [r for r in part_item_rows  if (r[0], r[1]) in db_keys]
            part_spell_rows = [r for r in part_spell_rows if (r[0], r[1]) in db_keys]

        _safe_many(
            """INSERT INTO participant_items(match_id,participant_id,slot,item_id)
               VALUES(?,?,?,?)
               ON CONFLICT(match_id,participant_id,slot) DO UPDATE SET item_id=excluded.item_id""",
            part_item_rows,
        )
        _safe_many(
            """INSERT INTO participant_summoner_spells(match_id,participant_id,slot,spell_id)
               VALUES(?,?,?,?)
               ON CONFLICT(match_id,participant_id,slot) DO UPDATE SET spell_id=excluded.spell_id""",
            part_spell_rows,
        )
        self._conn.commit()

    def seed_static_data(self) -> None:
        cur = self._conn.cursor()
        try:
            versions = httpx.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=30).json()
            version  = versions[0] if versions else "latest"
        except Exception:
            version = "latest"

        for url, table, key_fn, row_fn in [
            (
                f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json",
                "items",
                lambda d: [(int(k), v.get("name","")) for k,v in d.items() if k.isdigit()],
                "INSERT OR REPLACE INTO items(item_id,item_name) VALUES(?,?)",
            ),
            (
                f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/summoner.json",
                "summoner_spells",
                lambda d: [(int(v.get("key")), v.get("name","")) for v in d.values() if str(v.get("key","")).isdigit()],
                "INSERT OR REPLACE INTO summoner_spells(spell_id,spell_name) VALUES(?,?)",
            ),
        ]:
            try:
                data = httpx.get(url, timeout=60).json().get("data", {})
                cur.executemany(row_fn, key_fn(data))
            except Exception:
                pass

        try:
            data = httpx.get(
                f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json",
                timeout=60,
            ).json().get("data", {})
            rows = []
            for champ in data.values():
                try:
                    cid = int(champ.get("key"))
                except Exception:
                    continue
                tags  = champ.get("tags", [])
                roles = set()
                if "Support"  in tags: roles.add("Support")
                if "Marksman" in tags: roles.add("Bottom")
                if "Mage"     in tags: roles.add("Middle")
                if "Assassin" in tags: roles.update(["Middle", "Jungle"])
                if "Fighter"  in tags: roles.update(["Top", "Middle"])
                if "Tank"     in tags: roles.update(["Top", "Support"])
                rows.append((cid, champ.get("name",""), ",".join(sorted(roles))))
            cur.executemany("INSERT OR REPLACE INTO champions(champion_id,champion_name,champion_roles) VALUES(?,?,?)", rows)
        except Exception:
            pass
        self._conn.commit()

    def export_tables_csv(self, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: Dict[str, Path] = {}
        cur = self._conn.cursor()
        for name, q in {
            "matches":                    "SELECT * FROM matches",
            "teams":                      "SELECT * FROM teams",
            "participants":               "SELECT * FROM participants",
            "champions":                  "SELECT * FROM champions",
            "items":                      "SELECT * FROM items",
            "summoner_spells":            "SELECT * FROM summoner_spells",
            "participant_items":          "SELECT * FROM participant_items",
            "participant_summoner_spells":"SELECT * FROM participant_summoner_spells",
            "platforms":                  "SELECT * FROM platforms",
        }.items():
            p    = output_dir / f"{name}.csv"
            rows = cur.execute(q).fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if cols:
                    w.writerow(cols)
                w.writerows(rows)
            paths[name] = p
        return paths

    # ── Query helpers ──────────────────────────────────────────────────────

    def get_existing_match_ids(self) -> list[str]:
        try:
            rows = self._conn.execute("SELECT match_id FROM matches").fetchall()
            return [r[0] for r in rows] if rows else []
        except Exception:
            return []

    def get_existing_puuids(self) -> list[str]:
        try:
            rows = self._conn.execute("SELECT DISTINCT puuid FROM participants").fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception:
            return []

    def get_existing_puuids_for_region(self, region_value: str) -> list[str]:
        """
        Return PUUIDs that were scraped specifically from this region.
        Used to seed the next run of the same region without polluting
        other regions with irrelevant PUUIDs.
        """
        try:
            rows = self._conn.execute(
                """
                SELECT DISTINCT p.puuid
                FROM participants p
                JOIN matches m ON p.match_id = m.match_id
                WHERE m.region = ?
                """,
                (region_value,),
            ).fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception:
            return []

    def get_existing_match_ids_for_region(self, region_value: str) -> list[str]:
        """Return match IDs already stored for this region."""
        try:
            rows = self._conn.execute(
                "SELECT match_id FROM matches WHERE region = ?",
                (region_value,),
            ).fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception:
            return []