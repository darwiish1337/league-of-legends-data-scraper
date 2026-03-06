"""
Shared pytest fixtures and configuration for all tests.

This module provides:
- Temporary database fixtures
- Environment setup/teardown
- Mock objects for testing
"""
import os
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def setup_testing_env():
    """Automatically set TESTING=true for all tests."""
    os.environ['TESTING'] = 'true'
    yield
    os.environ.pop('TESTING', None)


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test database."""
    db_dir = Path(tempfile.mkdtemp(prefix="riot_test_"))
    yield db_dir
    
    # Cleanup
    import shutil
    if db_dir.exists():
        try:
            shutil.rmtree(db_dir)
        except:
            pass


@pytest.fixture
def temp_db_path(temp_db_dir):
    """Get path to temporary test database."""
    return temp_db_dir / "test.sqlite"


@pytest.fixture
def mock_riot_client():
    """Mock Riot API client."""
    from unittest.mock import AsyncMock, MagicMock
    
    client = MagicMock()
    client.get_match_ids = AsyncMock(return_value=[])
    client.get_match = AsyncMock(return_value=None)
    client.get_summoner_by_name = AsyncMock(return_value=None)
    client.get_league_entries = AsyncMock(return_value=[])
    
    return client


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter."""
    from unittest.mock import AsyncMock, MagicMock
    
    limiter = MagicMock()
    limiter.acquire = AsyncMock()
    limiter.get_status = MagicMock(return_value=(0, 10, 0, 100))
    
    return limiter


@pytest.fixture
def persistence_service(temp_db_path):
    """Create DataPersistenceService with temp database."""
    from config import settings
    from application.services.data_persistence_service import DataPersistenceService
    
    original_db_dir = settings.DB_DIR
    settings.DB_DIR = temp_db_path.parent
    
    service = DataPersistenceService(temp_db_path)
    
    yield service
    
    # Cleanup
    try:
        service._conn.close()
    except:
        pass
    
    settings.DB_DIR = original_db_dir


@pytest.fixture
def sample_session_id():
    """Provide a sample session ID for tests."""
    return "test_session_12345"


@pytest.fixture
def sample_regions():
    """Provide sample regions for tests."""
    return ["EUW1", "NA1", "KR"]
