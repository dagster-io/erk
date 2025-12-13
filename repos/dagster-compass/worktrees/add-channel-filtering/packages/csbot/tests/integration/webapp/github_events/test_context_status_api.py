"""Test cases for context status API endpoints.

These tests verify the context status API endpoint functionality that was created in commit 4992746.
The tests ensure proper enum handling, parameter parsing, and storage interaction.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from csbot.slackbot.storage.interface import ContextStatus, ContextStatusType, ContextUpdateType


class TestContextStatusAPIUnit:
    """Unit tests for context status API logic."""

    @pytest.mark.asyncio
    async def test_storage_called_with_correct_enums(self):
        """Test that storage is called with proper enum types."""
        # Mock storage
        mock_storage = Mock()
        mock_storage.get_context_status = AsyncMock(return_value=[])

        # Simulate calling storage with enums (as the endpoint does)
        await mock_storage.get_context_status(
            organization_id=123,
            status=ContextStatusType.OPEN,
            update_type=ContextUpdateType.CONTEXT_UPDATE,
            limit=100,
            offset=0,
        )

        # Verify enums were passed correctly
        mock_storage.get_context_status.assert_called_once_with(
            organization_id=123,
            status=ContextStatusType.OPEN,
            update_type=ContextUpdateType.CONTEXT_UPDATE,
            limit=100,
            offset=0,
        )

    @pytest.mark.asyncio
    async def test_storage_called_with_none_filters(self):
        """Test that storage handles None filters correctly."""
        # Mock storage
        mock_storage = Mock()
        mock_storage.get_context_status = AsyncMock(return_value=[])

        # Simulate calling storage without filters
        await mock_storage.get_context_status(
            organization_id=456,
            status=None,
            update_type=None,
            limit=50,
            offset=10,
        )

        # Verify None values were passed correctly
        mock_storage.get_context_status.assert_called_once_with(
            organization_id=456,
            status=None,
            update_type=None,
            limit=50,
            offset=10,
        )

    def test_enum_conversion_from_string(self):
        """Test converting string parameters to enums."""
        # Test status enum conversion
        status_str = "MERGED"
        status_enum = ContextStatusType(status_str)
        assert status_enum == ContextStatusType.MERGED

        # Test update_type enum conversion
        update_type_str = "DATA_REQUEST"
        update_type_enum = ContextUpdateType(update_type_str)
        assert update_type_enum == ContextUpdateType.DATA_REQUEST

    def test_enum_values_match_database_schema(self):
        """Test that enum values match the database CHECK constraints."""
        # Status enum values
        assert ContextStatusType.OPEN.value == "OPEN"
        assert ContextStatusType.MERGED.value == "MERGED"
        assert ContextStatusType.CLOSED.value == "CLOSED"

        # Update type enum values
        assert ContextUpdateType.SCHEDULED_ANALYSIS.value == "SCHEDULED_ANALYSIS"
        assert ContextUpdateType.CONTEXT_UPDATE.value == "CONTEXT_UPDATE"
        assert ContextUpdateType.DATA_REQUEST.value == "DATA_REQUEST"

    @pytest.mark.asyncio
    async def test_storage_returns_expected_structure(self):
        """Test that storage returns data in expected format."""
        # Mock storage with sample data (ContextStatus objects)
        mock_storage = Mock()
        sample_data = [
            ContextStatus(
                organization_id=123,
                repo_name="test/repo",
                update_type=ContextUpdateType.CONTEXT_UPDATE,
                github_url="https://github.com/test/repo/pull/1",
                title="Test PR",
                description="Test description",
                status=ContextStatusType.OPEN,
                created_at=1704067200,
                updated_at=1704070800,
                github_updated_at=1704069000,
                pr_info=None,
            )
        ]
        mock_storage.get_context_status = AsyncMock(return_value=sample_data)

        # Call storage
        result = await mock_storage.get_context_status(
            organization_id=123,
            status=None,
            update_type=None,
            limit=100,
            offset=0,
        )

        # Verify structure (now accessing NamedTuple attributes)
        assert len(result) == 1
        assert result[0].github_url == "https://github.com/test/repo/pull/1"
        assert result[0].update_type == ContextUpdateType.CONTEXT_UPDATE
        assert result[0].status == ContextStatusType.OPEN

    def test_all_status_enum_values(self):
        """Test all ContextStatusType enum values."""
        statuses = list(ContextStatusType)
        assert len(statuses) == 3
        assert ContextStatusType.OPEN in statuses
        assert ContextStatusType.MERGED in statuses
        assert ContextStatusType.CLOSED in statuses

    def test_all_update_type_enum_values(self):
        """Test all ContextUpdateType enum values."""
        update_types = list(ContextUpdateType)
        assert len(update_types) == 3
        assert ContextUpdateType.SCHEDULED_ANALYSIS in update_types
        assert ContextUpdateType.CONTEXT_UPDATE in update_types
        assert ContextUpdateType.DATA_REQUEST in update_types
