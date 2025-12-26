"""Tests for onboarding failure scenarios at each step.

This test suite exercises the idempotent onboarding handler's error handling
and recovery behavior when failures occur at different steps in the flow.
"""

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.test_utils import make_mocked_request

from csbot.slackbot.storage.onboarding_state import OnboardingState, OnboardingStep
from csbot.slackbot.webapp.onboarding import create_onboarding_process_api_handler


@pytest.fixture
def mock_request():
    """Create a mock POST request with valid JSON data."""
    request = make_mocked_request("POST", "/api/onboarding/process")
    request.json = AsyncMock(
        return_value={
            "token": "valid_token",
            "email": "test@example.com",
            "organization": "Test Organization",
        }
    )
    return request


class TestOnboardingStepFailures:
    """Test failure scenarios at each step of the onboarding process."""

    @pytest.mark.asyncio
    async def test_failure_at_slack_team_creation(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when creating Slack team (Step 1)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team:
            # Simulate Slack team creation failure
            mock_create_team.return_value = {"success": False, "error": "domain_taken"}

            response = await handler(mock_request)

            # Should return error response
            assert response.status == 400
            assert (
                isinstance(response.body, bytes) and b"Slack domain already taken" in response.body
            )

            # Verify state was updated with error
            assert complete_mock_bot_server.bot_manager.storage.update_onboarding_state.called

            # Verify token was not consumed on failure
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_at_channel_setup(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when setting up channels (Step 2)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("asyncio.sleep"),
        ):
            # Step 1 succeeds
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}

            # Step 2 fails - channel creation fails
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {
                "success": False,
                "error": "name_taken",
            }

            response = await handler(mock_request)

            # Should return error response
            assert response.status == 400

            # Verify we got past step 1
            mock_create_team.assert_called_once()

            # Verify token was not consumed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_at_compass_channels_setup(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when setting up Compass bot channels (Step 3)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch("csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"),
            patch("asyncio.sleep"),
        ):
            # Steps 1-2 succeed
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}

            # Step 3 fails - can't get bot user ID
            mock_get_bot_id.return_value = {
                "success": False,
                "error": "bot_not_found",
            }

            response = await handler(mock_request)

            # Should return error response
            assert response.status == 400

            # Verify error was saved to state
            assert complete_mock_bot_server.bot_manager.storage.update_onboarding_state.called

            # Verify token was not consumed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_at_contextstore_creation(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when creating contextstore repository (Step 4)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch("asyncio.sleep"),
            patch("csbot.agents.factory.create_agent_from_config"),
        ):
            # Steps 1-3 succeed
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}

            # Step 4 fails - contextstore creation fails
            mock_create_repo.return_value = {
                "success": False,
                "error": "Repository creation failed",
            }

            response = await handler(mock_request)

            # Should return error response
            assert response.status == 400

            # Verify we got through steps 1-3
            mock_create_team.assert_called_once()
            mock_get_bot_id.assert_called()

            # Verify we attempted step 4
            mock_create_repo.assert_called_once()

            # Verify token was not consumed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_at_billing_setup(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when setting up billing (Step 5)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )

        # Remove Stripe client to simulate billing setup failure
        complete_mock_bot_server.stripe_client = None

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch("asyncio.sleep"),
            patch("csbot.agents.factory.create_agent_from_config"),
        ):
            # Steps 1-4 succeed
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}
            mock_create_repo.return_value = {
                "success": True,
                "repo_url": "https://github.com/org/test-context",
                "repo_name": "test-organization-context",
            }

            # Step 5 fails - no Stripe client
            response = await handler(mock_request)

            # Should return error response
            assert response.status == 500

            # Verify we got through steps 1-4
            mock_create_team.assert_called_once()
            mock_create_repo.assert_called_once()

            # Verify token was not consumed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_at_organization_creation(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when creating organization (Step 6)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )

        # Make organization creation fail
        complete_mock_bot_server.bot_manager.storage.create_organization.side_effect = Exception(
            "Database error"
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch("asyncio.sleep"),
            patch("csbot.agents.factory.create_agent_from_config"),
        ):
            # Steps 1-5 succeed
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}
            mock_create_repo.return_value = {
                "success": True,
                "repo_url": "https://github.com/org/test-context",
                "repo_name": "test-organization-context",
            }

            # Step 6 fails - organization creation raises exception
            response = await handler(mock_request)

            # Should return error response
            assert response.status == 500

            # Verify we got through steps 1-5
            mock_create_team.assert_called_once()
            mock_create_repo.assert_called_once()

            # Verify we attempted organization creation
            complete_mock_bot_server.bot_manager.storage.create_organization.assert_called_once()

            # Verify token was not consumed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.skip(reason="Bot instance creation not part of minimal onboarding flow")
    @pytest.mark.asyncio
    async def test_failure_at_bot_instance_creation(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when creating bot instance (Step 7)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )
        complete_mock_bot_server.bot_manager.storage.create_organization.return_value = 123

        # Make bot instance creation fail
        complete_mock_bot_server.bot_manager.storage.create_bot_instance.side_effect = Exception(
            "Bot instance creation failed"
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch("asyncio.sleep"),
            patch("csbot.agents.factory.create_agent_from_config"),
        ):
            # Steps 1-6 succeed
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}
            mock_create_repo.return_value = {
                "success": True,
                "repo_url": "https://github.com/org/test-context",
                "repo_name": "test-organization-context",
            }

            # Step 7 fails - bot instance creation raises exception
            response = await handler(mock_request)

            # Should return error response
            assert response.status == 500

            # Verify we got through steps 1-6
            mock_create_team.assert_called_once()
            complete_mock_bot_server.bot_manager.storage.create_organization.assert_called_once()

            # Verify we attempted bot instance creation
            complete_mock_bot_server.bot_manager.storage.create_bot_instance.assert_called_once()

            # Verify token was not consumed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.skip(reason="Slack Connect not part of minimal onboarding flow")
    @pytest.mark.asyncio
    async def test_failure_at_slack_connect(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test failure when creating Slack Connect channel (Step 8)."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )
        complete_mock_bot_server.bot_manager.storage.create_organization.return_value = 123
        complete_mock_bot_server.bot_manager.storage.create_bot_instance.return_value = 456

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_slack_connect_channel"
            ) as mock_create_connect,
            patch("asyncio.sleep"),
            patch("csbot.agents.factory.create_agent_from_config"),
        ):
            # Steps 1-7 succeed
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}
            mock_create_repo.return_value = {
                "success": True,
                "repo_url": "https://github.com/org/test-context",
                "repo_name": "test-organization-context",
            }

            # Step 8 fails - Slack Connect creation fails
            mock_create_connect.return_value = {
                "success": False,
                "error": "external_org_migration_required",
            }

            response = await handler(mock_request)

            # Should return error response
            assert response.status == 400

            # Verify we got through steps 1-7
            mock_create_team.assert_called_once()
            complete_mock_bot_server.bot_manager.storage.create_bot_instance.assert_called_once()

            # Verify we attempted Slack Connect creation
            mock_create_connect.assert_called_once()

            # Token was consumed during bot instance creation (Step 8), even though Slack Connect (Step 9) failed
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_called_once_with(
                "valid_token", 456
            )


