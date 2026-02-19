__version__ = "1.0.0"
__author__ = "Data Engineering Team"

from .domain import (
    Match, Participant, Team, Summoner,
    Region, QueueType, Rank, Role
)

from .infrastructure import (
    RiotAPIClient,
    MatchRepository,
    SummonerRepository
)

from .application import (
    DataScraperService,
    ScrapeMatchesUseCase,
)

from .config import settings

__all__ = [
    '__version__',
    '__author__',
    'Match',
    'Participant',
    'Team',
    'Summoner',
    'Region',
    'QueueType',
    'Rank',
    'Role',
    'RiotAPIClient',
    'MatchRepository',
    'SummonerRepository',
    'DataScraperService',
    'ScrapeMatchesUseCase',
    'settings',
]
