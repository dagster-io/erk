from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from csbot.local_context_store.github.api import (
    IssueClosedEvent,
    IssueOpenedEvent,
    PrClosedEvent,
    PrCreatedEvent,
    PrMergedEvent,
)
from csbot.local_context_store.github.config import GithubConfig
from csbot.slackbot.slackbot_github_monitor import (
    GithubMonitor,
    PrInfo,
    SlackbotGithubMonitor,
)
from csbot.slackbot.storage.interface import (
    CRONJOB_PR_TITLE_PREFIX,
    ContextStatusType,
    ContextUpdateType,
)


@pytest.fixture
def mock_github():
    """Create a mock GitHub instance."""
    mock_github = MagicMock()
    mock_repo = MagicMock()
    mock_pr = MagicMock()

    mock_github.get_repo.return_value = mock_repo
    mock_repo.get_pull.return_value = mock_pr
    mock_pr.head.ref = "feature-branch"

    return mock_github, mock_repo, mock_pr


@pytest.fixture
def github_monitor(mock_github):
    """Create a GithubMonitor instance with mocked GitHub."""
    github_instance, mock_repo, mock_pr = mock_github
    monitor = GithubMonitor(
        github_config=GithubConfig.pat(
            token="fake-token",
            repo_name="test/repo",
        ),
    )
    return monitor, mock_repo, mock_pr, github_instance


@pytest.fixture
def mock_slack_client():
    """Create a mock Slack client."""
    client = AsyncMock()
    client.chat_postMessage.return_value = {"ok": True, "ts": "123.456"}
    client.chat_update.return_value = {"ok": True}
    return client


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = AsyncMock()
    return client


@pytest.fixture
def slackbot_github_monitor(github_monitor, mock_slack_client, mock_anthropic_client):
    """Create a SlackbotGithubMonitor instance."""
    monitor, mock_repo, mock_pr, mock_github = github_monitor
    kv_store = MagicMock()
    logger = structlog.get_logger(__name__)

    slackbot_monitor = SlackbotGithubMonitor(
        channel_name="test-channel",
        github_monitor=monitor,
        kv_store=kv_store,
        client=mock_slack_client,
        logger=logger,
        agent=mock_anthropic_client,
    )

    return slackbot_monitor, monitor, mock_repo, mock_pr


