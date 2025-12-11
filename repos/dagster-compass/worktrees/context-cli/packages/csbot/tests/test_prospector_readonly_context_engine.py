"""Tests for ProspectorReadOnlyContextEngine blocking write operations."""

from unittest.mock import Mock

import pytest

from csbot.contextengine.read_only import ProspectorReadOnlyContextEngine
from tests.factories import context_store_builder
from tests.fakes.context_store_manager import FakeContextStoreManager


class TestProspectorReadOnlyContextEngine:
    """Test that ProspectorReadOnlyContextEngine blocks write operations."""

    def setup_method(self):
        """Set up test fixtures using ContextStore."""
        # Create a simple ContextStore for testing
        self.context_store = context_store_builder().with_project("test/project").build()
        self.fake_provider = FakeContextStoreManager(self.context_store)

        # Create a mock agent
        self.mock_agent = Mock()

    def test_supports_add_context_returns_false(self):
        """Test that supports_add_context returns False for read-only context stores."""
        engine = ProspectorReadOnlyContextEngine(
            self.fake_provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp="Test ICP",
        )

        assert engine.supports_add_context() is False

    def test_supports_cron_jobs_returns_false(self):
        """Test that supports_cron_jobs returns False for read-only context stores."""
        engine = ProspectorReadOnlyContextEngine(
            self.fake_provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp="Test ICP",
        )

        assert engine.supports_cron_jobs() is False

    @pytest.mark.asyncio
    async def test_add_context_raises_error(self):
        """Test that add_context raises RuntimeError for prospector bot instances."""
        engine = ProspectorReadOnlyContextEngine(
            self.fake_provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp="Test ICP",
        )

        with pytest.raises(
            RuntimeError,
            match="Attempted to add context to a prospector bot instance",
        ):
            await engine.add_context(
                topic="Test Topic",
                incorrect_understanding="Wrong understanding",
                correct_understanding="Correct understanding",
                attribution="Test User",
            )

    @pytest.mark.asyncio
    async def test_add_cron_job_raises_error(self):
        """Test that add_cron_job raises RuntimeError for prospector bot instances."""
        engine = ProspectorReadOnlyContextEngine(
            self.fake_provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp="Test ICP",
        )

        with pytest.raises(
            RuntimeError,
            match="Attempted to add cron job to a prospector bot instance",
        ):
            await engine.add_cron_job(
                cron_job_name="test-job",
                cron_string="0 12 * * *",
                question="What's the status?",
                thread="test-thread",
                attribution="Test User",
            )

    @pytest.mark.asyncio
    async def test_update_cron_job_raises_error(self):
        """Test that update_cron_job raises RuntimeError for prospector bot instances."""
        engine = ProspectorReadOnlyContextEngine(
            self.fake_provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp="Test ICP",
        )

        with pytest.raises(
            RuntimeError,
            match="Attempted to update cron job in a prospector bot instance",
        ):
            await engine.update_cron_job(
                cron_job_name="test-job",
                additional_context="Additional context",
                attribution="Test User",
            )

    @pytest.mark.asyncio
    async def test_delete_cron_job_raises_error(self):
        """Test that delete_cron_job raises RuntimeError for prospector bot instances."""
        engine = ProspectorReadOnlyContextEngine(
            self.fake_provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp="Test ICP",
        )

        with pytest.raises(
            RuntimeError,
            match="Attempted to delete cron job from a prospector bot instance",
        ):
            await engine.delete_cron_job(
                cron_job_name="test-job",
                attribution="Test User",
            )

    @pytest.mark.asyncio
    async def test_get_system_prompt_with_icp(self):
        """Test get_system_prompt includes ICP context when provided."""
        # Create ContextStore with system prompt
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .with_system_prompt("Base system prompt content")
            .build()
        )
        provider = FakeContextStoreManager(context_store)

        icp_text = "Looking for senior engineers with Python experience"
        engine = ProspectorReadOnlyContextEngine(
            provider,
            self.mock_agent,
            "test-channel",
            set(),
            icp=icp_text,
        )

        result = await engine.get_system_prompt()

        # Verify both base prompt and ICP are included
        assert result is not None
        assert "Base system prompt content" in result
        assert "CANDIDATE PROFILE INFORMATION" in result
        assert icp_text in result
        assert "ideal candidate profile" in result

    @pytest.mark.asyncio
    async def test_read_operations_still_work(self):
        """Test that read operations don't raise read-only errors for prospector bot instances."""
        # Create ContextStore with a dataset
        context_store = (
            context_store_builder()
            .with_project("test/project", version=2)
            .add_dataset("test_connection", "test_table")
            .with_markdown("# Test Table\nTest content")
            .build()
        )
        provider = FakeContextStoreManager(context_store)

        engine = ProspectorReadOnlyContextEngine(
            provider,
            self.mock_agent,
            "test-channel",
            {"test_connection"},
            icp="Test ICP",
        )

        # Search should work (not raise read-only RuntimeError)
        results = await engine.search_datasets("test query", full=False)
        # Results may be empty but should not error
        assert isinstance(results, list)
