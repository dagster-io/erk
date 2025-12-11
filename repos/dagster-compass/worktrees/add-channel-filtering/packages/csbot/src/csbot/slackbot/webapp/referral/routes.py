import asyncio
import uuid

from aiohttp import web

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.slackbot_analytics import (
    AnalyticsEventType,
    log_analytics_event_unified,
)
from csbot.slackbot.storage.utils import is_postgresql
from csbot.slackbot.webapp.billing.billing import get_validated_billing_bot


def add_referral_routes(app: web.Application, bot_server: CompassBotServer):
    """Add referral routes to the webapp."""
    app.router.add_post(
        "/api/referral/generate-referral-token", create_generate_referral_token_handler(bot_server)
    )
    app.router.add_post(
        "/api/referral/log-copy-referral-link", create_log_copy_referral_link_handler(bot_server)
    )


def create_generate_referral_token_handler(bot_server: CompassBotServer):
    """Create handler to generate or retrieve referral token for organization."""

    async def generate_referral_token_handler(request: web.Request) -> web.Response:
        """Handle referral token generation requests."""

        # Validate billing access and get bot with organization
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)
        bot_instance = bot.bot_config

        # Check storage is available
        if not bot_server.bot_manager or not bot_server.bot_manager.storage:
            return web.json_response({"error": "Storage not available"}, status=503)

        storage = bot_server.bot_manager.storage

        # Get organization ID
        if not bot_instance or not bot_instance.organization_id:
            return web.json_response({"error": "No organization ID available"}, status=404)

        organization_id = bot_instance.organization_id

        try:
            # Get organization details to fetch name
            all_orgs = await storage.list_organizations()
            org = next((o for o in all_orgs if o.organization_id == organization_id), None)
            if not org:
                return web.json_response({"error": "Organization not found"}, status=404)

            org_name = org.organization_name or "org"

            # Check if organization already has a referral token by listing all tokens
            all_tokens = await storage.list_invite_tokens()
            existing_token = next(
                (t for t in all_tokens if t.issued_by_organization_id == organization_id), None
            )

            if existing_token:
                # Return existing token
                token_string = existing_token.token
            else:
                # Generate new token: org_name[:6] + 4 random chars
                org_prefix = org_name[:6].lower().replace(" ", "")
                random_suffix = uuid.uuid4().hex[:4]
                token_string = f"{org_prefix}{random_suffix}"

                # Create referral token in storage using create_invite_token
                await asyncio.to_thread(
                    storage.create_invite_token,
                    token_string,
                    is_single_use=False,  # Multi-use for org-generated tokens
                    consumer_bonus_answers=50,  # New users get 50 bonus answers
                )

                # Update the token to set issued_by_organization_id
                # This is done via direct SQL since create_invite_token doesn't support this field
                def update_token_issuer(conn_factory, token: str, org_id: int):
                    with conn_factory.with_conn() as conn:
                        cursor = conn.cursor()
                        if is_postgresql(conn):
                            cursor.execute(
                                "UPDATE referral_tokens SET issued_by_organization_id = %s WHERE token = %s",
                                (org_id, token),
                            )
                        else:
                            cursor.execute(
                                "UPDATE referral_tokens SET issued_by_organization_id = ? WHERE token = ?",
                                (org_id, token),
                            )

                        conn.commit()

                await asyncio.to_thread(
                    update_token_issuer, bot_server.sql_conn_factory, token_string, organization_id
                )

            # Build onboarding link
            public_url = bot_server.config.public_url
            onboarding_link = f"{public_url}/signup?referral-token={token_string}"

            try:
                await log_analytics_event_unified(
                    analytics_store=bot.analytics_store,
                    event_type=AnalyticsEventType.REFERRAL_LINK_GENERATED,
                    bot_id=bot.key.to_bot_id(),
                    organization_name=bot_instance.organization_name,
                    organization_id=bot_instance.organization_id,
                    team_id=bot.key.team_id,
                )
            except Exception as e:
                bot_server.logger.error(
                    f"Failed to log referral link generated for organization {organization_id}: {str(e)}"
                )

            return web.json_response(
                {
                    "success": True,
                    "token": token_string,
                    "onboarding_link": onboarding_link,
                }
            )

        except Exception as e:
            return web.json_response(
                {"error": f"Failed to generate referral token: {str(e)}"}, status=500
            )

    return generate_referral_token_handler


def create_log_copy_referral_link_handler(bot_server: CompassBotServer):
    """Create handler to log event when user copy the referral link issued for their organization."""

    async def log_copy_referral_link_handler(request: web.Request) -> web.Response:
        """Handle referral link copied."""

        # Validate billing access and get bot with organization
        bot, _ = await get_validated_billing_bot(bot_server, request)
        bot_instance = bot.bot_config

        # Get organization ID
        if not bot_instance or not bot_instance.organization_id:
            return web.json_response({"error": "No organization ID available"}, status=404)

        try:
            await log_analytics_event_unified(
                analytics_store=bot.analytics_store,
                event_type=AnalyticsEventType.REFERRAL_LINK_COPIED,
                bot_id=bot.key.to_bot_id(),
                organization_name=bot_instance.organization_name,
                organization_id=bot_instance.organization_id,
                team_id=bot.key.team_id,
            )
        except Exception as e:
            return web.json_response(
                {"error": f"Failed to log referral link copied: {str(e)}"}, status=500
            )

        return web.json_response(
            {
                "success": True,
            }
        )

    return log_copy_referral_link_handler