class TestGithubMonitorFileReconciler:
    """Test the file reconciler functionality."""

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_create_new_file(self, mock_get_github_client, github_monitor):
        """Test creating a new file in a PR."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor

        # Set up the mock to return our mocked GitHub instance
        mock_get_github_client.return_value = mock_github

        # Mock file doesn't exist (exception on get_contents)
        mock_repo.get_contents.side_effect = Exception("File not found")

        file_updates = {"new_file.py": "print('hello world')"}

        result = await monitor.update_pr_files(
            "https://github.com/test/repo/pull/123", file_updates, "Test commit"
        )

        assert result is True
        mock_repo.create_file.assert_called_once_with(
            path="new_file.py",
            message="Test commit - Create new_file.py",
            content="print('hello world')",
            branch="feature-branch",
        )

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_update_existing_file(
        self, mock_get_github_client, github_monitor
    ):
        """Test updating an existing file in a PR."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github

        # Mock existing file
        mock_contents = MagicMock()
        mock_contents.decoded_content.decode.return_value = "old content"
        mock_contents.sha = "old_sha"
        mock_repo.get_contents.return_value = mock_contents

        file_updates = {"existing_file.py": "new content"}

        result = await monitor.update_pr_files(
            "https://github.com/test/repo/pull/123", file_updates, "Test commit"
        )

        assert result is True
        # Should be called twice - once for initial check, once for concurrent check
        assert mock_repo.get_contents.call_count == 2
        mock_repo.update_file.assert_called_once_with(
            path="existing_file.py",
            message="Test commit - Update existing_file.py",
            content="new content",
            sha="old_sha",
            branch="feature-branch",
        )

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_delete_file(self, mock_get_github_client, github_monitor):
        """Test deleting a file from a PR."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github

        # Mock existing file
        mock_contents = MagicMock()
        mock_contents.decoded_content.decode.return_value = "file content"
        mock_contents.sha = "file_sha"
        mock_repo.get_contents.return_value = mock_contents

        file_updates = {"file_to_delete.py": None}

        result = await monitor.update_pr_files(
            "https://github.com/test/repo/pull/123", file_updates, "Test commit"
        )

        assert result is True
        # Should be called twice - once for initial check, once for concurrent check
        assert mock_repo.get_contents.call_count == 2
        mock_repo.delete_file.assert_called_once_with(
            path="file_to_delete.py",
            message="Test commit - Delete file_to_delete.py",
            sha="file_sha",
            branch="feature-branch",
        )

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_no_changes_needed(self, mock_get_github_client, github_monitor):
        """Test when files are already up to date."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github

        # Mock existing file with same content
        mock_contents = MagicMock()
        mock_contents.decoded_content.decode.return_value = "same content"
        mock_contents.sha = "file_sha"
        mock_repo.get_contents.return_value = mock_contents

        file_updates = {"unchanged_file.py": "same content"}

        result = await monitor.update_pr_files(
            "https://github.com/test/repo/pull/123", file_updates, "Test commit"
        )

        assert result is True
        mock_repo.get_contents.assert_called_once()
        mock_repo.update_file.assert_not_called()
        mock_repo.create_file.assert_not_called()
        mock_repo.delete_file.assert_not_called()

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_concurrent_modification(
        self, mock_get_github_client, github_monitor
    ):
        """Test handling concurrent file modifications."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github

        # Mock file that gets modified between reads
        mock_contents_initial = MagicMock()
        mock_contents_initial.decoded_content.decode.return_value = "old content"
        mock_contents_initial.sha = "old_sha"

        mock_contents_changed = MagicMock()
        mock_contents_changed.sha = "new_sha"  # Different SHA indicates concurrent change

        # First call returns initial state, second call shows it changed
        mock_repo.get_contents.side_effect = [mock_contents_initial, mock_contents_changed]

        file_updates = {"concurrent_file.py": "new content"}

        result = await monitor.update_pr_files(
            "https://github.com/test/repo/pull/123", file_updates, "Test commit"
        )

        # Should return False because no operations were completed
        assert result is False
        mock_repo.update_file.assert_not_called()

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_mixed_operations(self, mock_get_github_client, github_monitor):
        """Test mixed create, update, and delete operations."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github

        # Mock different scenarios for different files
        def mock_get_contents_side_effect(path, ref=None):  # noqa: ARG001
            if path == "create_me.py":
                raise Exception("File not found")
            elif path == "update_me.py":
                mock_contents = MagicMock()
                mock_contents.decoded_content.decode.return_value = "old content"
                mock_contents.sha = "update_sha"
                return mock_contents
            elif path == "delete_me.py":
                mock_contents = MagicMock()
                mock_contents.decoded_content.decode.return_value = "delete content"
                mock_contents.sha = "delete_sha"
                return mock_contents

        mock_repo.get_contents.side_effect = mock_get_contents_side_effect

        file_updates = {
            "create_me.py": "new file content",
            "update_me.py": "updated content",
            "delete_me.py": None,
        }

        result = await monitor.update_pr_files(
            "https://github.com/test/repo/pull/123", file_updates, "Mixed operations"
        )

        assert result is True
        mock_repo.create_file.assert_called_once()
        mock_repo.update_file.assert_called_once()
        mock_repo.delete_file.assert_called_once()


