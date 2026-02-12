"""Use case for scraping match data."""
import logging
from typing import Dict, List

from domain.entities import Match
from domain.enums import Region, QueueType
from infrastructure import RiotAPIClient, MatchRepository, SummonerRepository
from application.services import DataScraperService
from config import settings

logger = logging.getLogger(__name__)


class ScrapeMatchesUseCase:
    """Use case for scraping match data from Riot API."""
    
    def __init__(self, api_client: RiotAPIClient, progress_callback=None, status_callback=None):
        """
        Initialize use case.
        
        Args:
            api_client: Riot API client instance
        """
        self.api_client = api_client
        self.match_repo = MatchRepository(api_client)
        self.summoner_repo = SummonerRepository(api_client)
        self.scraper_service = DataScraperService(
            self.match_repo,
            self.summoner_repo,
            progress_callback=progress_callback,
            status_callback=status_callback
        )
    
    async def execute(
        self,
        regions: List[Region] = None,
        queue_types: List[QueueType] = None,
        matches_per_region: int = 500
    ) -> Dict[str, Dict[str, List[Match]]]:
        """
        Execute the scraping process.
        
        Args:
            regions: List of regions to scrape (defaults to all)
            queue_types: List of queue types to scrape (defaults to both ranked)
            matches_per_region: Number of matches to scrape per region
            
        Returns:
            Dictionary mapping region -> queue_type -> matches
        """
        # Default to all regions if not specified
        if regions is None:
            regions = Region.all_regions()
        
        # Default to both ranked queues if not specified
        if queue_types is None:
            queue_types = QueueType.ranked_queues()
        
        logger.info(
            f"Starting scrape for {len(regions)} regions, "
            f"{len(queue_types)} queue types"
        )
        
        results = {}
        
        for region in regions:
            region_results = {}
            
            for queue_type in queue_types:
                logger.info(
                    f"Scraping {region.value} - {queue_type.queue_name}..."
                )
                
                try:
                    matches = await self.scraper_service.scrape_matches_from_high_elo(
                        region=region,
                        queue_type=queue_type,
                        max_matches=matches_per_region
                    )
                    
                    region_results[queue_type.queue_name] = matches
                    
                    logger.info(
                        f"Completed {region.value} - {queue_type.queue_name}: "
                        f"{len(matches)} matches"
                    )
                
                except Exception as e:
                    logger.error(
                        f"Error scraping {region.value} - {queue_type.queue_name}: {e}"
                    )
                    region_results[queue_type.queue_name] = []
            
            results[region.value] = region_results
        
        # Log summary
        total_matches = sum(
            len(matches)
            for region_data in results.values()
            for matches in region_data.values()
        )
        
        logger.info(f"Scraping complete! Total matches collected: {total_matches}")
        
        return results
