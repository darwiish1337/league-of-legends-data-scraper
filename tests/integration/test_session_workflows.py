"""
Integration tests for complete workflows.

Tests:
- Full session lifecycle
- Resume after crash
- Persistence across instances
"""
import pytest
from application.services.data_persistence_service import DataPersistenceService


class TestSessionLifecycle:
    """Test complete session lifecycle."""

    def test_create_progress_complete_workflow(self, persistence_service, sample_session_id):
        """Test full workflow: create → run → complete."""
        # Step 1: Create session
        persistence_service.create_session(
            sample_session_id,
            ["EUW1", "NA1"],
            target=100,
            patch="16.3"
        )
        
        sessions = persistence_service.get_incomplete_sessions()
        assert len(sessions) > 0
        assert sessions[0]["session_id"] == sample_session_id
        
        # Step 2: Process first region
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        persistence_service.update_region_progress(sample_session_id, "EUW1", 25)
        persistence_service.update_region_progress(sample_session_id, "EUW1", 50)
        persistence_service.update_region_progress(sample_session_id, "EUW1", 100)
        persistence_service.mark_region_completed(sample_session_id, "EUW1", 100)
        
        # Step 3: Skip second region
        persistence_service.mark_region_skipped(sample_session_id, "NA1")
        
        # Verify final state
        regions = persistence_service.get_session_regions(sample_session_id)
        statuses = {r["region"]: r["status"] for r in regions}
        
        assert statuses["EUW1"] == "completed"
        assert statuses["NA1"] == "skipped"

    def test_progress_accumulation(self, persistence_service, sample_session_id):
        """Test cumulative progress updates."""
        persistence_service.create_session(
            sample_session_id,
            ["EUW1"],
            target=100,
            patch="16.3"
        )
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        
        # Multiple progress updates
        progress_steps = [10, 25, 50, 75, 100]
        for progress in progress_steps:
            persistence_service.update_region_progress(sample_session_id, "EUW1", progress)
            
            regions = persistence_service.get_session_regions(sample_session_id)
            assert regions[0]["matches_collected"] == progress


class TestCrashRecovery:
    """Test session recovery after crash/interruption."""

    def test_resume_after_interruption(self, persistence_service, sample_session_id):
        """Simulate: scrape → save → crash → resume."""
        # Initial scraping
        persistence_service.create_session(
            sample_session_id,
            ["EUW1", "NA1"],
            target=100,
            patch="16.3"
        )
        
        # Start scraping EUW1
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        persistence_service.update_region_progress(sample_session_id, "EUW1", 50)
        
        # Simulate crash (no mark_completed)
        
        # Recover: read session state
        incomplete = persistence_service.get_incomplete_sessions()
        assert len(incomplete) > 0
        
        # Resume: get session regions
        regions = persistence_service.get_session_regions(sample_session_id)
        
        # Verify EUW1 still has progress
        euw1 = next(r for r in regions if r["region"] == "EUW1")
        assert euw1["matches_collected"] == 50
        assert euw1["status"] == "running"
        
        # Resume: NA1 should be resumable
        na1 = next(r for r in regions if r["region"] == "NA1")
        assert na1["status"] == "pending"

    def test_resume_skips_completed_regions(self, persistence_service, sample_session_id):
        """Test resume filter: skip already completed regions."""
        persistence_service.create_session(
            sample_session_id,
            ["EUW1", "NA1", "KR"],
            target=100,
            patch="16.3"
        )
        
        # Mark some regions complete
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        persistence_service.mark_region_completed(sample_session_id, "EUW1", 100)
        
        persistence_service.mark_region_skipped(sample_session_id, "NA1")
        
        # Resume: get regions to process
        regions = persistence_service.get_session_regions(sample_session_id)
        resumable = [r for r in regions if r["status"] in ["pending", "running"]]
        
        # Should only have KR
        assert len(resumable) == 1
        assert resumable[0]["region"] == "KR"


class TestMultipleRegionIsolation:
    """Test that regions maintain independent state."""

    def test_independent_progress_tracking(self, persistence_service, sample_session_id):
        """Test each region tracks progress independently."""
        regions = ["EUW1", "NA1", "KR"]
        persistence_service.create_session(
            sample_session_id,
            regions,
            target=100,
            patch="16.3"
        )
        
        # Set different progress for each
        progress_map = {"EUW1": 30, "NA1": 60, "KR": 90}
        
        for region, progress in progress_map.items():
            persistence_service.mark_region_running(sample_session_id, region)
            persistence_service.update_region_progress(sample_session_id, region, progress)
        
        # Verify independent tracking
        region_rows = persistence_service.get_session_regions(sample_session_id)
        
        for row in region_rows:
            assert row["matches_collected"] == progress_map[row["region"]]

    def test_independent_status_transitions(self, persistence_service, sample_session_id):
        """Test regions transition to different statuses independently."""
        persistence_service.create_session(
            sample_session_id,
            ["EUW1", "NA1", "KR"],
            target=100,
            patch="16.3"
        )
        
        # Transition each region differently
        persistence_service.mark_region_running(sample_session_id, "EUW1")
        persistence_service.mark_region_completed(sample_session_id, "EUW1", 100)
        
        persistence_service.mark_region_skipped(sample_session_id, "NA1")
        
        persistence_service.mark_region_running(sample_session_id, "KR")
        
        # Verify each transition
        region_rows = {r["region"]: r for r in persistence_service.get_session_regions(sample_session_id)}
        
        assert region_rows["EUW1"]["status"] == "completed"
        assert region_rows["NA1"]["status"] == "skipped"
        assert region_rows["KR"]["status"] == "running"


class TestPersistenceAcrossInstances:
    """Test data persists across service instances."""

    def test_persistence_survives_service_reinit(self, temp_db_path, sample_session_id, sample_regions):
        """Test data persists when creating new service instance."""
        # Write data with first instance
        service1 = DataPersistenceService(temp_db_path)
        service1.create_session(sample_session_id, sample_regions, 100, "16.3")
        service1.mark_region_running(sample_session_id, "EUW1")
        service1.update_region_progress(sample_session_id, "EUW1", 42)
        service1._conn.close()
        
        # Read data with new instance
        service2 = DataPersistenceService(temp_db_path)
        regions = service2.get_session_regions(sample_session_id)
        
        # Verify data persisted
        euw1 = next(r for r in regions if r["region"] == "EUW1")
        assert euw1["matches_collected"] == 42
        assert euw1["status"] == "running"
        
        service2._conn.close()

    def test_multiple_sessions_independent(self, persistence_service):
        """Test multiple concurrent sessions don't interfere."""
        session1 = "session_1"
        session2 = "session_2"
        
        # Create both sessions
        persistence_service.create_session(session1, ["EUW1"], 100, "16.3")
        persistence_service.create_session(session2, ["NA1"], 100, "16.3")
        
        # Update session1
        persistence_service.mark_region_running(session1, "EUW1")
        persistence_service.update_region_progress(session1, "EUW1", 50)
        
        # Verify session2 unaffected
        regions1 = persistence_service.get_session_regions(session1)
        regions2 = persistence_service.get_session_regions(session2)
        
        assert regions1[0]["matches_collected"] == 50
        assert regions2[0]["matches_collected"] == 0
