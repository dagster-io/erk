"""Tests for GitHub integration in onboarding flow."""

from unittest.mock import MagicMock, patch

import pytest

from csbot.slackbot.webapp.onboarding_steps import create_contextstore_repository


class TestGitHubIntegration:
    """Test GitHub repository creation functionality."""

    @pytest.mark.asyncio
    async def test_create_contextstore_repository_success(self):
        """Test successful contextstore repository creation."""
        mock_logger = MagicMock()
        mock_repo = MagicMock()
        mock_repo.html_url = "https://github.com/org/test-context"
        mock_repo.github_config.repo_name = "test-context"

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_repository") as mock_create,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.initialize_contextstore_repository"
            ) as mock_init,
            patch(
                "csbot.slackbot.channel_bot.personalization.get_company_info_from_domain"
            ) as mock_get_company_info,
        ):
            mock_init.return_value = mock_repo
            mock_get_company_info.return_value = None

            auth_source = MagicMock()

            mock_agent = MagicMock()
            result = await create_contextstore_repository(
                mock_logger, mock_agent, auth_source, "test-team", "user@example.com"
            )

            assert result["success"] is True
            assert result["repo_url"] == "https://github.com/org/test-context"
            assert result["repo_name"] == "test-context"

            mock_create.assert_called_once_with(auth_source, "test-team-context")
            mock_init.assert_called_once_with(
                auth_source, "test-team-context", "test-team/compass", "dagster-compass", None
            )

    @pytest.mark.asyncio
    async def test_create_contextstore_repository_creation_failure(self):
        """Test repository creation failure."""
        mock_logger = MagicMock()
        auth_source = MagicMock()

        with patch("csbot.slackbot.webapp.onboarding_steps.create_repository") as mock_create:
            mock_create.side_effect = Exception("Repository creation failed")

            result = await create_contextstore_repository(
                mock_logger, MagicMock(), auth_source, "test-team", "user@example.com"
            )

            assert result["success"] is False
            assert "Repository creation failed" in result["error"]
