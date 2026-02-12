import sqlite3
from pathlib import Path
import csv
from typing import List, Dict, Any
import httpx
from domain.entities import Match
from domain.enums import Role

class DataPersistenceService:
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
            "CREATE TABLE IF NOT EXISTS matches (match_id TEXT PRIMARY KEY, region TEXT, platform_id TEXT, queue_id INTEGER, queue_type TEXT, game_version TEXT, patch_version TEXT, game_creation INTEGER, game_start_timestamp INTEGER, game_end_timestamp INTEGER, game_duration INTEGER, match_date TEXT, match_date_simple TEXT, duration_mmss TEXT)"
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
            if "match_date" not in cols:
                cur.execute("ALTER TABLE matches ADD COLUMN match_date TEXT")
            if "match_date_simple" not in cols:
                cur.execute("ALTER TABLE matches ADD COLUMN match_date_simple TEXT")
            if "duration_mmss" not in cols:
                cur.execute("ALTER TABLE matches ADD COLUMN duration_mmss TEXT")
            pcols = {c[1] for c in cur.execute("PRAGMA table_info(participants)").fetchall()}
            add_cols = [
                ("summoner1_id", "INTEGER"),
                ("summoner2_id", "INTEGER"),
                ("summoner1_name", "TEXT"),
                ("summoner2_name", "TEXT"),
                ("item0", "INTEGER"),
                ("item1", "INTEGER"),
                ("item2", "INTEGER"),
                ("item3", "INTEGER"),
                ("item4", "INTEGER"),
                ("item5", "INTEGER"),
                ("item6", "INTEGER"),
            ]
            for name, typ in add_cols:
                if name not in pcols:
                    cur.execute(f"ALTER TABLE participants ADD COLUMN {name} {typ}")
            # Ensure champions/items tables have new columns if migrated
            ccols = {c[1] for c in cur.execute("PRAGMA table_info(champions)").fetchall()}
            if "champion_roles" not in ccols:
                try:
                    cur.execute("ALTER TABLE champions ADD COLUMN champion_roles TEXT")
                except:
                    pass
            icols = {c[1] for c in cur.execute("PRAGMA table_info(items)").fetchall()}
            if "item_name" not in icols:
                try:
                    cur.execute("ALTER TABLE items ADD COLUMN item_name TEXT")
                except:
                    pass
            self._conn.commit()
        except:
            pass

    def reset_db(self) -> None:
        cur = self._conn.cursor()
        for table in [
            "participant_items",
            "participant_summoner_spells",
            "participants",
            "teams",
            "matches",
            "champions",
            "items",
            "summoner_spells",
        ]:
            cur.execute(f"DELETE FROM {table}")
        self._conn.commit()

    def save_raw_matches(self, matches: List[Match]) -> None:
        cur = self._conn.cursor()
        match_rows = []
        team_rows = []
        participant_rows = []
        champion_rows = []
        item_rows = set()
        spell_rows = {}
        part_item_rows = []
        part_spell_rows = []
        spell_names = {
            1: "Cleanse",
            3: "Exhaust",
            4: "Flash",
            6: "Ghost",
            7: "Heal",
            11: "Smite",
            12: "Teleport",
            13: "Clarity",
            14: "Ignite",
            21: "Barrier"
        }
        for m in matches:
            simple_date = f"{m.game_date.day}/{m.game_date.month}/{m.game_date.year}"
            mm = int(m.game_duration // 60)
            ss = int(m.game_duration % 60)
            mmss = f"{mm:02d}:{ss:02d}"
            match_rows.append(
                (
                    m.match_id,
                    m.region.value,
                    m.platform_id,
                    m.queue_id,
                    m.queue_type.queue_name,
                    m.game_version,
                    m.patch_version,
                    m.game_creation,
                    m.game_start_timestamp,
                    m.game_end_timestamp,
                    m.game_duration,
                    m.game_date.isoformat(),
                    simple_date,
                    mmss,
                )
            )
            for team in (m.team_100, m.team_200):
                team_rows.append(
                    (
                        m.match_id,
                        team.team_id,
                        1 if team.win else 0,
                        team.dragon_kills,
                        team.baron_kills,
                        team.tower_kills,
                        team.inhibitor_kills,
                        team.champion_kills,
                        team.atakhan_kills,
                        team.horde_kills,
                        team.total_gold,
                        team.total_experience,
                    )
                )
            for p in m.participants:
                pos = p.individual_position.value if p.individual_position else None
                if pos == Role.UTILITY.value:
                    pos = "SUPPORT"
                rank_tier = p.rank_tier.value if p.rank_tier else "UNRANKED"
                rank_div = p.rank_division or ""
                participant_rows.append(
                    (
                        m.match_id,
                        p.participant_id,
                        p.puuid,
                        p.summoner_name,
                        p.summoner_id,
                        p.team_id,
                        p.champion_id,
                        p.champion_name,
                        pos,
                        rank_tier,
                        rank_div,
                        p.summoner1_id,
                        p.summoner2_id,
                        p.summoner1_name,
                        p.summoner2_name,
                        p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6,
                        1 if p.win else 0,
                        p.kills,
                        p.deaths,
                        p.assists,
                        p.gold_earned,
                        p.champion_experience,
                        p.total_damage_dealt_to_champions,
                    )
                )
                champion_rows.append((p.champion_id, p.champion_name))
                for idx, item_id in enumerate(p.items_list):
                    if item_id and item_id > 0:
                        item_rows.add(item_id)
                        part_item_rows.append((m.match_id, p.participant_id, idx, item_id))
                for slot, spell_id in enumerate([p.summoner1_id, p.summoner2_id], start=1):
                    if spell_id and spell_id > 0:
                        spell_rows[spell_id] = spell_names.get(spell_id, None)
                        part_spell_rows.append((m.match_id, p.participant_id, slot, spell_id))
        cur.executemany(
            "INSERT OR REPLACE INTO matches(match_id, region, platform_id, queue_id, queue_type, game_version, patch_version, game_creation, game_start_timestamp, game_end_timestamp, game_duration, match_date, match_date_simple, duration_mmss) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            match_rows,
        )
        cur.executemany(
            "INSERT OR REPLACE INTO teams(match_id, team_id, win, dragon_kills, baron_kills, tower_kills, inhibitor_kills, champion_kills, atakhan_kills, horde_kills, total_gold, total_experience) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            team_rows,
        )
        cur.executemany(
            "INSERT OR REPLACE INTO participants(match_id, participant_id, puuid, summoner_name, summoner_id, team_id, champion_id, champion_name, individual_position, rank_tier, rank_division, summoner1_id, summoner2_id, summoner1_name, summoner2_name, item0, item1, item2, item3, item4, item5, item6, win, kills, deaths, assists, gold_earned, champion_experience, total_damage_dealt_to_champions) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            participant_rows,
        )
        if champion_rows:
            cur.executemany(
                "INSERT OR IGNORE INTO champions(champion_id, champion_name) VALUES(?, ?)",
                champion_rows,
            )
        if item_rows:
            cur.executemany(
                "INSERT OR IGNORE INTO items(item_id) VALUES(?)",
                [(i,) for i in sorted(item_rows)],
            )
        if spell_rows:
            cur.executemany(
                "INSERT OR IGNORE INTO summoner_spells(spell_id, spell_name) VALUES(?, ?)",
                [(sid, sname) for sid, sname in spell_rows.items() if sname],
            )
        if part_item_rows:
            cur.executemany(
                "INSERT OR REPLACE INTO participant_items(match_id, participant_id, slot, item_id) VALUES(?, ?, ?, ?)",
                part_item_rows,
            )
        if part_spell_rows:
            cur.executemany(
                "INSERT OR REPLACE INTO participant_summoner_spells(match_id, participant_id, slot, spell_id) VALUES(?, ?, ?, ?)",
                part_spell_rows,
            )
        self._conn.commit()

    def seed_static_data(self) -> None:
        cur = self._conn.cursor()
        try:
            ver_resp = httpx.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=30)
            ver_resp.raise_for_status()
            versions = ver_resp.json()
            version = versions[0] if versions else "latest"
        except Exception:
            version = "latest"
        # Items
        try:
            items_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json"
            r = httpx.get(items_url, timeout=60)
            r.raise_for_status()
            data = r.json().get("data", {})
            rows = []
            for id_str, info in data.items():
                try:
                    iid = int(id_str)
                except:
                    continue
                name = info.get("name", "")
                rows.append((iid, name))
            if rows:
                cur.executemany("INSERT OR REPLACE INTO items(item_id, item_name) VALUES(?, ?)", rows)
        except Exception:
            pass
        # Summoner spells
        try:
            spells_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/summoner.json"
            r = httpx.get(spells_url, timeout=60)
            r.raise_for_status()
            data = r.json().get("data", {})
            rows = []
            for spell in data.values():
                try:
                    sid = int(spell.get("key"))
                except:
                    continue
                name = spell.get("name", "")
                rows.append((sid, name))
            if rows:
                cur.executemany("INSERT OR REPLACE INTO summoner_spells(spell_id, spell_name) VALUES(?, ?)", rows)
        except Exception:
            pass
        # Champions + roles
        try:
            champs_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
            r = httpx.get(champs_url, timeout=60)
            r.raise_for_status()
            data = r.json().get("data", {})
            rows = []
            for champ in data.values():
                try:
                    cid = int(champ.get("key"))
                except:
                    continue
                name = champ.get("name", "")
                tags = champ.get("tags", [])
                roles = set()
                if "Support" in tags:
                    roles.add("Support")
                if "Marksman" in tags:
                    roles.add("Bottom")
                if "Mage" in tags:
                    roles.add("Middle")
                if "Assassin" in tags:
                    roles.update(["Middle", "Jungle"])
                if "Fighter" in tags:
                    roles.update(["Top", "Middle"])
                if "Tank" in tags:
                    roles.update(["Top", "Support"])
                role_text = ",".join(sorted(roles)) if roles else ""
                rows.append((cid, name, role_text))
            if rows:
                cur.executemany("INSERT OR REPLACE INTO champions(champion_id, champion_name, champion_roles) VALUES(?, ?, ?)", rows)
        except Exception:
            pass
        self._conn.commit()

    def export_tables_csv(self, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: Dict[str, Path] = {}
        cur = self._conn.cursor()
        table_queries = {
            "matches": "SELECT * FROM matches",
            "teams": "SELECT * FROM teams",
            "participants": "SELECT * FROM participants",
            "champions": "SELECT * FROM champions",
            "items": "SELECT * FROM items",
            "summoner_spells": "SELECT * FROM summoner_spells",
            "participant_items": "SELECT * FROM participant_items",
            "participant_summoner_spells": "SELECT * FROM participant_summoner_spells",
        }
        for name, q in table_queries.items():
            p = output_dir / f"{name}.csv"
            rows = cur.execute(q).fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                if cols:
                    w.writerow(cols)
                for r in rows:
                    w.writerow(r)
            paths[name] = p
        return paths
