"""Rank tier enumeration."""
from enum import Enum


class Rank(Enum):
    """League of Legends rank tiers."""
    
    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"
    
    @property
    def tier_value(self) -> str:
        """Get tier string value."""
        return self.value
    
    @classmethod
    def all_ranks(cls) -> list['Rank']:
        """Get all rank tiers."""
        return list(cls)
    
    @classmethod
    def from_string(cls, rank_str: str) -> 'Rank':
        """Create Rank from string."""
        try:
            return cls[rank_str.upper()]
        except KeyError:
            return cls.SILVER  # Default fallback
