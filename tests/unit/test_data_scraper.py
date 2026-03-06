"""
Unit tests for DataScraperService.

Tests:
- Service initialization
- Callback registration
- Deduplication logic
"""
import pytest
from unittest.mock import MagicMock
from application.services.data_scraper.data_scraper_service import DataScraperService


class TestDataScraperService:
    """Test DataScraperService class."""

    def test_initialization(self, mock_riot_client, mock_rate_limiter):
        """Test service initializes correctly."""
        scraper = DataScraperService(
            match_repo=MagicMock(),
            summoner_repo=MagicMock(),
        )
        
        assert scraper is not None
        assert scraper.scraped_match_ids is not None
        assert scraper.scraped_puuids is not None
        assert scraper.processed_puuids is not None

    def test_progress_callback_registration(self, mock_riot_client, mock_rate_limiter):
        """Test progress callback can be registered."""
        def progress_callback(current, total):
            pass
        
        scraper = DataScraperService(
            match_repo=MagicMock(),
            summoner_repo=MagicMock(),
            progress_callback=progress_callback,
        )
        
        assert scraper.progress_cb == progress_callback

    def test_status_callback_registration(self, mock_riot_client, mock_rate_limiter):
        """Test status callback can be registered."""
        def status_callback(status):
            pass
        
        scraper = DataScraperService(
            match_repo=MagicMock(),
            summoner_repo=MagicMock(),
            status_callback=status_callback,
        )
        
        assert scraper.status_cb == status_callback

    def test_deduplication_sets(self, mock_riot_client, mock_rate_limiter):
        """Test deduplication sets are initialized."""
        scraper = DataScraperService(
            match_repo=MagicMock(),
            summoner_repo=MagicMock(),
        )
        
        assert isinstance(scraper.scraped_match_ids, set)
        assert isinstance(scraper.scraped_puuids, set)
        assert isinstance(scraper.processed_puuids, set)

    def test_both_callbacks_together(self, mock_riot_client, mock_rate_limiter):
        """Test registering both callbacks at same time."""
        def progress_cb(current, total):
            pass
        
        def status_cb(status):
            pass
        
        scraper = DataScraperService(
            match_repo=MagicMock(),
            summoner_repo=MagicMock(),
            progress_callback=progress_cb,
            status_callback=status_cb,
        )
        
        assert scraper.progress_cb == progress_cb
        assert scraper.status_cb == status_cb
