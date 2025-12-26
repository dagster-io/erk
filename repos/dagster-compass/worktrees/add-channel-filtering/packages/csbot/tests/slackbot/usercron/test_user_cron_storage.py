"""Tests for cronjob_manager module."""

import pytest

from csbot.slackbot.usercron import UserCronStorage
from csbot.slackbot.usercron.storage import NO_CHANNEL_SENTINEL
from tests.factories import context_store_builder
from tests.fakes.context_store_manager import FakeContextStoreManager


class TestUserCronStorage:
    """Test UserCronStorage class."""

    def setup_method(self):
        """Set up test fixtures using ContextStore."""
        # Create initial ContextStore with test project
        initial_context_store = (
            context_store_builder()
            .with_project("test/project")
            .with_project_teams({"team1": ["user1"], "team2": ["user2"]})
            .build()
        )

        # Create fake provider and mutator
        self.fake_provider = FakeContextStoreManager(initial_context_store)

        # Create UserCronStorage with fakes
        self.cron_manager = UserCronStorage(
            self.fake_provider,
            None,
        )

    @pytest.mark.asyncio
    async def test_get_cron_jobs_empty(self):
        """Test get_cron_jobs with no cron jobs."""
        result = await self.cron_manager.get_cron_jobs()
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_cron_jobs_with_jobs(self):
        """Test get_cron_jobs with existing cron jobs."""
        # Update the fake provider with a ContextStore containing cronjobs
        context_store_with_jobs = (
            context_store_builder()
            .with_project("test/project")
            .add_general_cronjob("job1")
            .with_cron("0 9 * * *")
            .with_question("Test question")
            .with_thread("test-thread")
            .add_general_cronjob("job2")
            .with_cron("0 17 * * *")
            .with_question("Another question")
            .with_thread("another-thread")
            .build()
        )
        self.fake_provider.update_context_store(context_store_with_jobs)

        result = await self.cron_manager.get_cron_jobs()

        assert len(result) == 2
        assert "<general>/job1" in result
        assert "<general>/job2" in result
        assert result["<general>/job1"].cron == "0 9 * * *"
        assert result["<general>/job2"].question == "Another question"

    @pytest.mark.asyncio
    async def test_add_cron_job(self):
        """Test adding a cron job."""
        result = await self.cron_manager.add_cron_job(
            cron_job_name="test-job",
            cron_string="0 9 * * *",
            question="Test question",
            thread="test-thread",
            attribution=None,
        )

        assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_add_cron_job_with_attribution(self):
        """Test adding a cron job with attribution."""
        result = await self.cron_manager.add_cron_job(
            cron_job_name="test-job",
            cron_string="0 9 * * *",
            question="Test question",
            thread="test-thread",
            attribution="Created by test user",
        )

        assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_add_cron_job_invalid_cron(self):
        """Test adding a cron job with invalid cron string."""
        with pytest.raises(Exception):  # croniter will raise specific exception
            await self.cron_manager.add_cron_job(
                cron_job_name="test-job",
                cron_string="invalid cron",
                question="Test question",
                thread="test-thread",
                attribution=None,
            )

    @pytest.mark.asyncio
    async def test_update_cron_job(self):
        """Test updating a cron job."""
        # First add a cron job
        await self.cron_manager.add_cron_job(
            cron_job_name="test-job",
            cron_string="0 9 * * *",
            question="Test question",
            thread="test-thread",
            attribution=None,
        )

        # Now update it
        result = await self.cron_manager.update_cron_job(
            cron_job_name=f"{NO_CHANNEL_SENTINEL}/test-job",
            additional_context="Additional context for testing",
            attribution=None,
        )

        assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_update_cron_job_with_attribution(self):
        """Test updating a cron job with attribution."""
        # First add a cron job
        await self.cron_manager.add_cron_job(
            cron_job_name="test-job",
            cron_string="0 9 * * *",
            question="Test question",
            thread="test-thread",
            attribution=None,
        )

        # Now update it with attribution
        result = await self.cron_manager.update_cron_job(
            cron_job_name=f"{NO_CHANNEL_SENTINEL}/test-job",
            additional_context="Additional context for testing",
            attribution="Updated by test user",
        )

        assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_update_cron_job_not_found(self):
        """Test updating a non-existent cron job."""
        with pytest.raises(
            ValueError, match=f"Scheduled analysis '{NO_CHANNEL_SENTINEL}/nonexistent' not found"
        ):
            await self.cron_manager.update_cron_job(
                cron_job_name=f"{NO_CHANNEL_SENTINEL}/nonexistent",
                additional_context="Additional context",
                attribution=None,
            )

    @pytest.mark.asyncio
    async def test_delete_cron_job(self):
        """Test deleting a cron job."""
        # First add a cron job
        await self.cron_manager.add_cron_job(
            cron_job_name="test-job",
            cron_string="0 9 * * *",
            question="Test question",
            thread="test-thread",
            attribution=None,
        )

        # Now delete it
        result = await self.cron_manager.delete_cron_job(
            cron_job_name=f"{NO_CHANNEL_SENTINEL}/test-job",
            attribution=None,
        )

        assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_delete_cron_job_with_attribution(self):
        """Test deleting a cron job with attribution."""
        # First add a cron job
        await self.cron_manager.add_cron_job(
            cron_job_name="test-job",
            cron_string="0 9 * * *",
            question="Test question",
            thread="test-thread",
            attribution=None,
        )

        # Now delete it with attribution
        result = await self.cron_manager.delete_cron_job(
            cron_job_name=f"{NO_CHANNEL_SENTINEL}/test-job",
            attribution="Deleted by test user",
        )

        assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_delete_cron_job_not_found(self):
        """Test deleting a non-existent cron job."""
        with pytest.raises(
            ValueError, match=f"Scheduled analysis '{NO_CHANNEL_SENTINEL}/nonexistent' not found"
        ):
            await self.cron_manager.delete_cron_job(
                cron_job_name=f"{NO_CHANNEL_SENTINEL}/nonexistent",
                attribution=None,
            )

    @pytest.mark.asyncio
    async def test_cron_job_workflow(self):
        """Test complete workflow: add -> update -> delete cron job."""
        cron_job_name = "workflow-test"

        # Add a cron job
        add_result = await self.cron_manager.add_cron_job(
            cron_job_name=cron_job_name,
            cron_string="0 9 * * *",
            question="Initial question",
            thread="test-thread",
            attribution="Test workflow",
        )
        assert add_result.cron_job_review_url == "https://github.com/test/repo/pull/123"

        # Verify it exists
        jobs = await self.cron_manager.get_cron_jobs()
        full_cron_job_name = f"{NO_CHANNEL_SENTINEL}/{cron_job_name}"
        assert full_cron_job_name in jobs
        assert jobs[full_cron_job_name].question == "Initial question"

        # Update the cron job
        update_result = await self.cron_manager.update_cron_job(
            cron_job_name=full_cron_job_name,
            additional_context="Updated context",
            attribution="Test workflow update",
        )
        assert update_result.cron_job_review_url == "https://github.com/test/repo/pull/123"

        # Verify the update
        jobs = await self.cron_manager.get_cron_jobs()
        assert "Additional context: Updated context" in jobs[full_cron_job_name].question

        # Delete the cron job
        delete_result = await self.cron_manager.delete_cron_job(
            cron_job_name=full_cron_job_name,
            attribution="Test workflow cleanup",
        )
        assert delete_result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_multiple_cron_jobs(self):
        """Test managing multiple cron jobs simultaneously."""
        jobs_data = [
            ("morning-job", "0 9 * * *", "Morning check", "morning-thread"),
            ("evening-job", "0 17 * * *", "Evening check", "evening-thread"),
            ("weekly-job", "0 9 * * 1", "Weekly report", "weekly-thread"),
        ]

        # Add multiple jobs
        for job_name, cron_string, question, thread in jobs_data:
            result = await self.cron_manager.add_cron_job(
                cron_job_name=job_name,
                cron_string=cron_string,
                question=question,
                thread=thread,
                attribution=None,
            )
            assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

        # Verify all jobs exist
        jobs = await self.cron_manager.get_cron_jobs()
        assert len(jobs) == 3

        for job_name, cron_string, question, thread in jobs_data:
            full_job_name = f"{NO_CHANNEL_SENTINEL}/{job_name}"
            assert full_job_name in jobs
            assert jobs[full_job_name].cron == cron_string
            assert jobs[full_job_name].question == question
            assert jobs[full_job_name].thread == thread

        # Update one job
        await self.cron_manager.update_cron_job(
            cron_job_name=f"{NO_CHANNEL_SENTINEL}/morning-job",
            additional_context="Updated morning job",
            attribution=None,
        )

        # Delete one job
        await self.cron_manager.delete_cron_job(
            cron_job_name=f"{NO_CHANNEL_SENTINEL}/weekly-job",
            attribution=None,
        )

        # Verify final state
        jobs = await self.cron_manager.get_cron_jobs()
        assert len(jobs) == 2
        assert f"{NO_CHANNEL_SENTINEL}/morning-job" in jobs
        assert f"{NO_CHANNEL_SENTINEL}/evening-job" in jobs
        assert f"{NO_CHANNEL_SENTINEL}/weekly-job" not in jobs
        assert "Updated morning job" in jobs[f"{NO_CHANNEL_SENTINEL}/morning-job"].question

    @pytest.mark.asyncio
    async def test_cron_jobs_for_channel(self):
        context_store = (
            context_store_builder()
            .add_general_cronjob(
                "general-cron-job", "* * * * *", "general question", "general-thread"
            )
            .new_channel("my-channel")
            .add_channel_cronjob("my-cron-job", "* * * * *", "channel question", "thread")
            .build()
        )
        provider = FakeContextStoreManager(context_store)
        storage = UserCronStorage(provider, "my-channel")
        crons = {cron_job.question for cron_job in (await storage.get_cron_jobs()).values()}
        assert crons == {"general question", "channel question"}

        storage = UserCronStorage(provider, "my-other-channel")
        crons = {cron_job.question for cron_job in (await storage.get_cron_jobs()).values()}
        assert crons == {"general question"}


