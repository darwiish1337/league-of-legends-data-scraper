"""
Unit tests for DataPersistenceService.

Tests:
- Session creation and retrieval
- Region status transitions
- Progress tracking
- Database structure
"""
import pytest
from application.services.data_persistence_service import DataPersistenceService


class TestDataPersistenceService:
    """Test DataPersistenceService class."""

    def test_initialization(self, temp_db_path):
        """Test service initializes with database."""
        service = DataPersistenceService(temp_db_path)
        
        assert service is not None
        assert service._conn is not None
        
        service._conn.close()

    def test_create_session(self, persistence_service, sample_session_id, sample_regions):
        """Test creating a new scraping session."""
        persistence_service.create_session(
            sample_session_id, 
            sample_regions, 
            target=100, 
            patch="16.3"
        )
        
        sessions = persistence_service.get_incomplete_sessions()
        
        assert len(sessions) > 0
        assert sessions[0]["session_id"] == sample_session_id

    def test_get_session_regions(self, persistence_service, sample_session_id, sample_regions):
        """Test retrieving regions for a session."""
        persistence_service.create_session(
            sample_session_id, 
            sample_regions, 
            target=100, 
            patch="16.3"
        )
        
        regions = persistence_service.get_session_regions(sample_session_id)
        
        assert len(regions) == len(sample_regions)
        assert all(r["status"] == "pending" for r in regions)

    def test_mark_region_running(self, persistence_service, sample_session_id):
        """Test marking a region as running."""
        persistence_service.create_session(
            sample_session_id, 
            ["EUW1"], 
            target=100, 
            patch="16.3"
        )
        
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        
        regions = persistence_service.get_session_regions(sample_session_id)
        assert regions[0]["status"] == "running"

    def test_update_region_progress(self, persistence_service, sample_session_id):
        """Test updating progress for a region."""
        persistence_service.create_session(
            sample_session_id, 
            ["EUW1"], 
            target=100, 
            patch="16.3"
        )
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        
        # Update progress
        persistence_service.update_region_progress(sample_session_id, "EUW1", 25)
        
        regions = persistence_service.get_session_regions(sample_session_id)
        assert regions[0]["matches_collected"] == 25

    def test_mark_region_completed(self, persistence_service, sample_session_id):
        """Test marking a region as completed."""
        persistence_service.create_session(
            sample_session_id, 
            ["EUW1"], 
            target=100, 
            patch="16.3"
        )
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        persistence_service.mark_region_completed(sample_session_id, "EUW1", 100)
        
        regions = persistence_service.get_session_regions(sample_session_id)
        
        assert regions[0]["status"] == "completed"
        assert regions[0]["matches_collected"] == 100

    def test_mark_region_skipped(self, persistence_service, sample_session_id):
        """Test marking a region as skipped."""
        persistence_service.create_session(
            sample_session_id, 
            ["EUW1"], 
            target=100, 
            patch="16.3"
        )
        persistence_service.mark_region_skipped(sample_session_id, "EUW1")
        
        regions = persistence_service.get_session_regions(sample_session_id)
        assert regions[0]["status"] == "skipped"

    def test_database_table_structure(self, persistence_service):
        """Test all required database tables exist."""
        cur = persistence_service._conn.cursor()
        
        required_tables = [
            "matches", "platforms", "teams", "participants",
            "champions", "items", "summoner_spells",
            "scrape_sessions", "scrape_session_regions"
        ]
        
        for table in required_tables:
            cur.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            assert cur.fetchone() is not None, f"Table {table} not found"

    def test_multiple_regions_independent_progress(self, persistence_service, sample_session_id):
        """Test that progress is tracked independently per region."""
        regions = ["EUW1", "NA1"]
        persistence_service.create_session(
            sample_session_id, 
            regions, 
            target=100, 
            patch="16.3"
        )
        
        # Update progress for different regions
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        persistence_service.update_region_progress(sample_session_id, "EUW1", 50)
        
        persistence_service.mark_region_running(sample_session_id, "NA1")
        persistence_service.update_region_progress(sample_session_id, "NA1", 25)
        
        # Verify independent progress
        region_rows = {r["region"]: r for r in persistence_service.get_session_regions(sample_session_id)}
        
        assert region_rows["EUW1"]["matches_collected"] == 50
        assert region_rows["NA1"]["matches_collected"] == 25

    def test_zero_progress_session_detection(self, persistence_service, sample_session_id):
        """Test sessions with zero collected matches."""
        persistence_service.create_session(
            sample_session_id, 
            ["EUW1"], 
            target=100, 
            patch="16.3"
        )
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        
        # No progress update, so matches_collected remains 0
        regions = persistence_service.get_session_regions(sample_session_id)
        assert regions[0]["matches_collected"] == 0
