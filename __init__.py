"""
Riot Games League of Legends Data Scraper
==========================================

Professional-grade data scraper for LoL ranked matches (Patch 26.01).

Features:
- Clean Architecture (Domain → Infrastructure → Application → Presentation)
- SOLID Principles
- Async API calls with rate limiting
- Comprehensive match data collection
- Statistical analysis and aggregation

Author: Data Engineering Team
Version: 1.0.0
Patch: 26.01
"""

__version__ = "1.0.0"
__author__ = "Data Engineering Team"
__patch__ = "26.01"

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
    DataProcessorService,
    ScrapeMatchesUseCase,
    ProcessStatisticsUseCase
)

from .config import settings

__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__patch__',
    
    # Domain
    'Match',
    'Participant',
    'Team',
    'Summoner',
    'Region',
    'QueueType',
    'Rank',
    'Role',
    
    # Infrastructure
    'RiotAPIClient',
    'MatchRepository',
    'SummonerRepository',
    
    # Application
    'DataScraperService',
    'DataProcessorService',
    'ScrapeMatchesUseCase',
    'ProcessStatisticsUseCase',
    
    # Config
    'settings',
]
