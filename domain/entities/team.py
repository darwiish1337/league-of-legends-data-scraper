"""Team entity representing a team in a match."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Team:
    """Represents a team (5 players) in a match."""
    
    # Identity
    team_id: int  # 100 or 200
    win: bool
    
    # Objectives - Dragons
    dragon_kills: int = 0
    first_dragon: bool = False
    
    # Dragon types killed
    air_dragons: int = 0
    chemtech_dragons: int = 0
    earth_dragons: int = 0
    elder_dragons: int = 0
    fire_dragons: int = 0
    hextech_dragons: int = 0
    infernal_dragons: int = 0
    mountain_dragons: int = 0
    ocean_dragons: int = 0
    water_dragons: int = 0
    
    # Objectives - Baron
    baron_kills: int = 0
    first_baron: bool = False
    
    # Objectives - Rift Herald/Voidgrubs
    rift_herald_kills: int = 0
    first_rift_herald: bool = False
    
    # Void Grubs (new objective)
    horde_kills: int = 0  # Voidgrubs
    
    # Objectives - Towers
    tower_kills: int = 0
    first_tower: bool = False
    
    # Objectives - Inhibitors
    inhibitor_kills: int = 0
    first_inhibitor: bool = False
    
    # Objectives - Other
    champion_kills: int = 0
    first_blood: bool = False
    
    # Atakhan (new objective in patch 26.01)
    atakhan_kills: int = 0
    first_atakhan: bool = False
    
    # Team gold & experience
    total_gold: int = 0
    total_experience: int = 0
    
    # Bans
    bans: list[int] = field(default_factory=list)
    
    @property
    def total_dragons_killed(self) -> int:
        """Calculate total dragons (excluding elder)."""
        return (self.air_dragons + self.chemtech_dragons + 
                self.earth_dragons + self.fire_dragons + 
                self.hextech_dragons + self.infernal_dragons + 
                self.mountain_dragons + self.ocean_dragons + 
                self.water_dragons)
    
    @property
    def dragon_soul(self) -> bool:
        """Check if team got dragon soul (4 dragons)."""
        return self.total_dragons_killed >= 4
    
    def to_dict(self) -> dict:
        """Convert team to dictionary."""
        return {
            'team_id': self.team_id,
            'win': self.win,
            'dragon_kills': self.dragon_kills,
            'first_dragon': self.first_dragon,
            'air_dragons': self.air_dragons,
            'chemtech_dragons': self.chemtech_dragons,
            'earth_dragons': self.earth_dragons,
            'elder_dragons': self.elder_dragons,
            'fire_dragons': self.fire_dragons,
            'hextech_dragons': self.hextech_dragons,
            'infernal_dragons': self.infernal_dragons,
            'mountain_dragons': self.mountain_dragons,
            'ocean_dragons': self.ocean_dragons,
            'water_dragons': self.water_dragons,
            'total_dragons': self.total_dragons_killed,
            'dragon_soul': self.dragon_soul,
            'baron_kills': self.baron_kills,
            'first_baron': self.first_baron,
            'rift_herald_kills': self.rift_herald_kills,
            'first_rift_herald': self.first_rift_herald,
            'voidgrub_kills': self.horde_kills,
            'atakhan_kills': self.atakhan_kills,
            'first_atakhan': self.first_atakhan,
            'tower_kills': self.tower_kills,
            'first_tower': self.first_tower,
            'inhibitor_kills': self.inhibitor_kills,
            'first_inhibitor': self.first_inhibitor,
            'champion_kills': self.champion_kills,
            'first_blood': self.first_blood,
            'total_gold': self.total_gold,
            'total_experience': self.total_experience,
            'bans': self.bans,
        }
