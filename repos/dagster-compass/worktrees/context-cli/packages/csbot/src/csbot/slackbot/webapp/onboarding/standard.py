"""Standard onboarding flow handlers."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.slack_utils import generate_urlsafe_team_name
from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.storage.onboarding_context import OnboardingContext
from csbot.slackbot.storage.onboarding_exceptions import (
    BillingSetupError,
    BotInstanceCreationError,
    OnboardingInProgressError,
    OnboardingStepError,
    OrganizationCreationError,
)
from csbot.slackbot.webapp.onboarding.shared import (
    is_valid_email,
)
from csbot.slackbot.webapp.onboarding.utils import is_token_valid
from csbot.slackbot.webapp.onboarding_steps import (
    create_contextstore_repo,
    create_organization_step,
    create_slack_team_step,
    create_stripe_customer_step,
    create_stripe_subscription_step,
    invite_admins_step,
    list_channels_step,
    reconstruct_results_from_state,
    record_tos_step,
    retrieve_bot_ids_step,
)
from csbot.slackbot.webapp.referral.referral import REFERRAL_TOKEN_COOKIE_NAME
from csbot.slackbot.webapp.security import (
    set_onboarding_auth_cookie,
)
from csbot.temporal import constants
from csbot.temporal.client_wrapper import start_workflow_with_search_attributes
from csbot.temporal.org_onboarding_check import OrgOnboardingCheckInput

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


async def create_minimal_onboarding(
    bot_server: "CompassBotServer",
    email: str,
    organization_raw: str,
    token: str | None,
    has_valid_token: bool,
    onboarding_type: str = "standard",
) -> dict:
    """Create minimal setup required to enter connection flow.

    This creates only the essentials:
    - Slack team (for team_id)
    - Stripe customer + subscription
    - Organization in DB

    Skips:
    - Channels (created after first connection)
    - Bot instances (created after first connection)
    - Contextstore (created after first connection)
    - Slack invites (sent after first connection)

    Args:
        bot_server: Bot server instance
        email: User email
        organization_raw: Original organization name
        token: Referral token (optional)
        has_valid_token: Whether the token is valid
        onboarding_type: Type of onboarding flow ("standard" or "prospector")

    Returns:
        Dict with {organization_id, team_id, email}
    """
    organization = generate_urlsafe_team_name(organization_raw)
    analytics_store = SlackbotAnalyticsStore(bot_server.sql_conn_factory)

    async with OnboardingContext(
        analytics_store, bot_server.logger, bot_server.bot_manager.storage, email, organization
    ) as ctx:
        # Validate required configuration
        if not bot_server.config.compass_bot_token:
            bot_server.logger.error("Missing required Slack bot token")
            raise OrganizationCreationError("Account creation failed. Please contact support.")

        if not (
            bot_server.config.slack_admin_token and bot_server.config.compass_dev_tools_bot_token
        ):
            bot_server.logger.error("Admin tokens required for user onboarding functionality")
            raise OrganizationCreationError(
                "Onboarding feature not available in local development mode."
            )

        # Extract tokens
        admin_token = bot_server.config.slack_admin_token.get_secret_value()
        org_bot_token = bot_server.config.compass_dev_tools_bot_token.get_secret_value()
        compass_bot_token = bot_server.config.compass_bot_token.get_secret_value()

        bot_server.logger.info(f"Starting minimal onboarding for organization: {organization}")

        # Check if already completed
        from csbot.slackbot.storage.onboarding_state import OnboardingStep

        if ctx.state.current_step == OnboardingStep.COMPLETED:
            bot_server.logger.info(f"Minimal onboarding already completed for {organization}")
            # Reconstruct results to get organization_id and team_id
            (
                slack_team_result_check,
                _,
                _,
                _,
                _,
                organization_result_check,
            ) = reconstruct_results_from_state(ctx.state, analytics_store)
            return {
                "organization_id": organization_result_check.organization_id
                if organization_result_check
                else 0,
                "team_id": slack_team_result_check.team_id if slack_team_result_check else "",
                "email": email,
            }

        # Check for duplicate request
        if ctx.is_duplicate_request:
            bot_server.logger.warning(f"Minimal onboarding already in progress for {organization}")
            raise OnboardingInProgressError("Onboarding is already in progress")

        # Reconstruct results from state
        (
            slack_team_result,
            channel_setup_result,
            _,
            contextstore_result,
            billing_result,
            organization_result,
        ) = reconstruct_results_from_state(ctx.state, analytics_store)

        # Step 1: Create Slack team
        if not ctx.state.is_step_completed(OnboardingStep.SLACK_TEAM_CREATED):
            bot_server.logger.info("Executing step: Create Slack team")
            slack_team_result = await create_slack_team_step(
                ctx=ctx,
                admin_token=admin_token,
                organization=organization,
                email=email,
                bot_server=bot_server,
            )
            bot_server.logger.info(f"Slack team created: {slack_team_result.team_id}")
            # Wait for Slack to propagate team creation and bot installations
            await asyncio.sleep(3)

        # Step 2: Verify bot installation by listing channels
        if not ctx.state.is_step_completed(OnboardingStep.CHANNELS_LISTED):
            if not slack_team_result:
                raise OnboardingStepError("Slack team result is None")
            bot_server.logger.info("Executing step: List channels (verify bot installation)")
            channel_setup_result = await list_channels_step(
                ctx=ctx,
                org_bot_token=org_bot_token,
                team_id=slack_team_result.team_id,
                organization=organization,
                bot_server=bot_server,
            )
            bot_server.logger.info(
                f"Channels listed, general channel: {channel_setup_result.general_channel_id}"
            )

        # Step 2b: Invite Dagster admins to team (grants admin token access for channel creation)
        if not ctx.state.is_step_completed(OnboardingStep.ADMINS_INVITED):
            if not slack_team_result or not channel_setup_result:
                raise OnboardingStepError("Slack team or channel setup result is None")
            bot_server.logger.info("Executing step: Invite Dagster admins")
            await invite_admins_step(
                ctx=ctx,
                admin_token=admin_token,
                team_id=slack_team_result.team_id,
                general_channel_id=channel_setup_result.general_channel_id,
                dagster_admins_to_invite=bot_server.config.dagster_admins_to_invite,
                bot_server=bot_server,
            )
            bot_server.logger.info("Dagster admins invited")

        # Step 3: Retrieve bot IDs (verify bot tokens work)
        if not ctx.state.is_step_completed(OnboardingStep.BOT_IDS_RETRIEVED):
            bot_server.logger.info("Executing step: Retrieve bot IDs")
            await retrieve_bot_ids_step(
                ctx=ctx,
                org_bot_token=org_bot_token,
                compass_bot_token=compass_bot_token,
                bot_server=bot_server,
            )
            bot_server.logger.info("Bot IDs retrieved")

        # Step 4: Create contextstore repository
        if not ctx.state.is_step_completed(OnboardingStep.CONTEXTSTORE_REPO_CREATED):
            if not slack_team_result:
                raise OnboardingStepError("Slack team result is None")
            bot_server.logger.info("Executing step: Create contextstore repository")
            contextstore_result = await create_contextstore_repo(
                ctx=ctx,
                slack_team_result=slack_team_result,
                email=email,
                bot_server=bot_server,
            )
            bot_server.logger.info(
                f"Contextstore repository created: {contextstore_result.contextstore_repo_name}"
            )
        else:
            bot_server.logger.info(
                "Skipping step: Create contextstore repository (already completed)"
            )
            assert contextstore_result is not None

        # Step 5: Create Stripe customer
        # (can happen in parallel with bot setup since it's independent)
        if not ctx.state.is_step_completed(OnboardingStep.STRIPE_CUSTOMER_CREATED):
            if not slack_team_result:
                raise OnboardingStepError("Slack team result is None")
            bot_server.logger.info("Executing step: Create Stripe customer")
            await create_stripe_customer_step(
                ctx=ctx,
                slack_team_result=slack_team_result,
                organization=organization,
                email=email,
                bot_server=bot_server,
                organization_raw=organization_raw,
            )
            bot_server.logger.info("Stripe customer created")

        # Step 6: Create Stripe subscription
        if not ctx.state.is_step_completed(OnboardingStep.STRIPE_SUBSCRIPTION_CREATED):
            bot_server.logger.info("Executing step: Create Stripe subscription")
            billing_result = await create_stripe_subscription_step(ctx=ctx, bot_server=bot_server)
            bot_server.logger.info(
                f"Stripe subscription created: {billing_result.stripe_subscription_id}"
            )

        # Step 7: Create organization
        if not ctx.state.is_step_completed(OnboardingStep.ORGANIZATION_CREATED):
            if not billing_result:
                raise OnboardingStepError("Billing result is None")
            if not contextstore_result:
                raise OnboardingStepError("Contextstore result is None")
            bot_server.logger.info("Executing step: Create organization")
            await create_organization_step(
                ctx=ctx,
                billing_result=billing_result,
                organization=organization,
                email=email,
                token=token,
                bot_server=bot_server,
                organization_raw=organization_raw,
                contextstore_repo_name=contextstore_result.contextstore_repo_name,
                onboarding_type=onboarding_type,
            )
            bot_server.logger.info("Organization created in DB")

        # Step 8: Record TOS acceptance
        if not ctx.state.is_step_completed(OnboardingStep.TOS_RECORDED):
            if not billing_result or not slack_team_result:
                raise OnboardingStepError("Billing or slack team result is None")
            bot_server.logger.info("Executing step: Record TOS acceptance")
            organization_result = await record_tos_step(
                ctx=ctx,
                billing_result=billing_result,
                channel_setup_result=None,  # No channels in minimal onboarding
                slack_team_result=slack_team_result,
                organization_raw=organization_raw,
                email=email,
                bot_server=bot_server,
            )
            bot_server.logger.info("TOS acceptance recorded")

        # Note: Onboarding is NOT marked as COMPLETED here - it will be marked completed
        # after the first data source is connected and Slack Connect invite is sent

        if not organization_result or not slack_team_result:
            raise OnboardingStepError("Organization or slack team result is None after onboarding")

        # Schedule org onboarding check workflow to validate setup (delayed by 10 minutes)
        workflow_id = (
            f"org-onboarding-check-{organization_result.organization_id}-{str(uuid.uuid4())[:8]}"
        )
        bot_server.logger.info(
            f"Scheduling org onboarding validation workflow (10 minute delay): {workflow_id} "
            f"for organization_id={organization_result.organization_id}"
        )

        try:
            await start_workflow_with_search_attributes(
                bot_server.temporal_client,
                bot_server.config.temporal,
                constants.Workflow.ORG_ONBOARDING_CHECK_WORKFLOW_NAME.value,
                OrgOnboardingCheckInput(organization_id=organization_result.organization_id),
                id=workflow_id,
                task_queue=constants.DEFAULT_TASK_QUEUE,
                organization_name=organization_raw,
                start_delay=timedelta(minutes=10),
            )
            bot_server.logger.info(
                f"Successfully scheduled org onboarding validation workflow: {workflow_id} "
                f"(will start in 10 minutes)"
            )
        except Exception as e:
            bot_server.logger.error(
                f"Failed to schedule org onboarding validation workflow: {workflow_id}",
                exc_info=e,
            )

        contextstore_repo = (
            contextstore_result.contextstore_repo_name if contextstore_result else None
        )

        bot_server.logger.info(
            f"Minimal onboarding completed for {organization} - "
            f"organization_id={organization_result.organization_id}, team_id={slack_team_result.team_id}, "
            f"contextstore={contextstore_repo}"
        )

        return {
            "organization_id": organization_result.organization_id,
            "team_id": slack_team_result.team_id,
            "email": email,
            "contextstore_github_repo": contextstore_repo,
        }


def create_onboarding_status_handler(
    bot_server: "CompassBotServer",
) -> Callable[[web.Request], Awaitable[web.Response]]:
    """Create the onboarding status polling endpoint."""

    async def handle_onboarding_status(request: web.Request) -> web.Response:
        """Handle GET request - return the current onboarding status as JSON."""
        # Get query parameters
        email = request.query.get("email")
        organization = request.query.get("organization")

        if not email or not organization:
            return web.Response(
                status=400,
                text="Missing email or organization parameter",
                content_type="text/plain",
            )

        # Get onboarding state from storage
        # Sanitize organization name to match how it was stored during onboarding
        from csbot.slackbot.slack_utils import generate_urlsafe_team_name

        organization_sanitized = generate_urlsafe_team_name(organization)
        storage = bot_server.bot_manager.storage
        state = await storage.get_onboarding_state(email, organization_sanitized)

        if state is None:
            return web.json_response({"status": "not_started"})

        # Determine status: completed, error, or in_progress
        from csbot.slackbot.storage.onboarding_state import OnboardingStep

        if state.current_step == OnboardingStep.COMPLETED:
            return web.json_response({"status": "completed"})
        elif state.error_message:
            return web.json_response({"status": "error", "error_message": state.error_message})
        else:
            return web.json_response({"status": "in_progress"})

    return handle_onboarding_status


def create_onboarding_submit_api_handler(bot_server: "CompassBotServer"):
    """Create JSON API handler for onboarding form validation.

    This endpoint validates the onboarding form data and returns JSON.
    Used by the React frontend before starting background processing.
    """

    async def handle_onboarding_submit_api(request: web.Request) -> web.Response:
        """Validate onboarding form and return JSON response."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON in request body"}, status=400
            )

        token = body.get("token")
        email = body.get("email")
        organization = body.get("organization")
        storage = bot_server.bot_manager.storage

        # Token is optional - validate only if provided and not empty
        validated_token = None
        if token and isinstance(token, str) and token.strip():
            token_status = await storage.is_referral_token_valid(token)

            if not token_status.is_valid:
                return web.json_response(
                    {
                        "success": False,
                        "error": "The referral token is not valid.",
                        "error_type": "invalid_token",
                    },
                    status=400,
                )

            if token_status.has_been_consumed and token_status.is_single_use:
                return web.json_response(
                    {
                        "success": False,
                        "error": "This referral token can only be used once and has already been used.",
                        "error_type": "token_consumed",
                    },
                    status=400,
                )
            validated_token = token.strip()

        # Validate email
        if not email or not isinstance(email, str):
            return web.json_response(
                {
                    "success": False,
                    "error": "Please provide a valid email address.",
                    "error_type": "missing_email",
                },
                status=400,
            )

        if not is_valid_email(email):
            return web.json_response(
                {
                    "success": False,
                    "error": "Please provide a valid email address format.",
                    "error_type": "invalid_email",
                },
                status=400,
            )

        # Validate organization
        if not organization or not isinstance(organization, str):
            return web.json_response(
                {
                    "success": False,
                    "error": "Please provide your organization name.",
                    "error_type": "missing_organization",
                },
                status=400,
            )

        # Track analytics
        from csbot.slackbot.segment_analytics import track_onboarding_event

        track_onboarding_event(
            step_name="Organization Created",
            organization=organization,
            email=email,
            additional_info={
                "signup_date": datetime.now().isoformat(),
                "product": "Compass Bot",
            },
        )

        # Return success with validated data
        return web.json_response(
            {
                "success": True,
                "message": "Validation successful",
                "data": {
                    "email": email,
                    "organization": organization,
                    "has_token": validated_token is not None,
                },
            }
        )

    return handle_onboarding_submit_api


