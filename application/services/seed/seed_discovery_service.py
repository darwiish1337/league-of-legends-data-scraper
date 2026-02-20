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
        try:
            for t in tiers:
                for d in divisions:
                    entries = await self.api_client.get_league_entries(region, queue_type, t, d, page=1)
                    if not entries:
                        continue
                    for e in entries:
                        sid = e.get("summonerId")
                        if sid:
                            summoner_ids.append(sid)
                            if len(summoner_ids) >= count:
                                break
                    if len(summoner_ids) >= count:
                        break
                if len(summoner_ids) >= count:
                    break
            tasks = [self.summoner_repo.get_summoner_by_id(region, sid) for sid in summoner_ids[:count]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            puuids: List[str] = []
            for r in results:
                if isinstance(r, Exception) or r is None:
                    continue
                puuids.append(r.puuid)
            # unique preserve order
            seen = set()
            ordered = []
            for p in puuids:
                if p not in seen:
                    seen.add(p)
                    ordered.append(p)
            return ordered[:count]
        except Exception:
            return []

