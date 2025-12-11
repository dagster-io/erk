"""Helper functions for billing operations - extracting repeated business logic.

These helpers contain actual business logic (not thin API wrappers):
- Bot instance validation and fetching
- Usage data aggregation and filtering
- Current plan determination from subscriptions
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiohttp import web

from csbot.slackbot.webapp.htmlstring import HtmlString

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot import CompassChannelBaseBotInstance


async def get_validated_billing_bot(
    bot_server: "CompassBotServer",
    request: web.Request,
) -> tuple["CompassChannelBaseBotInstance", str]:
    """Validate billing access and return bot with Stripe customer ID.

    This extracts the common pattern of validating JWT, fetching bot instance,
    and ensuring Stripe customer ID exists. Used by all billing endpoints.

    Args:
        bot_server: The bot server instance
        request: The aiohttp request

    Returns:
        Tuple of (bot, stripe_customer_id)

    Raises:
        web.HTTPException: If validation fails (401, 404, etc.)
    """
    from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance
    from csbot.slackbot.webapp.security import ensure_token_is_valid

    async def get_error_message() -> HtmlString:
        return HtmlString(
            unsafe_html="<h1>Access Denied</h1><p>You don't have permission to manage billing.</p>"
        )

    # Validate JWT token
    organization_context = await ensure_token_is_valid(
        bot_server=bot_server,
        error_message=get_error_message,
        request=request,
    )

    # Find governance bot for this organization
    governance_bot = None
    for bot_instance in bot_server.bots.values():
        if (
            bot_instance.bot_config.organization_id == organization_context.organization_id
            and bot_instance.bot_config.team_id == organization_context.team_id
        ):
            if isinstance(bot_instance.bot_type, (BotTypeGovernance, BotTypeCombined)):
                governance_bot = bot_instance
                break

    if not governance_bot:
        raise web.HTTPNotFound(
            text='{"error": "No governance bot found for organization"}',
            content_type="application/json",
        )

    # Get bot config with Stripe customer ID
    bot_instance = governance_bot.bot_config
    if not bot_instance or not bot_instance.stripe_customer_id:
        raise web.HTTPBadRequest(
            text='{"error": "No Stripe customer associated with this organization"}',
            content_type="application/json",
        )

    return governance_bot, bot_instance.stripe_customer_id


async def get_current_plan_name(
    stripe_client: Any,
    bot_instance: Any,
    plan_config: list[dict[str, str | list[str] | None]],
) -> str | None:
    """Determine current plan name from subscription.

    Extracts the logic of fetching subscription, getting product ID,
    and matching to plan configuration.

    Args:
        stripe_client: Stripe client instance
        bot_instance: Bot instance with subscription info
        plan_config: List of plan configurations from get_plan_config()

    Returns:
        Plan name (lowercase) or None if no subscription
        For unknown product IDs, returns the product ID itself
    """
    # Check if bot has a subscription
    if not bot_instance.stripe_subscription_id:
        return "free"  # No subscription means free plan

    # Get subscription details
    subscription_details = await asyncio.to_thread(
        stripe_client.get_subscription_details,
        bot_instance.stripe_subscription_id,
    )

    # Only consider active subscriptions
    if subscription_details.get("status") != "active":
        return "free"  # Inactive subscription defaults to free

    # Extract product ID from subscription
    items = subscription_details.get("items", {}).get("data", [])
    if not items:
        return "free"

    item = items[0]
    if not item.get("price") or not item["price"].get("product"):
        return "free"

    current_product_id = item["price"]["product"]

    # Match product ID to plan name
    for plan in plan_config:
        if plan.get("product_id") == current_product_id:
            plan_name = plan.get("name", "")
            if isinstance(plan_name, str):
                return plan_name.lower()

    # Unknown product - return product ID itself
    return current_product_id


async def get_organization_current_month_usage(
    analytics_store: Any,
    organization_id: int,
) -> dict[str, Any]:
    """Get current month usage statistics for an organization.

    Aggregates usage data for the current month, including:
    - Total answers (with and without bonus)
    - Unique users who asked questions
    - Per-bot breakdowns

    Args:
        analytics_store: Analytics store instance
        organization_id: Organization ID

    Returns:
        Dict with usage statistics:
        - total_answers: Total answers this month (including bonus)
        - total_answers_no_bonus: Answers without bonus
        - total_unique_users: Unique users who asked questions
        - bot_details: List of per-bot usage (top 10)
        - current_month_name: Formatted month name
    """
    # Get current month boundaries
    now = datetime.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month = now.month
    current_year = now.year

    # Get usage data
    usage_data = await analytics_store.get_organization_usage_tracking_data(
        organization_id, include_bonus_answers=True
    )
    usage_data_no_bonus = await analytics_store.get_organization_usage_tracking_data(
        organization_id, include_bonus_answers=False
    )

    # Get analytics data for unique user counting
    current_month_days = (now - current_month_start).days + 1
    analytics_data = await analytics_store.get_organization_analytics_data(
        organization_id, days=current_month_days
    )

    # Filter analytics to current month only
    current_month_analytics = []
    for record in analytics_data:
        created_at = record["created_at"]
        # Parse if string, otherwise use as-is
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
        if created_at >= current_month_start:
            current_month_analytics.append(record)

    # Count unique users by bot (only users who asked questions)
    unique_users_by_bot: dict[str, set[str]] = {}
    for record in current_month_analytics:
        bot_id = record.get("bot_id")
        user_id = record.get("user_id")
        event_type = record.get("event_type")

        if bot_id and user_id and event_type in ["new_conversation", "new_reply"]:
            if bot_id not in unique_users_by_bot:
                unique_users_by_bot[bot_id] = set()
            unique_users_by_bot[bot_id].add(user_id)

    # Calculate totals
    total_answers = 0
    total_answers_no_bonus = 0
    bot_usage: dict[str, dict[str, Any]] = {}

    # Process usage data for current month
    for record in usage_data:
        if record.get("month") == current_month and record.get("year") == current_year:
            bot_id = record.get("bot_id", "Unknown Bot")
            answer_count = record.get("answer_count", 0) or 0

            bot_usage[bot_id] = {
                "answer_count": answer_count,
                "last_updated": record.get("updated_at", "Unknown"),
                "unique_users": len(unique_users_by_bot.get(bot_id, set())),
            }
            total_answers += answer_count

    for record in usage_data_no_bonus:
        if record.get("month") == current_month and record.get("year") == current_year:
            answer_count = record.get("answer_count", 0) or 0
            total_answers_no_bonus += answer_count

    # Build bot details list (sorted by usage, top 10)
    bot_details = [
        {
            "bot_id": bot_id,
            "answer_count": usage["answer_count"],
            "unique_users_this_month": usage["unique_users"],
            "last_updated": usage["last_updated"],
        }
        for bot_id, usage in bot_usage.items()
    ]
    bot_details.sort(key=lambda x: x["answer_count"], reverse=True)

    # Count total unique users across all bots
    all_unique_users = set()
    for record in current_month_analytics:
        user_id = record.get("user_id")
        event_type = record.get("event_type")
        if user_id and event_type in ["new_conversation", "new_reply"]:
            all_unique_users.add(user_id)

    return {
        "total_answers": total_answers,
        "total_answers_no_bonus": total_answers_no_bonus,
        "bonus_answers_this_month": total_answers - total_answers_no_bonus,
        "total_unique_users": len(all_unique_users),
        "bot_count": len(bot_details),
        "bot_details": bot_details[:10],  # Top 10 bots
        "current_month_name": current_month_start.strftime("%B %Y"),
    }
