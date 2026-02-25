from __future__ import annotations

import asyncio
from typing import List

from domain.enums import Region, QueueType
from infrastructure.api import RiotAPIClient
from infrastructure.repositories import SummonerRepository


class SeedDiscoveryService:
    """
    Discovers seed PUUIDs for a region/queue using league entries with fallbacks.
    Fetches summoner IDs from tier/division pages, then resolves to PUUIDs.
    """

    def __init__(self, api_client: RiotAPIClient, summoner_repo: SummonerRepository) -> None:
        self.api_client = api_client
        self.summoner_repo = summoner_repo

    async def discover_seed_puuids(self, region: Region, queue_type: QueueType, count: int = 50) -> List[str]:
        tiers = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND"]
        divisions = ["I", "II", "III", "IV"]
        summoner_ids: List[str] = []
        summoner_names: List[str] = []
        try:
            try:
                top = []
                ch = await self.api_client.get_challenger_league(region, queue_type)
                gm = await self.api_client.get_grandmaster_league(region, queue_type)
                ms = await self.api_client.get_master_league(region, queue_type)
                for blob in [ch, gm, ms]:
                    if not blob:
                        continue
                    for e in blob.get("entries", [])[:count]:
                        sname = e.get("summonerName")
                        sid = e.get("summonerId")
                        if sname:
                            summoner_names.append(sname)
                        if sid:
                            summoner_ids.append(sid)
                        if len(summoner_names) >= count:
                            break
                    if len(summoner_names) >= count:
                        break
            except Exception:
                pass
            if len(summoner_names) < count:
                for t in tiers:
                    for d in divisions:
                        entries = await self.api_client.get_league_entries(region, queue_type, t, d, page=1)
                        if not entries:
                            continue
                        for e in entries:
                            sid = e.get("summonerId")
                            sname = e.get("summonerName")
                            if sid:
                                summoner_ids.append(sid)
                            if sname:
                                summoner_names.append(sname)
                            if len(summoner_ids) >= count:
                                break
                        if len(summoner_ids) >= count:
                            break
                    if len(summoner_ids) >= count:
                        break
            
            puuids: List[str] = []
            if summoner_names:
                name_tasks = [self.summoner_repo.get_summoner_by_name(region, n) for n in summoner_names[:count]]
                name_results = await asyncio.gather(*name_tasks, return_exceptions=True)
                for r in name_results:
                    if isinstance(r, Exception) or r is None:
                        continue
                    puuids.append(r.puuid)
            if not puuids and summoner_ids:
                id_tasks = [self.summoner_repo.get_summoner_by_id(region, sid) for sid in summoner_ids[:count]]
                id_results = await asyncio.gather(*id_tasks, return_exceptions=True)
                for r in id_results:
                    if isinstance(r, Exception) or r is None:
                        continue
                    puuids.append(r.puuid)
            
            seen = set()
            ordered = []
            for p in puuids:
                if p not in seen:
                    seen.add(p)
                    ordered.append(p)
            return ordered[:count]
        except Exception:
            return []
