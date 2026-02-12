"""Participant entity representing a player in a match."""
from dataclasses import dataclass, field
from typing import Optional
from ..enums import Role, Rank


@dataclass
class Participant:
    """Represents a player participant in a match."""
    
    # Identity
    puuid: str
    summoner_name: str
    summoner_id: str
    summoner_level: int
    
    # Match context
    team_id: int
    participant_id: int
    champion_id: int
    champion_name: str
    
    # Position/Role
    individual_position: Role
    team_position: Role
    
    # Rank (to be fetched separately)
    rank_tier: Optional[Rank] = None
    rank_division: Optional[str] = None
    
    # Summoner Spells
    summoner1_id: int = 0
    summoner2_id: int = 0
    summoner1_name: str = ""
    summoner2_name: str = ""
    
    # Match outcome
    win: bool = False
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    
    # Gold & Experience
    gold_earned: int = 0
    gold_spent: int = 0
    total_minions_killed: int = 0
    champion_experience: int = 0
    
    # Damage
    total_damage_dealt_to_champions: int = 0
    total_damage_taken: int = 0
    physical_damage_dealt_to_champions: int = 0
    magic_damage_dealt_to_champions: int = 0
    true_damage_dealt_to_champions: int = 0
    
    # Vision
    vision_score: int = 0
    wards_placed: int = 0
    wards_killed: int = 0
    vision_wards_bought_in_game: int = 0
    
    # Items (slots 0-6)
    item0: int = 0
    item1: int = 0
    item2: int = 0
    item3: int = 0
    item4: int = 0
    item5: int = 0
    item6: int = 0  # Trinket
    
    # Objectives
    turret_kills: int = 0
    inhibitor_kills: int = 0
    dragon_kills: int = 0
    baron_kills: int = 0
    
    # Additional stats
    total_time_cc_dealt: int = 0
    time_ccing_others: int = 0
    longest_time_spent_living: int = 0
    total_heal: int = 0
    
    @property
    def items_list(self) -> list[int]:
        """Get list of all items (excluding trinket)."""
        return [
            self.item0, self.item1, self.item2,
            self.item3, self.item4, self.item5
        ]
    
    @property
    def summoner_spells(self) -> tuple[int, int]:
        """Get summoner spell IDs as tuple."""
        return (self.summoner1_id, self.summoner2_id)
    
    @property
    def kda(self) -> float:
        """Calculate KDA ratio."""
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return (self.kills + self.assists) / self.deaths
    
    def to_dict(self) -> dict:
        """Convert participant to dictionary."""
        return {
            'puuid': self.puuid,
            'summoner_name': self.summoner_name,
            'summoner_id': self.summoner_id,
            'summoner_level': self.summoner_level,
            'team_id': self.team_id,
            'participant_id': self.participant_id,
            'champion_id': self.champion_id,
            'champion_name': self.champion_name,
            'position': self.individual_position.value if self.individual_position else None,
            'rank_tier': self.rank_tier.value if self.rank_tier else None,
            'rank_division': self.rank_division,
            'summoner1_id': self.summoner1_id,
            'summoner2_id': self.summoner2_id,
            'summoner1_name': self.summoner1_name,
            'summoner2_name': self.summoner2_name,
            'win': self.win,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'kda': self.kda,
            'gold_earned': self.gold_earned,
            'gold_spent': self.gold_spent,
            'cs': self.total_minions_killed,
            'champion_experience': self.champion_experience,
            'total_damage_dealt': self.total_damage_dealt_to_champions,
            'total_damage_taken': self.total_damage_taken,
            'physical_damage': self.physical_damage_dealt_to_champions,
            'magic_damage': self.magic_damage_dealt_to_champions,
            'true_damage': self.true_damage_dealt_to_champions,
            'vision_score': self.vision_score,
            'wards_placed': self.wards_placed,
            'wards_killed': self.wards_killed,
            'control_wards_placed': self.vision_wards_bought_in_game,
            'items': self.items_list,
            'trinket': self.item6,
            'turret_kills': self.turret_kills,
            'inhibitor_kills': self.inhibitor_kills,
            'dragon_kills': self.dragon_kills,
            'baron_kills': self.baron_kills,
        }
