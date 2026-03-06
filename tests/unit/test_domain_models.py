"""
Unit tests for domain models and enumerations.

Tests:
- Region enum
- QueueType enum
- Match entity
"""
import pytest
from domain.enums import Region, QueueType
from domain.entities import Match, Team


class TestRegionEnum:
    """Test Region enumeration."""

    def test_all_regions_exist(self):
        """Test all_regions() returns regions."""
        regions = Region.all_regions()
        
        assert len(regions) > 0
        assert isinstance(regions, (list, tuple))

    def test_region_values(self):
        """Test region enum values are lowercase."""
        for region in Region.all_regions():
            assert region.value == region.value.lower()

    def test_known_regions_present(self):
        """Test known League regions are present."""
        region_names = [r.value for r in Region.all_regions()]
        
        expected_regions = ["euw1", "na1", "kr"]
        for expected in expected_regions:
            assert expected in region_names, f"Region {expected} not found"

    def test_regional_route_attribute(self):
        """Test region has regional_route attribute."""
        region = Region.EUW1
        
        assert hasattr(region, "regional_route")
        assert region.regional_route is not None


class TestQueueTypeEnum:
    """Test QueueType enumeration."""

    def test_ranked_queues_exist(self):
        """Test ranked_queues() returns queues."""
        queues = QueueType.ranked_queues()
        
        assert len(queues) > 0
        assert isinstance(queues, (list, tuple))

    def test_ranked_queues_have_queue_id(self):
        """Test all ranked queues have queue_id."""
        for queue in QueueType.ranked_queues():
            assert hasattr(queue, "queue_id")
            assert queue.queue_id is not None

    def test_specific_queues(self):
        """Test specific queue types exist."""
        assert hasattr(QueueType, "RANKED_SOLO_5x5")
        assert hasattr(QueueType, "RANKED_FLEX_SR")

    def test_queue_id_values(self):
        """Test queue_id values are integers."""
        for queue in QueueType.ranked_queues():
            assert isinstance(queue.queue_id, int)


class TestMatchEntity:
    """Test Match entity."""

    @pytest.fixture
    def sample_team(self):
        """Create a sample team."""
        return Team(team_id=100, win=True)

    @pytest.fixture
    def sample_match_data(self, sample_team):
        """Create sample match data."""
        return {
            "match_id": "EUW1_123456",
            "game_id": 12345,
            "region": Region.EUW1,
            "platform_id": "euw1",
            "queue_id": 420,
            "queue_type": QueueType.RANKED_SOLO_5x5,
            "game_version": "16.3",
            "game_mode": "CLASSIC",
            "game_type": "MATCHED_GAME",
            "game_creation": 1700000000000,
            "game_start_timestamp": 1700000100000,
            "game_end_timestamp": 1700000400000,
            "game_duration": 300,
            "team_100": sample_team,
            "team_200": sample_team,
        }

    def test_match_creation(self, sample_match_data):
        """Test Match entity can be created."""
        match = Match(**sample_match_data)
        
        assert match.match_id == "EUW1_123456"
        assert match.game_id == 12345

    def test_match_region(self, sample_match_data):
        """Test Match stores region correctly."""
        match = Match(**sample_match_data)
        
        assert match.region == Region.EUW1

    def test_match_queue_type(self, sample_match_data):
        """Test Match stores queue type correctly."""
        match = Match(**sample_match_data)
        
        assert match.queue_type == QueueType.RANKED_SOLO_5x5

    def test_match_duration(self, sample_match_data):
        """Test Match calculates duration correctly."""
        match = Match(**sample_match_data)
        
        assert match.game_duration == 300

    def test_match_version(self, sample_match_data):
        """Test Match stores version."""
        match = Match(**sample_match_data)
        
        assert match.game_version == "16.3"
