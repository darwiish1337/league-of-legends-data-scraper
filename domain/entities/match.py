"""Match entity representing a complete match."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .participant import Participant
from .team import Team
from ..enums import QueueType, Region


@dataclass
class Match:
    """Represents a complete League of Legends match."""
    
    # Match identity
    match_id: str
    game_id: int
    
    # Match metadata
    region: Region
    platform_id: str
    queue_id: int
    queue_type: QueueType
    
    # Timing
    game_creation: int  # Unix timestamp milliseconds
    game_start_timestamp: int  # Unix timestamp milliseconds
    game_end_timestamp: int  # Unix timestamp milliseconds
    game_duration: int  # Seconds
    
    # Version & Patch
    game_version: str
    game_mode: str
    game_type: str
    
    # Teams (100 = Blue, 200 = Red)
    team_100: Team
    team_200: Team
    
    # Participants (10 players)
    participants: list[Participant] = field(default_factory=list)
    
    @property
    def game_date(self) -> datetime:
        """Get game date as datetime object."""
        return datetime.fromtimestamp(self.game_creation / 1000)
    
    @property
    def game_duration_minutes(self) -> float:
        """Get game duration in minutes."""
        return self.game_duration / 60.0
    
    @property
    def patch_version(self) -> str:
        """Extract patch version (e.g., '26.01')."""
        # game_version format: "26.01.123.456"
        parts = self.game_version.split('.')
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return self.game_version
    
    @property
    def is_patch_26_01(self) -> bool:
        """Check if match is from patch 26.01."""
        return self.patch_version == "26.01"
    
    @property
    def blue_team(self) -> Team:
        """Get blue team (team 100)."""
        return self.team_100
    
    @property
    def red_team(self) -> Team:
        """Get red team (team 200)."""
        return self.team_200
    
    @property
    def winning_team(self) -> Team:
        """Get the winning team."""
        return self.team_100 if self.team_100.win else self.team_200
    
    @property
    def losing_team(self) -> Team:
        """Get the losing team."""
        return self.team_200 if self.team_100.win else self.team_100
    
    def get_participants_by_team(self, team_id: int) -> list[Participant]:
        """Get all participants for a specific team."""
        return [p for p in self.participants if p.team_id == team_id]
    
    def to_dict(self) -> dict:
        """Convert match to dictionary."""
        return {
            'match_id': self.match_id,
            'game_id': self.game_id,
            'region': self.region.value,
            'platform_id': self.platform_id,
            'queue_id': self.queue_id,
            'queue_type': self.queue_type.queue_name,
            'game_creation': self.game_creation,
            'game_date': self.game_date.isoformat(),
            'game_start': self.game_start_timestamp,
            'game_end': self.game_end_timestamp,
            'game_duration_seconds': self.game_duration,
            'game_duration_minutes': round(self.game_duration_minutes, 2),
            'game_version': self.game_version,
            'patch_version': self.patch_version,
            'game_mode': self.game_mode,
            'game_type': self.game_type,
            'team_100': self.team_100.to_dict(),
            'team_200': self.team_200.to_dict(),
            'participants': [p.to_dict() for p in self.participants],
            'blue_team_win': self.team_100.win,
            'red_team_win': self.team_200.win,
        }