def create_onboarding_process_api_handler(bot_server: "CompassBotServer"):
    """Create JSON API handler for onboarding background processing.

    This handler validates the request, calls the shared create_onboarding helper,
    and returns a JSON response for the React frontend.
    """

    async def handle_onboarding_process_api(request: web.Request) -> web.Response:
        """Execute onboarding and return JSON response."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON in request body"}, status=400
            )

        token = request.cookies.get(REFERRAL_TOKEN_COOKIE_NAME)
        email = body.get("email")
        organization = body.get("organization")

        # Validate token if provided
        has_valid_token, error_message = await is_token_valid(token, organization, bot_server)
        if not has_valid_token:
            return web.json_response({"success": False, "error": error_message}, status=400)

        # Validate email and organization
        if not email or not isinstance(email, str):
            return web.json_response(
                {"success": False, "error": "Missing or invalid email"}, status=400
            )

        if not organization or not isinstance(organization, str):
            return web.json_response(
                {"success": False, "error": "Missing or invalid organization"}, status=400
            )

        if not is_valid_email(email):
            return web.json_response(
                {"success": False, "error": "Invalid email format"}, status=400
            )

        # Determine onboarding type based on token
        from csbot.slackbot.flags import is_prospector_grant_token

        onboarding_type = "standard"
        if token and isinstance(token, str) and token.strip() and has_valid_token:
            if is_prospector_grant_token(token):
                onboarding_type = "prospector"

        # Call minimal onboarding helper (creates org + team + Stripe only)
        try:
            result = await create_minimal_onboarding(
                bot_server=bot_server,
                email=email,
                organization_raw=organization,
                token=token,
                has_valid_token=has_valid_token,
                onboarding_type=onboarding_type,
            )

            # Return JSON response with redirect URL
            response = web.json_response(
                {
                    "success": True,
                    "redirect_url": "/onboarding/connections",
                    "message": "Organization created successfully",
                }
            )

            set_onboarding_auth_cookie(
                response=response,
                bot_server=bot_server,
                max_age=timedelta(hours=6),
                organization_id=result["organization_id"],
                team_id=result["team_id"],
                email=email,
            )

            return response
        except OnboardingStepError as e:
            # Determine status code based on error type
            if isinstance(
                e, BillingSetupError | OrganizationCreationError | BotInstanceCreationError
            ):
                status_code = 500
            elif isinstance(e, OnboardingInProgressError):
                status_code = 429
            else:
                status_code = 400

            return web.json_response(
                {
                    "success": False,
                    "message": e.user_facing_message,
                },
                status=status_code,
            )

    return handle_onboarding_process_api
