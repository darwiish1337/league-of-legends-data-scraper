"""Seed discovery - fast path first, deep search as fallback."""
from __future__ import annotations

import asyncio
from typing import List

from domain.enums import Region, QueueType
from infrastructure.api import RiotAPIClient
from infrastructure.repositories import SummonerRepository


class SeedDiscoveryService:
    """
    Discovers seed PUUIDs for a region/queue.

    Fast path  : Challenger → Grandmaster → Master  (3 API calls)
    Slow path  : Division pages  (only if fast path yields < count)

    PUUIDs are resolved from summonerId (1 call each, batched).
    summonerName resolution is skipped — summonerId is always present
    and avoids an extra round-trip per entry.
    """

    def __init__(self, api_client: RiotAPIClient, summoner_repo: SummonerRepository) -> None:
        self.api_client    = api_client
        self.summoner_repo = summoner_repo

    async def discover_seed_puuids(
        self, region: Region, queue_type: QueueType, count: int = 50
    ) -> List[str]:
        summoner_ids: List[str] = []

        # ── Fast path: Challenger / Grandmaster / Master ──────────────
        try:
            blobs = await asyncio.gather(
                self.api_client.get_challenger_league(region, queue_type),
                self.api_client.get_grandmaster_league(region, queue_type),
                self.api_client.get_master_league(region, queue_type),
                return_exceptions=True,
            )
            for blob in blobs:
                if isinstance(blob, Exception) or not blob:
                    continue
                for entry in blob.get("entries", []):
                    sid = entry.get("summonerId")
                    if sid and sid not in summoner_ids:
                        summoner_ids.append(sid)
                    if len(summoner_ids) >= count:
                        break
                if len(summoner_ids) >= count:
                    break
        except Exception:
            pass

        # ── Slow path: division pages (only if still short) ───────────
        if len(summoner_ids) < count:
            tiers     = ["GOLD", "PLATINUM", "EMERALD", "DIAMOND", "SILVER"]
            divisions = ["I", "II"]
            for tier in tiers:
                for div in divisions:
                    try:
                        entries = await self.api_client.get_league_entries(
                            region, queue_type, tier, div, page=1
                        )
                        if not entries:
                            continue
                        for entry in entries:
                            sid = entry.get("summonerId")
                            if sid and sid not in summoner_ids:
                                summoner_ids.append(sid)
                            if len(summoner_ids) >= count:
                                break
                    except Exception:
                        continue
                    if len(summoner_ids) >= count:
                        break
                if len(summoner_ids) >= count:
                    break

        if not summoner_ids:
            return []

        # ── Resolve summonerIds → PUUIDs (batched, concurrent) ────────
        batch   = summoner_ids[:count]
        tasks   = [self.summoner_repo.get_summoner_by_id(region, sid) for sid in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        puuids: List[str] = []
        seen:   set       = set()
        for r in results:
            if isinstance(r, Exception) or r is None:
                continue
            p = r.puuid
            if p and p not in seen:
                seen.add(p)
                puuids.append(p)

        return puuids