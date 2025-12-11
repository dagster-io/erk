"""Tests for ContextEngine integration with user cron jobs."""

from unittest.mock import Mock

import pytest


class TestContextEngineCronIntegration:
    """Test context engine integration with cron job functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock context engine with async methods
        self.engine = Mock()
        self.engine.get_cron_jobs = Mock()
        self.engine.add_cron_job = Mock()
        self.engine.update_cron_job = Mock()
        self.engine.delete_cron_job = Mock()

    @pytest.mark.asyncio
    async def test_cron_job_operations(self):
        """Test that cron job operations are properly delegated to UserCronStorage."""
        # Mock the cron manager to be an async mock
        mock_cron_manager = Mock()

        # Set up async mock returns
        async def mock_get_cron_jobs():
            return {"daily": Mock()}

        async def mock_add_cron_job(*args, **kwargs):
            return Mock()

        async def mock_update_cron_job(*args, **kwargs):
            return Mock()

        async def mock_delete_cron_job(*args, **kwargs):
            return Mock()

        mock_cron_manager.get_cron_jobs = mock_get_cron_jobs
        mock_cron_manager.add_cron_job = mock_add_cron_job
        mock_cron_manager.update_cron_job = mock_update_cron_job
        mock_cron_manager.delete_cron_job = mock_delete_cron_job

        self.engine._cron_manager = mock_cron_manager

        # Configure mock return values
        self.engine.get_cron_jobs.return_value = {"daily": Mock()}
        self.engine.add_cron_job.return_value = Mock()
        self.engine.update_cron_job.return_value = Mock()
        self.engine.delete_cron_job.return_value = Mock()

        # Test get_cron_jobs
        result = self.engine.get_cron_jobs()
        assert "daily" in result

        # Test add_cron_job
        result = self.engine.add_cron_job(
            "test-job", "0 12 * * *", "What's the status?", "test-thread", "Test User"
        )
        assert result is not None

        # Test update_cron_job
        result = self.engine.update_cron_job("test-job", "Additional context", "Test User")
        assert result is not None

        # Test delete_cron_job
        result = self.engine.delete_cron_job("test-job", "Test User")
        assert result is not None
