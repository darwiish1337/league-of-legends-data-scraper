"""Summoner repository implementation."""
import logging
from typing import Optional

from domain.entities import Summoner
from domain.enums import Region, Rank
from domain.interfaces import ISummonerRepository
from infrastructure.api import RiotAPIClient

logger = logging.getLogger(__name__)


class SummonerRepository(ISummonerRepository):
    """Repository for summoner data using Riot API."""
    
    def __init__(self, api_client: RiotAPIClient):
        """
        Initialize summoner repository.
        
        Args:
            api_client: Riot API client instance
        """
        self.api_client = api_client
    
    async def get_summoner_by_puuid(
        self,
        region: Region,
        puuid: str
    ) -> Optional[Summoner]:
        """
        Get summoner by PUUID.
        
        Args:
            region: Server region
            puuid: Player UUID
            
        Returns:
            Summoner entity or None
        """
        summoner_data = await self.api_client.get_summoner_by_puuid(region, puuid)
        if not summoner_data:
            return None
        
        # Get ranked information
        summoner_id = summoner_data['id']
        rank_info = await self.get_summoner_rank_info(region, summoner_id)
        
        # Create summoner entity
        summoner = Summoner(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            summoner_name=summoner_data['name'],
            profile_icon_id=summoner_data['profileIconId'],
            summoner_level=summoner_data['summonerLevel']
        )
        
        # Add ranked info
        if 'solo' in rank_info:
            solo = rank_info['solo']
            summoner.solo_tier = Rank.from_string(solo['tier'])
            summoner.solo_division = solo['rank']
            summoner.solo_lp = solo['leaguePoints']
            summoner.solo_wins = solo['wins']
            summoner.solo_losses = solo['losses']
        
        if 'flex' in rank_info:
            flex = rank_info['flex']
            summoner.flex_tier = Rank.from_string(flex['tier'])
            summoner.flex_division = flex['rank']
            summoner.flex_lp = flex['leaguePoints']
            summoner.flex_wins = flex['wins']
            summoner.flex_losses = flex['losses']
        
        return summoner
    
    async def get_summoner_by_id(
        self,
        region: Region,
        summoner_id: str
    ) -> Optional[Summoner]:
        summoner_data = await self.api_client.get_summoner_by_id(region, summoner_id)
        if not summoner_data:
            return None
        
        rank_info = await self.get_summoner_rank_info(region, summoner_data['id'])
        
        summoner = Summoner(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            summoner_name=summoner_data['name'],
            profile_icon_id=summoner_data['profileIconId'],
            summoner_level=summoner_data['summonerLevel']
        )
        
        if 'solo' in rank_info:
            solo = rank_info['solo']
            summoner.solo_tier = Rank.from_string(solo['tier'])
            summoner.solo_division = solo['rank']
            summoner.solo_lp = solo['leaguePoints']
            summoner.solo_wins = solo['wins']
            summoner.solo_losses = solo['losses']
        
        if 'flex' in rank_info:
            flex = rank_info['flex']
            summoner.flex_tier = Rank.from_string(flex['tier'])
            summoner.flex_division = flex['rank']
            summoner.flex_lp = flex['leaguePoints']
            summoner.flex_wins = flex['wins']
            summoner.flex_losses = flex['losses']
        
        return summoner
    
    async def get_summoner_by_name(
        self,
        region: Region,
        summoner_name: str
    ) -> Optional[Summoner]:
        summoner_data = await self.api_client.get_summoner_by_name(region, summoner_name)
        if not summoner_data:
            return None
        
        rank_info = await self.get_summoner_rank_info(region, summoner_data['id'])
        
        summoner = Summoner(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            summoner_name=summoner_data['name'],
            profile_icon_id=summoner_data['profileIconId'],
            summoner_level=summoner_data['summonerLevel']
        )
        
        if 'solo' in rank_info:
            solo = rank_info['solo']
            summoner.solo_tier = Rank.from_string(solo['tier'])
            summoner.solo_division = solo['rank']
            summoner.solo_lp = solo['leaguePoints']
            summoner.solo_wins = solo['wins']
            summoner.solo_losses = solo['losses']
        
        if 'flex' in rank_info:
            flex = rank_info['flex']
            summoner.flex_tier = Rank.from_string(flex['tier'])
            summoner.flex_division = flex['rank']
            summoner.flex_lp = flex['leaguePoints']
            summoner.flex_wins = flex['wins']
            summoner.flex_losses = flex['losses']
        
        return summoner
    
    async def get_summoner_rank_info(
        self,
        region: Region,
        summoner_id: str
    ) -> dict:
        """
        Get summoner ranked information.
        
        Args:
            region: Server region
            summoner_id: Summoner ID (encrypted)
            
        Returns:
            Dictionary with 'solo' and 'flex' rank info
        """
        entries = await self.api_client.get_league_entries_by_summoner(
            region, summoner_id
        )
        
        if not entries:
            return {}
        
        result = {}
        
        for entry in entries:
            queue_type = entry['queueType']
            
            if queue_type == 'RANKED_SOLO_5x5':
                result['solo'] = entry
            elif queue_type == 'RANKED_FLEX_SR':
                result['flex'] = entry
        
        return result

    async def get_summoner_rank_info_flexible(
        self,
        region: Region,
        puuid: str,
        summoner_id: str
    ) -> dict:
        """
        Try to get rank info by PUUID first, then fallback to summoner_id.
        Returns dict with optional 'solo' and 'flex' entries.
        """
        # Try by PUUID
        entries = await self.api_client.get_league_entries_by_puuid(region, puuid)
        if not entries:
            entries = await self.api_client.get_league_entries_by_summoner(region, summoner_id)
            if not entries:
                return {}
        result = {}
        for entry in entries:
            q = entry.get('queueType')
            if q == 'RANKED_SOLO_5x5':
                result['solo'] = entry
            elif q == 'RANKED_FLEX_SR':
                result['flex'] = entry
        return result
