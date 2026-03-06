"""
Unit tests for configuration and settings.

Tests:
- Required settings exist
- Directory creation
- Patch configuration
"""
import pytest
from config import settings


class TestSettingsConfiguration:
    """Test settings configuration."""

    def test_required_settings_exist(self):
        """Test all required settings are configured."""
        required_settings = [
            'RIOT_API_KEY',
            'RATE_LIMIT_PER_1_SEC',
            'RATE_LIMIT_PER_2_MIN',
            'TARGET_PATCH',
            'PATCH_START_DATE',
            'MAX_CONCURRENT_REQUESTS',
            'REQUEST_TIMEOUT',
            'MAX_RETRIES',
        ]
        
        for setting in required_settings:
            assert hasattr(settings, setting), f"Setting {setting} not found"

    def test_rate_limit_values_are_positive(self):
        """Test rate limit values are positive integers."""
        assert settings.RATE_LIMIT_PER_1_SEC > 0
        assert settings.RATE_LIMIT_PER_2_MIN > 0

    def test_concurrent_requests_is_positive(self):
        """Test MAX_CONCURRENT_REQUESTS is positive."""
        assert settings.MAX_CONCURRENT_REQUESTS > 0

    def test_timeout_is_positive(self):
        """Test REQUEST_TIMEOUT is positive."""
        assert settings.REQUEST_TIMEOUT > 0

    def test_max_retries_is_non_negative(self):
        """Test MAX_RETRIES is non-negative."""
        assert settings.MAX_RETRIES >= 0


class TestSettingsDirectories:
    """Test settings directories."""

    def test_directory_paths_exist(self):
        """Test directory paths are defined."""
        assert hasattr(settings, 'DB_DIR')
        assert hasattr(settings, 'CSV_DIR')
        assert hasattr(settings, 'LOG_DIR')

    def test_directories_are_paths(self):
        """Test directory attributes are Path objects."""
        from pathlib import Path
        
        assert isinstance(settings.DB_DIR, Path)
        assert isinstance(settings.CSV_DIR, Path)
        assert isinstance(settings.LOG_DIR, Path)


class TestPatchConfiguration:
    """Test patch configuration."""

    def test_target_patch_exists(self):
        """Test TARGET_PATCH is configured."""
        assert hasattr(settings, 'TARGET_PATCH')
        assert settings.TARGET_PATCH is not None

    def test_patch_start_date_exists(self):
        """Test PATCH_START_DATE is configured."""
        assert hasattr(settings, 'PATCH_START_DATE')
        assert settings.PATCH_START_DATE is not None

    def test_patch_format(self):
        """Test TARGET_PATCH has expected format."""
        patch = settings.TARGET_PATCH
        
        # Should be something like "16.3" or "16.*"
        assert isinstance(patch, str)
        assert len(patch) > 0
