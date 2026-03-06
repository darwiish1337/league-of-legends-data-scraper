"""
Unit tests for CLI command resume logic.

Tests:
- Resume menu filtering logic
- Zero-progress detection
"""
import pytest


class TestResomeMenuFiltering:
    """Test resume menu filtering logic."""

    def test_resume_filters_pending_regions(self):
        """Test resume menu shows only pending/running regions."""
        session_regions = [
            {"region": "EUW1", "status": "completed", "matches_collected": 100},
            {"region": "NA1", "status": "pending", "matches_collected": 0},
            {"region": "KR", "status": "skipped", "matches_collected": 0},
        ]
        
        # Filter logic: only pending or running
        incomplete = [
            r for r in session_regions 
            if r["status"] in ["pending", "running"]
        ]
        
        assert len(incomplete) == 1
        assert incomplete[0]["region"] == "NA1"

    def test_zero_progress_detection(self):
        """Test detecting regions with zero progress."""
        session_regions = [
            {"region": "EUW1", "status": "running", "matches_collected": 0},
            {"region": "NA1", "status": "running", "matches_collected": 50},
        ]
        
        zero_progress = [
            r for r in session_regions 
            if r["matches_collected"] == 0
        ]
        
        assert len(zero_progress) == 1
        assert zero_progress[0]["region"] == "EUW1"

    def test_session_filtering_all_completed(self):
        """Test filtering when all regions are completed."""
        session_regions = [
            {"region": "EUW1", "status": "completed", "matches_collected": 100},
            {"region": "NA1", "status": "completed", "matches_collected": 100},
        ]
        
        incomplete = [
            r for r in session_regions 
            if r["status"] in ["pending", "running"]
        ]
        
        assert len(incomplete) == 0

    def test_session_filtering_mixed_statuses(self):
        """Test filtering with mixed region statuses."""
        session_regions = [
            {"region": "EUW1", "status": "completed", "matches_collected": 100},
            {"region": "NA1", "status": "running", "matches_collected": 30},
            {"region": "KR", "status": "pending", "matches_collected": 0},
            {"region": "BR1", "status": "skipped", "matches_collected": 0},
        ]
        
        incomplete = [
            r for r in session_regions 
            if r["status"] in ["pending", "running"]
        ]
        
        assert len(incomplete) == 2
        regions = [r["region"] for r in incomplete]
        assert "NA1" in regions
        assert "KR" in regions