class TestOnboardingIdempotency:
    """Test idempotent behavior when retrying after failures."""

    @pytest.mark.skip(reason="Test uses steps not in minimal onboarding flow")
    @pytest.mark.asyncio
    async def test_resume_after_step_3_failure(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test that onboarding can resume from step 3 after a previous failure."""
        # Setup: Previous onboarding failed at step 3 (bot ID retrieval)
        # Mark all steps up to and including governance channel creation as completed
        existing_state = OnboardingState(
            id=1,
            email="test@example.com",
            organization_name="Test Organization",
            current_step=OnboardingStep.GOVERNANCE_CHANNEL_CREATED,
            completed_steps=[
                OnboardingStep.INITIALIZED,
                OnboardingStep.SLACK_TEAM_CREATED,
                OnboardingStep.CHANNELS_LISTED,
                OnboardingStep.ADMINS_INVITED,
                OnboardingStep.COMPASS_CHANNEL_CREATED,
                OnboardingStep.GOVERNANCE_CHANNEL_CREATED,
            ],
            slack_team_id="T12345",
            team_domain="test-organization-dgc",
            team_name="test-organization",
            general_channel_id="C11111",
            compass_channel_id="C33333",
            compass_channel_name="compass",
            governance_channel_id="C44444",
            governance_channel_name="governance",
            error_message="Bot user ID retrieval failed",
            created_at=None,
            updated_at=None,
            completed_at=None,
            processing_started_at=None,
        )

        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )
        complete_mock_bot_server.bot_manager.storage.get_onboarding_state.return_value = (
            existing_state
        )
        complete_mock_bot_server.bot_manager.storage.create_organization.return_value = 123
        complete_mock_bot_server.bot_manager.storage.create_bot_instance.return_value = 456

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_slack_connect_channel"
            ) as mock_create_connect,
            patch("asyncio.sleep"),
            patch("csbot.agents.factory.create_agent_from_config"),
        ):
            # Steps 3-8 succeed on retry
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}
            mock_create_repo.return_value = {
                "success": True,
                "repo_url": "https://github.com/org/test-context",
                "repo_name": "test-organization-context",
            }
            mock_create_connect.return_value = {"success": True, "invite_id": "I12345"}

            response = await handler(mock_request)

            # Should succeed
            assert response.status == 200

            # Verify steps 1-2 were skipped (not called)
            mock_create_team.assert_not_called()
            mock_get_channels.assert_not_called()
            mock_create_channel.assert_not_called()

            # Verify we resumed from step 3
            mock_get_bot_id.assert_called()
            mock_create_repo.assert_called_once()

            # Verify token was consumed on success
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_called_once_with(
                "valid_token", 456
            )

    @pytest.mark.skip(reason="Test expects full onboarding completion, not minimal")
    @pytest.mark.asyncio
    async def test_already_completed_onboarding(
        self, complete_mock_bot_server, valid_token_status, mock_request
    ):
        """Test that handler returns early if onboarding is already completed."""
        # Setup: Onboarding already completed
        completed_state = OnboardingState(
            id=1,
            email="test@example.com",
            organization_name="Test Organization",
            current_step=OnboardingStep.COMPLETED,
            slack_team_id="T12345",
            compass_channel_id="C33333",
            governance_channel_id="C44444",
            compass_bot_user_id="U12345",
            contextstore_repo_name="test-organization-context",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
            organization_id=123,
            compass_bot_instance_id=456,
            created_at=None,
            updated_at=None,
            completed_at=None,
            processing_started_at=None,
        )

        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            valid_token_status
        )
        complete_mock_bot_server.bot_manager.storage.get_onboarding_state.return_value = (
            completed_state
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
        ):
            response = await handler(mock_request)

            # Should succeed immediately
            assert response.status == 200

            # Verify no steps were executed
            mock_create_team.assert_not_called()
            mock_get_bot_id.assert_not_called()
            mock_create_repo.assert_not_called()

            # Token was already consumed when onboarding completed the first time
            # It should not be consumed again on subsequent calls
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()