class TestCronJobValidation:
    """Test cron job validation functionality."""

    def setup_method(self):
        """Set up test fixtures using ContextStore."""
        # Create initial ContextStore
        initial_context_store = context_store_builder().with_project("test/project").build()

        # Create fake provider and mutator
        self.fake_provider = FakeContextStoreManager(initial_context_store)

        # Create UserCronStorage with fakes
        self.cron_manager = UserCronStorage(
            self.fake_provider,
            None,
        )

    @pytest.mark.asyncio
    async def test_valid_cron_strings(self):
        """Test various valid cron string formats."""
        valid_cron_strings = [
            "0 9 * * *",  # Daily at 9 AM
            "*/15 * * * *",  # Every 15 minutes
            "0 */2 * * *",  # Every 2 hours
            "0 9 * * 1-5",  # Weekdays at 9 AM
            "30 2 1 * *",  # First day of month at 2:30 AM
            "0 0 * * 0",  # Every Sunday at midnight
        ]

        for i, cron_string in enumerate(valid_cron_strings):
            result = await self.cron_manager.add_cron_job(
                cron_job_name=f"valid-job-{i}",
                cron_string=cron_string,
                question=f"Test question {i}",
                thread=f"test-thread-{i}",
                attribution=None,
            )
            assert result.cron_job_review_url == "https://github.com/test/repo/pull/123"

    @pytest.mark.asyncio
    async def test_invalid_cron_strings(self):
        """Test various invalid cron string formats."""
        invalid_cron_strings = [
            "invalid",
            "60 9 * * *",  # Invalid minute
            "0 25 * * *",  # Invalid hour
            "0 9 32 * *",  # Invalid day
            "0 9 * 13 *",  # Invalid month
            "0 9 * * 8",  # Invalid weekday
            "",  # Empty string
            "* * * *",  # Missing field
        ]

        for i, cron_string in enumerate(invalid_cron_strings):
            with pytest.raises(Exception):  # croniter will raise specific exceptions
                await self.cron_manager.add_cron_job(
                    cron_job_name=f"invalid-job-{i}",
                    cron_string=cron_string,
                    question=f"Test question {i}",
                    thread=f"test-thread-{i}",
                    attribution=None,
                )

    # Test with normalized channel name
    @pytest.mark.asyncio
    async def test_normalized_channel_name(self):
        """Test with normalized channel name."""
        # Create ContextStore with global and channel-specific cronjobs
        context_store = (
            context_store_builder()
            .with_project("test/project")
            .add_general_cronjob("test-job")
            .with_cron("0 9 * * *")
            .with_question("Question global")
            .with_thread("test-thread")
            .new_channel("test-channel")
            .add_channel_cronjob("test-job")
            .with_cron("0 9 * * *")
            .with_question("Question test-channel")
            .with_thread("test-thread")
            .new_channel("test-channel2")
            .add_channel_cronjob("test-job")
            .with_cron("0 9 * * *")
            .with_question("Question test-channel2")
            .with_thread("test-thread")
            .build()
        )

        async def run_test(
            channel_name: str | None, expected_job_name: str, expected_question: str
        ):
            provider = FakeContextStoreManager(context_store)
            cron_manager = UserCronStorage(
                provider,
                channel_name,
            )
            result = await cron_manager.get_cron_jobs()
            assert expected_job_name in result
            assert result[expected_job_name].question == expected_question

        await run_test(None, "<general>/test-job", "Question global")
        await run_test("test-channel", "test-channel/test-job", "Question test-channel")
        await run_test("test-channel2", "test-channel2/test-job", "Question test-channel2")
