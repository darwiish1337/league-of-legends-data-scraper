"""Repository interfaces for data access."""
from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities import Match, Summoner
from ..enums import Region, QueueType


class IMatchRepository(ABC):
    """Interface for match data repository."""
    
    @abstractmethod
    async def get_match_by_id(self, region: Region, match_id: str) -> Optional[Match]:
        """Get a single match by ID."""
        pass
    
    @abstractmethod
    async def get_match_ids_by_puuid(
        self, 
        region: Region, 
        puuid: str, 
        queue_type: QueueType,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start: int = 0,
        count: int = 100
    ) -> List[str]:
        """Get match IDs for a summoner."""
        pass
    
    @abstractmethod
    async def save_match(self, match: Match) -> bool:
        """Save a match to storage."""
        pass


class ISummonerRepository(ABC):
    """Interface for summoner data repository."""
    
    @abstractmethod
    async def get_summoner_by_puuid(self, region: Region, puuid: str) -> Optional[Summoner]:
        """Get summoner by PUUID."""
        pass
    
    @abstractmethod
    async def get_summoner_rank_info(self, region: Region, summoner_id: str) -> dict:
        """Get summoner ranked information."""
        pass
