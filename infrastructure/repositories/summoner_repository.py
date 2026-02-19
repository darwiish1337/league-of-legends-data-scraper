"""Summoner repository implementation."""
import logging
from typing import Optional

from domain.entities import Summoner
from domain.enums import Region
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
        
        # Create summoner entity
        summoner = Summoner(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            summoner_name=summoner_data['name'],
            profile_icon_id=summoner_data['profileIconId'],
            summoner_level=summoner_data['summonerLevel']
        )
        
        return summoner
    
    async def get_summoner_by_id(
        self,
        region: Region,
        summoner_id: str
    ) -> Optional[Summoner]:
        summoner_data = await self.api_client.get_summoner_by_id(region, summoner_id)
        if not summoner_data:
            return None
        
        summoner = Summoner(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            summoner_name=summoner_data['name'],
            profile_icon_id=summoner_data['profileIconId'],
            summoner_level=summoner_data['summonerLevel']
        )
        
        return summoner
    
    async def get_summoner_by_name(
        self,
        region: Region,
        summoner_name: str
    ) -> Optional[Summoner]:
        summoner_data = await self.api_client.get_summoner_by_name(region, summoner_name)
        if not summoner_data:
            return None
        summoner = Summoner(
            puuid=summoner_data['puuid'],
            summoner_id=summoner_data['id'],
            account_id=summoner_data['accountId'],
            summoner_name=summoner_data['name'],
            profile_icon_id=summoner_data['profileIconId'],
            summoner_level=summoner_data['summonerLevel']
        )
        
        return summoner