class TestGithubMonitorTitleBodyUpdates:
    """Test PR title and body update functionality."""

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_title_and_body_with_attribution(
        self, mock_get_github_client, github_monitor
    ):
        """Test updating PR title and body with user attribution."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github
        mock_pr.body = "Original PR body"

        with patch("csbot.local_context_store.github.api.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-08-06 15:30:45 UTC"

            result = await monitor.update_pr_title_and_body(
                "https://github.com/test/repo/pull/123",
                title="New Title",
                body="New body content",
                user_name="John Doe",
            )

        assert result is True
        mock_pr.edit.assert_called_once_with(
            title="New Title",
            body="**Updated by:** John Doe at 2024-08-06 15:30:45 UTC\n\nNew body content",
        )

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_title_only(self, mock_get_github_client, github_monitor):
        """Test updating only PR title."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github
        mock_pr.body = "Original PR body"

        with patch("csbot.local_context_store.github.api.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-08-06 15:30:45 UTC"

            result = await monitor.update_pr_title_and_body(
                "https://github.com/test/repo/pull/123",
                title="New Title",
                body=None,
                user_name="John Doe",
            )

        assert result is True
        mock_pr.edit.assert_called_once_with(
            title="New Title",
            body="**Updated by:** John Doe at 2024-08-06 15:30:45 UTC\n\nOriginal PR body",
        )

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_body_only(self, mock_get_github_client, github_monitor):
        """Test updating only PR body."""
        monitor, mock_repo, mock_pr, mock_github = github_monitor
        mock_get_github_client.return_value = mock_github
        mock_pr.body = "Original PR body"

        with patch("csbot.local_context_store.github.api.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-08-06 15:30:45 UTC"

            result = await monitor.update_pr_title_and_body(
                "https://github.com/test/repo/pull/123",
                title=None,
                body="New body content",
                user_name="Jane Smith",
            )

        assert result is True
        mock_pr.edit.assert_called_once_with(
            body="**Updated by:** Jane Smith at 2024-08-06 15:30:45 UTC\n\nNew body content"
        )


class TestGithubMonitorPRMethods:
    """Test the PR methods on GithubMonitor."""

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_get_pr_system_prompt_with_details(
        self, mock_get_github_client, slackbot_github_monitor
    ):
        """Test PR system prompt generation with PR details."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock get_pr_details
        monitor.get_pr_details = AsyncMock(
            return_value={
                "title": "Fix bug in authentication",
                "body": "This PR fixes a critical bug in the authentication system.",
                "files": {
                    "auth.py": "def authenticate():\n    pass",
                    "tests.py": "def test_auth():\n    pass",
                },
            }
        )

        prompt = await slackbot_monitor.get_pr_system_prompt(
            "https://github.com/test/repo/pull/123"
        )

        assert "Fix bug in authentication" in prompt
        assert "This PR fixes a critical bug" in prompt
        assert "`auth.py`: 2 lines" in prompt
        assert "`tests.py`: 2 lines" in prompt

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_get_pr_system_prompt_large_pr(
        self, mock_get_github_client, slackbot_github_monitor
    ):
        """Test PR system prompt when PR is too large."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock get_pr_details returning None (too large)
        monitor.get_pr_details = AsyncMock(return_value=None)

        prompt = await slackbot_monitor.get_pr_system_prompt(
            "https://github.com/test/repo/pull/123"
        )

        assert "too large to display full details" in prompt
        assert "help users understand it and answer questions" in prompt

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_get_pr_tools_structure(self, mock_get_github_client, slackbot_github_monitor):
        """Test that PR tools are correctly structured."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        tools = await slackbot_monitor.get_pr_tools(
            "https://github.com/test/repo/pull/123", "John Doe"
        )

        expected_tools = [
            "read_pr_file",
            "list_pr_files",
            "update_pr_file",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools
            assert callable(tools[tool_name])


class TestGithubMonitorPRTools:
    """Test the PR tools functionality on GithubMonitor."""

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_read_pr_file_success(self, mock_get_github_client, slackbot_github_monitor):
        """Test successful reading of PR file."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock get_pr_details
        monitor.get_pr_details = AsyncMock(
            return_value={
                "title": "Test PR",
                "body": "Test body",
                "files": {
                    "main.py": "def main():\n    print('hello')",
                    "test.py": "def test():\n    pass",
                },
            }
        )

        tools = await slackbot_monitor.get_pr_tools(
            "https://github.com/test/repo/pull/123", "John Doe"
        )

        result = await tools["read_pr_file"]("main.py")
        assert result == "def main():\n    print('hello')"

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_read_pr_file_not_found(self, mock_get_github_client, slackbot_github_monitor):
        """Test reading non-existent PR file."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock get_pr_details
        monitor.get_pr_details = AsyncMock(
            return_value={
                "title": "Test PR",
                "body": "Test body",
                "files": {"main.py": "def main():\n    pass"},
            }
        )

        tools = await slackbot_monitor.get_pr_tools(
            "https://github.com/test/repo/pull/123", "John Doe"
        )

        result = await tools["read_pr_file"]("nonexistent.py")
        assert "not found in PR" in result
        assert "main.py" in result

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_list_pr_files(self, mock_get_github_client, slackbot_github_monitor):
        """Test listing PR files."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock get_pr_details
        monitor.get_pr_details = AsyncMock(
            return_value={
                "title": "Test PR",
                "body": "Test body",
                "files": {
                    "main.py": "def main():\n    print('hello')\n    return 0",
                    "test.py": "import unittest",
                },
            }
        )

        tools = await slackbot_monitor.get_pr_tools(
            "https://github.com/test/repo/pull/123", "John Doe"
        )

        result = await tools["list_pr_files"]()
        assert "Files in this PR:" in result
        assert "`main.py` (3 lines)" in result
        assert "`test.py` (1 lines)" in result

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_files_success(self, mock_get_github_client, slackbot_github_monitor):
        """Test successful PR file updates."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock update operations
        monitor.update_pr_files = AsyncMock(return_value=True)
        monitor.update_pr_title_and_body = AsyncMock(return_value=True)
        monitor.comment_on_pr = AsyncMock()
        slackbot_monitor.tick = AsyncMock()

        tools = await slackbot_monitor.get_pr_tools(
            "https://github.com/test/repo/pull/123", "John Doe"
        )

        result = await tools["update_pr_file"](
            "main.py",
            "def main():\n    print('updated')",
            "Update main.py",
            "New PR Title",
            "New PR Description",
        )

        assert "✅ Updated main.py successfully!" in result

        monitor.update_pr_files.assert_called_once_with(
            "https://github.com/test/repo/pull/123",
            {"main.py": "def main():\n    print('updated')"},
            "Update main.py",
        )
        monitor.update_pr_title_and_body.assert_called_once_with(
            "https://github.com/test/repo/pull/123",
            "New PR Title",
            "New PR Description",
            "John Doe",
        )
        monitor.comment_on_pr.assert_called_once_with(
            "https://github.com/test/repo/pull/123",
            "Updated by: John Doe via Slack\n\nCommit: Update main.py",
        )

        monitor.update_pr_files.reset_mock()
        monitor.update_pr_title_and_body.reset_mock()
        monitor.comment_on_pr.reset_mock()

        result2 = await tools["update_pr_file"](
            "old.py", None, "Delete old.py", "Updated PR Title", "Updated PR Description"
        )

        assert "✅ Deleted old.py successfully!" in result2

        monitor.update_pr_files.assert_called_once_with(
            "https://github.com/test/repo/pull/123",
            {"old.py": None},
            "Delete old.py",
        )
        monitor.update_pr_title_and_body.assert_called_once_with(
            "https://github.com/test/repo/pull/123",
            "Updated PR Title",
            "Updated PR Description",
            "John Doe",
        )
        monitor.comment_on_pr.assert_called_once_with(
            "https://github.com/test/repo/pull/123",
            "Updated by: John Doe via Slack\n\nCommit: Delete old.py",
        )

    @pytest.mark.asyncio
    @patch("csbot.local_context_store.github.config.PATGithubAuthSource.get_github_client")
    async def test_update_pr_metadata(self, mock_get_github_client, slackbot_github_monitor):
        """Test PR metadata updates through update_pr_file."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Mock update operations
        monitor.update_pr_files = AsyncMock(return_value=True)
        monitor.update_pr_title_and_body = AsyncMock(return_value=True)
        monitor.comment_on_pr = AsyncMock()
        slackbot_monitor.tick = AsyncMock()

        tools = await slackbot_monitor.get_pr_tools(
            "https://github.com/test/repo/pull/123", "John Doe"
        )

        # Test that PR metadata can be updated through the update_pr_file tool
        result = await tools["update_pr_file"](
            "test.py", "print('test')", "Update test file", "New Title", "New description"
        )

        assert "✅ Updated test.py successfully!" in result
        monitor.update_pr_title_and_body.assert_called_once_with(
            "https://github.com/test/repo/pull/123", "New Title", "New description", "John Doe"
        )


class TestHandleGithubEvent:
    """Test the handle_github_event method that writes to context_status."""

    @pytest.mark.asyncio
    async def test_handle_pr_created_event(self, slackbot_github_monitor):
        """Test handling a PR created event."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance with organization
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 123
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store to capture upsert call
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert

        # Mock get_pr_info
        mock_pr_info = PrInfo(type="context_update_created", bot_id="bot_123")
        slackbot_monitor.get_pr_info = AsyncMock(return_value=mock_pr_info)

        # Create event
        event = PrCreatedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/456",
            pr_title="Add new feature",
            pr_description="This PR adds a new feature",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(event)

        # Verify upsert was called with correct parameters
        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args[1]

        assert call_args["organization_id"] == 123
        assert call_args["repo_name"] == "test/repo"
        assert call_args["update_type"] == ContextUpdateType.CONTEXT_UPDATE
        assert call_args["github_url"] == "https://github.com/test/repo/pull/456"
        assert call_args["title"] == "Add new feature"
        assert call_args["description"] == "This PR adds a new feature"
        assert call_args["status"] == ContextStatusType.OPEN
        assert call_args["created_at"] == int(
            datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC).timestamp()
        )
        assert call_args["pr_info"] == mock_pr_info

    @pytest.mark.asyncio
    async def test_handle_pr_merged_event(self, slackbot_github_monitor):
        """Test handling a PR merged event."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 123
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert
        slackbot_monitor.get_pr_info = AsyncMock(return_value=None)

        # Create event
        event = PrMergedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/789",
            pr_title="Fix critical bug",
            pr_description="Fixes #123",
            timestamp=datetime(2024, 2, 20, 14, 45, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(event)

        # Verify upsert was called with MERGED status
        call_args = mock_upsert.call_args[1]
        assert call_args["status"] == ContextStatusType.MERGED
        assert call_args["update_type"] == ContextUpdateType.CONTEXT_UPDATE
        assert call_args["github_url"] == "https://github.com/test/repo/pull/789"

    @pytest.mark.asyncio
    async def test_handle_pr_closed_event(self, slackbot_github_monitor):
        """Test handling a PR closed event."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 123
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert
        slackbot_monitor.get_pr_info = AsyncMock(return_value=None)

        # Create event
        event = PrClosedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/111",
            pr_title="Abandoned PR",
            pr_description="No longer needed",
            timestamp=datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(event)

        # Verify upsert was called with CLOSED status
        call_args = mock_upsert.call_args[1]
        assert call_args["status"] == ContextStatusType.CLOSED
        assert call_args["update_type"] == ContextUpdateType.CONTEXT_UPDATE
        assert call_args["github_url"] == "https://github.com/test/repo/pull/111"

    @pytest.mark.asyncio
    async def test_handle_issue_opened_event(self, slackbot_github_monitor):
        """Test handling an issue opened event."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 456
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert

        # Create event
        event = IssueOpenedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/issues/42",
            issue_title="Data request: Q1 metrics",
            issue_description="Need quarterly metrics for analysis",
            timestamp=datetime(2024, 4, 5, 11, 20, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(event)

        # Verify upsert was called with DATA_REQUEST type
        call_args = mock_upsert.call_args[1]
        assert call_args["organization_id"] == 456
        assert call_args["update_type"] == ContextUpdateType.DATA_REQUEST
        assert call_args["status"] == ContextStatusType.OPEN
        assert call_args["github_url"] == "https://github.com/test/repo/issues/42"
        assert call_args["title"] == "Data request: Q1 metrics"
        assert call_args["description"] == "Need quarterly metrics for analysis"
        assert call_args["pr_info"] is None

    @pytest.mark.asyncio
    async def test_handle_event_without_bot_instance(self, slackbot_github_monitor):
        """Test handling event when bot_instance is not set."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # No bot instance set
        slackbot_monitor.bot_instance = None

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert

        # Create event
        event = PrCreatedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/1",
            pr_title="Test",
            pr_description="Test",
            timestamp=datetime.now(tz=UTC),
        )

        await slackbot_monitor.handle_github_event(event)

        # Should not call upsert
        mock_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_event_with_pr_info(self, slackbot_github_monitor):
        """Test that pr_info is correctly serialized and stored."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 789
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert

        # Mock get_pr_info to return a PrInfo object
        mock_pr_info = PrInfo(type="scheduled_analysis_created", bot_id="bot_xyz")
        slackbot_monitor.get_pr_info = AsyncMock(return_value=mock_pr_info)

        # Create event
        event = PrCreatedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/999",
            pr_title="Scheduled analysis",
            pr_description="Weekly data analysis",
            timestamp=datetime.now(tz=UTC),
        )

        await slackbot_monitor.handle_github_event(event)

        # Verify pr_info was passed as PrInfo object
        call_args = mock_upsert.call_args[1]
        assert call_args["pr_info"] is not None
        assert isinstance(call_args["pr_info"], PrInfo)
        assert call_args["pr_info"].type == "scheduled_analysis_created"
        assert call_args["pr_info"].bot_id == "bot_xyz"

    @pytest.mark.asyncio
    async def test_handle_event_upsert_behavior(self, slackbot_github_monitor):
        """Test that repeated events for same URL update existing entry."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 100
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert
        slackbot_monitor.get_pr_info = AsyncMock(return_value=None)

        same_url = "https://github.com/test/repo/pull/555"

        # First event - PR created
        event1 = PrCreatedEvent(
            repo_name="test/repo",
            url=same_url,
            pr_title="Initial title",
            pr_description="Initial description",
            timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(event1)

        # Second event - PR merged (same URL, different status)
        event2 = PrMergedEvent(
            repo_name="test/repo",
            url=same_url,
            pr_title="Updated title",
            pr_description="Updated description",
            timestamp=datetime(2024, 1, 2, 15, 0, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(event2)

        # Verify both upserts were called with same github_url
        assert mock_upsert.call_count == 2
        first_call = mock_upsert.call_args_list[0][1]
        second_call = mock_upsert.call_args_list[1][1]

        assert first_call["github_url"] == same_url
        assert second_call["github_url"] == same_url
        assert first_call["status"] == ContextStatusType.OPEN
        assert second_call["status"] == ContextStatusType.MERGED

    @pytest.mark.asyncio
    async def test_handle_cronjob_pr_events(self, slackbot_github_monitor):
        """Test that all cronjob PR events are marked as SCHEDULED_ANALYSIS."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 123
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert
        slackbot_monitor.get_pr_info = AsyncMock(return_value=None)

        # Test created, merged, and closed cronjob PRs
        test_cases = [
            (
                PrCreatedEvent(
                    repo_name="test/repo",
                    url="https://github.com/test/repo/pull/1",
                    pr_title=f"{CRONJOB_PR_TITLE_PREFIX} daily-analysis",
                    pr_description="Automated analysis",
                    timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                ),
                ContextStatusType.OPEN,
            ),
            (
                PrMergedEvent(
                    repo_name="test/repo",
                    url="https://github.com/test/repo/pull/2",
                    pr_title=f"{CRONJOB_PR_TITLE_PREFIX} weekly-report",
                    pr_description="Weekly analysis",
                    timestamp=datetime(2024, 2, 20, 14, 45, 0, tzinfo=UTC),
                ),
                ContextStatusType.MERGED,
            ),
            (
                PrClosedEvent(
                    repo_name="test/repo",
                    url="https://github.com/test/repo/pull/3",
                    pr_title=f"{CRONJOB_PR_TITLE_PREFIX} monthly-summary",
                    pr_description="Cancelled",
                    timestamp=datetime(2024, 3, 10, 9, 0, 0, tzinfo=UTC),
                ),
                ContextStatusType.CLOSED,
            ),
        ]

        for event, expected_status in test_cases:
            await slackbot_monitor.handle_github_event(event)
            call_args = mock_upsert.call_args[1]
            assert call_args["update_type"] == ContextUpdateType.SCHEDULED_ANALYSIS
            assert call_args["status"] == expected_status

    @pytest.mark.asyncio
    async def test_handle_regular_pr_vs_cronjob_pr(self, slackbot_github_monitor):
        """Test that regular PRs and cronjob PRs are distinguished correctly."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 123
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert
        slackbot_monitor.get_pr_info = AsyncMock(return_value=None)

        # Regular PR
        regular_event = PrCreatedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/1",
            pr_title="Add new feature",
            pr_description="Manual feature addition",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(regular_event)
        call_args = mock_upsert.call_args[1]
        assert call_args["update_type"] == ContextUpdateType.CONTEXT_UPDATE

        # Cronjob PR
        cronjob_event = PrCreatedEvent(
            repo_name="test/repo",
            url="https://github.com/test/repo/pull/2",
            pr_title=f"{CRONJOB_PR_TITLE_PREFIX} daily-analysis",
            pr_description="Automated analysis",
            timestamp=datetime(2024, 1, 15, 11, 30, 0, tzinfo=UTC),
        )

        await slackbot_monitor.handle_github_event(cronjob_event)
        call_args = mock_upsert.call_args[1]
        assert call_args["update_type"] == ContextUpdateType.SCHEDULED_ANALYSIS

    @pytest.mark.asyncio
    async def test_handle_issue_events(self, slackbot_github_monitor):
        """Test that issue opened and closed events are handled correctly."""
        slackbot_monitor, monitor, mock_repo, mock_pr = slackbot_github_monitor

        # Set up bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.bot_config.organization_id = 456
        slackbot_monitor.bot_instance = mock_bot_instance

        # Mock kv_store
        mock_upsert = AsyncMock()
        slackbot_monitor.kv_store.upsert_context_status = mock_upsert

        # Test both opened and closed issues
        test_cases = [
            (
                IssueOpenedEvent(
                    repo_name="test/repo",
                    url="https://github.com/test/repo/issues/1",
                    issue_title="Data request: Q1 metrics",
                    issue_description="Need quarterly metrics",
                    timestamp=datetime(2024, 4, 5, 11, 20, 0, tzinfo=UTC),
                ),
                ContextStatusType.OPEN,
            ),
            (
                IssueClosedEvent(
                    repo_name="test/repo",
                    url="https://github.com/test/repo/issues/2",
                    issue_title="Data request completed",
                    issue_description="Request fulfilled",
                    timestamp=datetime(2024, 4, 6, 12, 30, 0, tzinfo=UTC),
                ),
                ContextStatusType.CLOSED,
            ),
        ]

        for event, expected_status in test_cases:
            await slackbot_monitor.handle_github_event(event)
            call_args = mock_upsert.call_args[1]
            assert call_args["organization_id"] == 456
            assert call_args["update_type"] == ContextUpdateType.DATA_REQUEST
            assert call_args["status"] == expected_status
            assert call_args["pr_info"] is None
