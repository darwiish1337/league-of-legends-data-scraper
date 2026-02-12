"""Summoner entity representing a player account."""
from dataclasses import dataclass
from typing import Optional
from ..enums import Rank


@dataclass
class Summoner:
    """Represents a League of Legends summoner/player."""
    
    # Identity
    puuid: str
    summoner_id: str
    account_id: str
    summoner_name: str
    profile_icon_id: int
    summoner_level: int
    
    # Ranked info (Solo/Duo)
    solo_tier: Optional[Rank] = None
    solo_division: Optional[str] = None
    solo_lp: int = 0
    solo_wins: int = 0
    solo_losses: int = 0
    
    # Ranked info (Flex)
    flex_tier: Optional[Rank] = None
    flex_division: Optional[str] = None
    flex_lp: int = 0
    flex_wins: int = 0
    flex_losses: int = 0
    
    @property
    def solo_winrate(self) -> float:
        """Calculate solo queue win rate."""
        total = self.solo_wins + self.solo_losses
        if total == 0:
            return 0.0
        return (self.solo_wins / total) * 100
    
    @property
    def flex_winrate(self) -> float:
        """Calculate flex queue win rate."""
        total = self.flex_wins + self.flex_losses
        if total == 0:
            return 0.0
        return (self.flex_wins / total) * 100
    
    def to_dict(self) -> dict:
        """Convert summoner to dictionary."""
        return {
            'puuid': self.puuid,
            'summoner_id': self.summoner_id,
            'account_id': self.account_id,
            'summoner_name': self.summoner_name,
            'profile_icon_id': self.profile_icon_id,
            'summoner_level': self.summoner_level,
            'solo_tier': self.solo_tier.value if self.solo_tier else None,
            'solo_division': self.solo_division,
            'solo_lp': self.solo_lp,
            'solo_wins': self.solo_wins,
            'solo_losses': self.solo_losses,
            'solo_winrate': round(self.solo_winrate, 2),
            'flex_tier': self.flex_tier.value if self.flex_tier else None,
            'flex_division': self.flex_division,
            'flex_lp': self.flex_lp,
            'flex_wins': self.flex_wins,
            'flex_losses': self.flex_losses,
            'flex_winrate': round(self.flex_winrate, 2),
        }
