import asyncio
from datetime import datetime
from typing import Any

from aiohttp import web
from dateutil.relativedelta import relativedelta

from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.webapp.billing.billing import (
    get_current_plan_name,
    get_validated_billing_bot,
)
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.security import OrganizationContext, require_permission
from csbot.stripe.stripe_utils import (
    update_plan_limits_from_product,
    update_plan_limits_with_dependencies,
)


async def switch_subscription_to_product(
    stripe_customer_id: str,
    target_product_id: str,
    organization_id: int,
    existing_subscription_id: str | None = None,
    stripe_client: Any | None = None,
    storage: Any | None = None,
    bot_server: CompassBotServer | None = None,
) -> dict[str, str | bool]:
    """Switch a subscription to a new product or create a new subscription.

    This is the shared logic used by both billing routes and admin panel.

    Args:
        stripe_client: Stripe client instance (preferred over bot_server.stripe_client)
        storage: Storage instance (preferred over bot_server.bot_manager.storage)
        bot_server: Bot server instance (legacy - use stripe_client and storage instead)
        existing_subscription_id: Current subscription ID (if any)
        stripe_customer_id: Stripe customer ID
        target_product_id: Target product ID to switch to
        organization_id: Organization ID for plan limits update

    Returns:
        Dictionary with success/error info and subscription_id

    Raises:
        Exception: If subscription switch fails
    """
    # Support both new style (direct dependencies) and legacy style (bot_server)
    if stripe_client is None:
        if (
            bot_server is None
            or not hasattr(bot_server, "stripe_client")
            or not bot_server.stripe_client
        ):
            raise Exception("Stripe client not available")
        stripe_client = bot_server.stripe_client

    if storage is None:
        if (
            bot_server is None
            or not hasattr(bot_server, "bot_manager")
            or not bot_server.bot_manager
        ):
            raise Exception("Bot manager not available")
        storage = bot_server.bot_manager.storage

    # Check if we have an active subscription to update
    active_subscription = None
    if existing_subscription_id:
        try:
            import stripe

            subscription = stripe.Subscription.retrieve(existing_subscription_id)
            if subscription.get("status") == "active":
                active_subscription = subscription
        except Exception:
            # Continue without active subscription
            pass

    if active_subscription:
        # Update existing active subscription
        import stripe

        # Get the new price for the target product
        prices = stripe.Price.list(product=target_product_id, active=True, limit=1)
        if not prices.data:
            raise Exception(f"No active prices found for product {target_product_id}")

        new_price_id = prices.data[0].id

        # Update the subscription to the new product
        updated_subscription = stripe.Subscription.modify(
            active_subscription["id"],
            items=[
                {
                    "id": active_subscription["items"]["data"][0]["id"],
                    "price": new_price_id,
                }
            ],
            metadata={"product_id": str(target_product_id)},
            proration_behavior="always_invoice",  # Prorate the change immediately
        )

        # Update plan limits for the organization based on the new product metadata
        if bot_server:
            # Legacy call with bot_server
            if not bot_server.stripe_client:
                raise ValueError("Stripe client not available")
            await update_plan_limits_from_product(
                stripe_client=bot_server.stripe_client,
                plan_manager=bot_server.bot_manager.storage,
                product_id=target_product_id,
                organization_id=organization_id,
            )
        else:
            # Direct call with dependencies
            await update_plan_limits_with_dependencies(
                stripe_client=stripe_client,
                storage=storage,
                product_id=target_product_id,
                organization_id=organization_id,
            )

        return {"success": True, "subscription_id": updated_subscription["id"], "action": "updated"}

    else:
        # Create new subscription (no active subscription exists)
        new_subscription = await asyncio.to_thread(
            stripe_client.create_subscription,
            stripe_customer_id,
            target_product_id,
        )

        # Update plan limits for the organization based on the new product metadata
        if bot_server:
            # Legacy call with bot_server
            if not bot_server.stripe_client:
                raise ValueError("Stripe client not available")
            await update_plan_limits_from_product(
                stripe_client=bot_server.stripe_client,
                plan_manager=bot_server.bot_manager.storage,
                product_id=target_product_id,
                organization_id=organization_id,
            )
        else:
            # Direct call with dependencies
            await update_plan_limits_with_dependencies(
                stripe_client=stripe_client,
                storage=storage,
                product_id=target_product_id,
                organization_id=organization_id,
            )

        return {"success": True, "subscription_id": new_subscription["id"], "action": "created"}


def get_plan_config(bot_server: CompassBotServer) -> list[dict[str, str | list[str] | None]]:
    """Get plan configuration with product IDs from config."""
    return [
        {
            "name": "Free",
            "description": "Try Compass for free with limited usage in a single channel.",
            "product_id": bot_server.config.stripe.free_product_id,
            "formatted_price": "$0/mo",
            "features": [
                "20 Answers/month",
                "1 Channel",
                "Supported data: Prospecting data + connect your data warehouse",
                "AI Governance and customization",
            ],
            "color_scheme": "gray",
        },
        {
            "name": "Starter",
            "description": "Leverage Compass at low volume - perfect for small teams.",
            "product_id": bot_server.config.stripe.starter_product_id,
            "formatted_price": "$49/mo",
            "features": [
                "75 Answers/month",
                "1 Channel",
                "$0.70 per additional Answer",
                "Supported data: Prospecting data + connect your data warehouse",
                "AI Governance and customization",
            ],
            "color_scheme": "blue",
        },
        {
            "name": "Team",
            "description": "Use Compass across your organization with higher message.",
            "product_id": bot_server.config.stripe.team_product_id,
            "formatted_price": "$499/mo",
            "features": [
                "750 Answers/month",
                "3 Channels",
                "$0.50 per additional Answer",
                "Supported data: Prospecting data + connect your data warehouse",
                "AI Governance and customization",
            ],
            "color_scheme": "purple",
        },
        {
            "name": "Pro",
            "description": "Connect Compass to your data for custom, governed insights.",
            "product_id": None,  # Will need to add this product ID
            "formatted_price": "Contact us",
            "features": [
                "Custom volume",
                "Unlimited Channels",
                "Supported data: Prospecting data + connect your data warehouse",
                "Advanced governance, customization, and enterprise support",
            ],
            "color_scheme": "gradient",
        },
    ]


async def _get_billing_data(bot_server: CompassBotServer, bot) -> dict:
    """Extract billing data logic for both Jinja and JSON responses.

    Args:
        bot: The CompassChannelBotInstance
        bot_server: The bot server instance

    Returns:
        A dict with all billing information that can be used by both
        the Jinja template handler and the JSON API handler.
    """
    analytics_store = bot.analytics_store

    # Get organization ID from the bot instance
    bot_instance = bot.bot_config
    if not bot_instance or not bot_instance.organization_id:
        # No organization ID available, return empty state
        return {
            "no_bot_available": True,
            "has_stripe_client": bot_server.stripe_client is not None,
            "stripe_publishable_key": None,
            "plan_pricing_data": [],
            "current_plan": None,
            "usage_data": None,
            "has_subscription": False,
            "payment_method_info": None,
            "billing_details": None,
        }

    organization_id = bot_instance.organization_id

    # Get Stripe billing information if available
    payment_method_info = None
    billing_details = None
    current_plan = None
    has_subscription = False

    # Get bot instance data from storage to access Stripe customer ID
    if bot_server.stripe_client and bot_server.bot_manager:
        try:
            if bot_instance and bot_instance.stripe_customer_id:
                # Get payment methods
                payment_methods = await asyncio.to_thread(
                    bot_server.stripe_client.get_customer_payment_methods,
                    bot_instance.stripe_customer_id,
                )
                payment_method_info = {
                    "has_payment_method": len(payment_methods) > 0,
                    "payment_methods": payment_methods,
                }

                # Get customer details
                customer_details = await asyncio.to_thread(
                    bot_server.stripe_client.get_customer_details,
                    bot_instance.stripe_customer_id,
                )
                billing_details = {
                    "email": customer_details.get("email"),
                }

                # Get current subscription to determine selected plan
                if (
                    bot_instance
                    and hasattr(bot_instance, "stripe_subscription_id")
                    and bot_instance.stripe_subscription_id
                ):
                    subscription_id = bot_instance.stripe_subscription_id
                    subscription_details = await asyncio.to_thread(
                        bot_server.stripe_client.get_subscription_details, subscription_id
                    )

                    # Check if subscription is active
                    if subscription_details.get("status") == "active":
                        has_subscription = True

                        # Extract product ID from subscription
                        if subscription_details.get("items") and subscription_details["items"].get(
                            "data"
                        ):
                            subscription_items = subscription_details["items"]["data"]
                            if subscription_items:
                                # Get the first item's price and product
                                item = subscription_items[0]
                                if item.get("price") and item["price"].get("product"):
                                    current_product_id = item["price"]["product"]

                                    # Match product ID to plan name
                                    plan_found = False
                                    for plan in get_plan_config(bot_server):
                                        if plan.get("product_id") == current_product_id:
                                            plan_name = plan.get("name", "")
                                            if isinstance(plan_name, str):
                                                current_plan = plan_name.lower()
                                                plan_found = True
                                            break

                                    # If we have a subscription but unknown product, set to the product ID
                                    if not plan_found:
                                        current_plan = current_product_id

                # If no subscription found at all, assume Free plan
                if current_plan is None:
                    current_plan = "free"
        except Exception:
            # If Stripe calls fail, we'll just not show the billing info
            pass

    # Get plan configuration data
    plan_pricing_data = [plan.copy() for plan in get_plan_config(bot_server)]

    # If user has an unknown plan, fetch its price and update the Pro plan display
    if current_plan and current_plan not in ["free", "starter", "team"]:
        # This means current_plan is a product ID for an unknown plan
        if bot_server.stripe_client:
            try:
                product_with_price = await asyncio.to_thread(
                    bot_server.stripe_client.get_product_with_price, current_plan
                )

                # Convert cents to dollars (ensure float for JSON serialization)
                price_dollars = float(product_with_price.unit_amount) / 100
                formatted_price = f"${price_dollars:.0f}"

                # Add recurring info if available
                if product_with_price.recurring_interval:
                    formatted_price += f"/{product_with_price.recurring_interval}"

                # Update the Pro plan to show the actual price
                for plan in plan_pricing_data:
                    if plan.get("name") == "Pro":
                        plan["formatted_price"] = formatted_price
                        break
            except Exception:
                # If fetching fails, keep the default "Contact us"
                pass

    # Get usage tracking data for the entire organization
    usage_data = await analytics_store.get_organization_usage_tracking_data(
        organization_id, include_bonus_answers=True
    )
    usage_data_no_bonus = await analytics_store.get_organization_usage_tracking_data(
        organization_id, include_bonus_answers=False
    )

    # Calculate current month
    now = datetime.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get analytics data for the current month to count unique users
    current_month_days = (now - current_month_start).days + 1
    analytics_data = await analytics_store.get_organization_analytics_data(
        organization_id, days=current_month_days
    )

    # Filter analytics data to current month only
    current_month_analytics = []
    for record in analytics_data:
        created_at = record["created_at"]
        # Parse created_at if it's a string, otherwise use as-is
        if isinstance(created_at, str):
            try:
                # Try standard ISO format first
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                # Skip this record if we can't parse the date
                continue
        # Compare datetime objects
        if created_at >= current_month_start:
            current_month_analytics.append(record)

    # Count unique users by bot for current month - only users who asked questions
    unique_users_by_bot = {}
    for record in current_month_analytics:
        bot_id = record.get("bot_id")
        user_id = record.get("user_id")
        event_type = record.get("event_type")

        # Only count users who asked questions (new conversations or replies)
        if bot_id and user_id and event_type in ["new_conversation", "new_reply"]:
            if bot_id not in unique_users_by_bot:
                unique_users_by_bot[bot_id] = set()
            unique_users_by_bot[bot_id].add(user_id)

    # Convert sets to counts
    unique_user_counts_by_bot = {
        bot_id: len(user_set) for bot_id, user_set in unique_users_by_bot.items()
    }

    # Calculate totals
    total_answers = 0
    total_answers_no_bonus = 0
    total_unique_users = len(
        set(
            record.get("user_id")
            for record in current_month_analytics
            if record.get("user_id")
            and record.get("event_type") in ["new_conversation", "new_reply"]
        )
    )
    bot_details = []

    # Filter usage data for current month and group by bot_id
    current_month = now.month
    current_year = now.year
    bot_usage_current_month = {}

    for record in usage_data:
        # With new monthly structure, check if record is for current month/year
        if record.get("month") == current_month and record.get("year") == current_year:
            bot_id = record.get("bot_id", "Unknown Bot")
            answer_count = record.get("answer_count", 0) or 0
            updated_at = record.get("updated_at", "Unknown")

            bot_usage_current_month[bot_id] = {
                "answer_count": answer_count,
                "last_updated": updated_at,
                "unique_users_this_month": unique_user_counts_by_bot.get(bot_id, 0),
            }
            total_answers += answer_count

    for record in usage_data_no_bonus:
        if record.get("month") == current_month and record.get("year") == current_year:
            answer_count = record.get("answer_count", 0) or 0
            total_answers_no_bonus += answer_count

    # Create bot_details from current month usage
    for bot_id, usage_info in bot_usage_current_month.items():
        bot_details.append(
            {
                "bot_id": bot_id,
                "answer_count": usage_info["answer_count"],
                "last_updated": usage_info["last_updated"],
                "unique_users_this_month": usage_info["unique_users_this_month"],
            }
        )

    # Sort bots by answer count (descending)
    bot_details.sort(key=lambda x: x["answer_count"], reverse=True)

    # Prepare bot details with channel names
    response_bot_details = []
    for bot_detail in bot_details:
        bot_key_obj = BotKey.from_bot_id(bot_detail["bot_id"])
        # Convert datetime to ISO format string for JSON serialization
        last_updated = bot_detail["last_updated"]
        if isinstance(last_updated, datetime):
            last_updated = last_updated.isoformat()
        response_bot_details.append(
            {
                "channel_name": bot_key_obj.channel_name,
                "bot_id": bot_detail["bot_id"],
                "answer_count": bot_detail["answer_count"],
                "unique_users_this_month": bot_detail["unique_users_this_month"],
                "last_updated": last_updated,
            }
        )

    # Get plan limits and bonus answer data for the organization (only for active subscriptions)
    plan_limit_value = None
    has_overage_available = False
    bonus_answers_earned = 0
    bonus_answers_used = 0
    bonus_answers_remaining = 0
    if bot_server.bot_manager and has_subscription:
        try:
            if (
                bot_instance
                and bot_instance.organization_id
                and bot_instance.stripe_subscription_id
            ):
                plan_limits = await bot_server.get_plan_limits_from_cache_or_fallback(
                    bot_instance.organization_id, bot_instance.stripe_subscription_id
                )
                plan_limit_value = plan_limits.base_num_answers
                has_overage_available = plan_limits.allow_overage

                # Get bonus answer grant data for this organization
                bonus_answers_earned = await analytics_store.get_organization_bonus_answer_grants(
                    bot_instance.organization_id
                )

                # Get bonus answers consumed directly from usage_tracking table
                bonus_answers_used = await analytics_store.get_organization_bonus_answers_consumed(
                    bot_instance.organization_id
                )

                # Calculate remaining bonus answers
                bonus_answers_remaining = max(0, bonus_answers_earned - bonus_answers_used)
        except Exception:
            # If plan limit retrieval fails, continue without it
            pass

    # Return common data structure
    return {
        "no_bot_available": False,
        "has_stripe_client": bot_server.stripe_client is not None,
        "stripe_publishable_key": bot_server.config.stripe.publishable_key
        if bot_server.config.stripe.publishable_key
        else None,
        "plan_pricing_data": plan_pricing_data,
        "current_plan": current_plan,
        "has_subscription": has_subscription,
        "payment_method_info": payment_method_info,
        "billing_details": billing_details,
        "usage_data": {
            "total_answers": total_answers,
            "total_answers_no_bonus": total_answers_no_bonus,
            "bonus_answers_this_month": total_answers - total_answers_no_bonus,
            "total_unique_users": total_unique_users,
            "bot_count": len(bot_details),
            "current_month_name": current_month_start.strftime("%B %Y"),
            "bonus_answers_remaining": bonus_answers_remaining,
            "bonus_answers_earned": bonus_answers_earned,
            "bonus_answers_used": bonus_answers_used,
            "plan_limit": plan_limit_value,
            "has_overage_available": has_overage_available,
            "bot_details": response_bot_details,
        },
    }


def add_billing_routes(app: web.Application, bot_server: CompassBotServer):
    """Add billing management routes to the webapp."""
    # /billing route is handled by React SPA in routes.py
    app.router.add_get("/api/billing/data", create_billing_data_handler(bot_server))
    app.router.add_get("/api/billing/stripe-data", create_stripe_data_handler(bot_server))
    app.router.add_get("/api/billing/usage-history", create_usage_history_handler(bot_server))
    app.router.add_get(
        "/api/billing/current-month-usage", create_current_month_usage_handler(bot_server)
    )
    app.router.add_get("/api/billing/plan-limits", create_plan_limits_handler(bot_server))
    app.router.add_post("/api/billing/switch-plan", create_plan_switch_handler(bot_server))
    app.router.add_post("/api/billing/create-setup-intent", create_setup_intent_handler(bot_server))
    app.router.add_post(
        "/api/billing/confirm-payment-method", create_confirm_payment_method_handler(bot_server)
    )
    app.router.add_delete(
        "/api/billing/payment-method/{payment_method_id}",
        create_delete_payment_method_handler(bot_server),
    )
    app.router.add_put("/api/billing/customer-details", create_update_customer_handler(bot_server))


def create_billing_data_handler(bot_server: CompassBotServer):
    """Create billing data API handler for React frontend."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_BILLING,
    )
    async def billing_data_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle billing data API requests - returns all billing info as JSON."""
        from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance

        # Find governance bot for this organization
        bot = None
        for bot_instance in bot_server.bots.values():
            if (
                bot_instance.bot_config.organization_id == organization_context.organization_id
                and bot_instance.bot_config.team_id == organization_context.team_id
            ):
                if isinstance(bot_instance.bot_type, (BotTypeGovernance, BotTypeCombined)):
                    bot = bot_instance
                    break

        if not bot:
            # No bots available, return empty state
            return web.json_response(
                {
                    "no_bot_available": True,
                    "has_stripe_client": bot_server.stripe_client is not None,
                    "stripe_publishable_key": None,
                    "plan_pricing_data": [],
                    "current_plan": None,
                    "usage_data": None,
                    "has_subscription": False,
                    "payment_method_info": None,
                    "billing_details": None,
                }
            )

        # Get common billing data
        billing_data = await _get_billing_data(bot_server, bot)

        # Return as JSON
        return web.json_response(billing_data)

    return billing_data_handler


def create_stripe_data_handler(bot_server: CompassBotServer):
    """Create Stripe data API handler."""

    async def stripe_data_handler(request: web.Request) -> web.Response:
        """Handle Stripe data API requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)
        bot_instance = bot.bot_config

        # Get Stripe billing information
        payment_method_info = None
        billing_details = None
        current_plan = None
        plan_pricing_data = []

        if bot_server.stripe_client:
            try:
                # Get payment methods
                payment_methods = await asyncio.to_thread(
                    bot_server.stripe_client.get_customer_payment_methods, stripe_customer_id
                )
                payment_method_info = {
                    "has_payment_method": len(payment_methods) > 0,
                    "payment_methods": payment_methods,
                }

                # Get customer details
                customer_details = await asyncio.to_thread(
                    bot_server.stripe_client.get_customer_details, stripe_customer_id
                )
                billing_details = {
                    "email": customer_details.get("email"),
                }

                # Determine current plan from subscription
                current_plan = await get_current_plan_name(
                    bot_server.stripe_client, bot_instance, get_plan_config(bot_server)
                )

                # Get plan configuration data
                plan_pricing_data = [plan.copy() for plan in get_plan_config(bot_server)]

                # If user has an unknown plan, fetch its price and update the Pro plan display
                if current_plan and current_plan not in ["free", "starter", "team", "pro"]:
                    # This means current_plan is a product ID for an unknown plan
                    try:
                        product_with_price = await asyncio.to_thread(
                            bot_server.stripe_client.get_product_with_price, current_plan
                        )

                        # Format price for display
                        if product_with_price.unit_amount > 0:
                            # Convert cents to dollars (ensure float for JSON serialization)
                            price_dollars = float(product_with_price.unit_amount) / 100
                            formatted_price = f"${price_dollars:.0f}"

                            # Add recurring info if available
                            if product_with_price.recurring_interval:
                                formatted_price += f"/{product_with_price.recurring_interval}"

                            # Update the Pro plan to show the actual price
                            for plan in plan_pricing_data:
                                if plan.get("name") == "Pro":
                                    plan["formatted_price"] = formatted_price
                                    break
                    except Exception:
                        # If fetching fails, keep the default "Contact us"
                        pass

            except Exception:
                return web.json_response({"error": "Failed to fetch Stripe data"}, status=500)
        else:
            # No Stripe client, just get plan configuration data
            plan_pricing_data = [plan.copy() for plan in get_plan_config(bot_server)]

        return web.json_response(
            {
                "stripe_available": bot_server.stripe_client is not None,
                "payment_method_info": payment_method_info,
                "billing_details": billing_details,
                "plan_pricing_data": plan_pricing_data,
                "current_plan": current_plan,
            }
        )

    return stripe_data_handler


def create_usage_history_handler(bot_server: CompassBotServer):
    """Create usage history API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_BILLING,
    )
    async def usage_history_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle usage history API requests."""
        from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance

        # Find governance bot for this organization
        bot = None
        for bot_instance in bot_server.bots.values():
            if (
                bot_instance.bot_config.organization_id == organization_context.organization_id
                and bot_instance.bot_config.team_id == organization_context.team_id
            ):
                if isinstance(bot_instance.bot_type, (BotTypeGovernance, BotTypeCombined)):
                    bot = bot_instance
                    break

        if not bot:
            return web.json_response({"error": "No bot instances available"}, status=404)

        analytics_store = bot.analytics_store

        # Get organization ID from the bot instance
        bot_instance = bot.bot_config
        if not bot_instance or not bot_instance.organization_id:
            return web.json_response({"error": "No organization ID available"}, status=404)

        organization_id = bot_instance.organization_id

        # Get historical usage data for the entire organization (last 12 months)
        usage_data = await analytics_store.get_organization_usage_tracking_data(
            organization_id, include_bonus_answers=True
        )

        # Get plan limits for the organization
        if not bot_instance.stripe_subscription_id:
            return web.json_response(
                {"error": "No stripe subscription ID available"},
                status=404,
            )
        plan_limit = await bot_server.get_plan_limits_from_cache_or_fallback(
            bot_instance.organization_id, bot_instance.stripe_subscription_id
        )

        # Calculate current month
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        # Organize data by month/year and sum up totals
        monthly_totals = {}
        for record in usage_data:
            month = record.get("month")
            year = record.get("year")
            answer_count = record.get("answer_count", 0) or 0

            if month and year:
                month_key = f"{year}-{month:02d}"
                if month_key not in monthly_totals:
                    monthly_totals[month_key] = 0
                monthly_totals[month_key] += answer_count

        # Generate last 12 months of data (including current month)
        months_data = []
        for i in range(11, -1, -1):  # 12 months back to current
            target_date = now.replace(day=1) - relativedelta(months=i)
            month_key = f"{target_date.year}-{target_date.month:02d}"
            month_name = target_date.strftime("%b %Y")

            answer_count = monthly_totals.get(month_key, 0)
            months_data.append(
                {
                    "month": month_name,
                    "month_key": month_key,
                    "answer_count": answer_count,
                    "is_current": (
                        target_date.month == current_month and target_date.year == current_year
                    ),
                }
            )

        # Find the first month with non-zero usage
        first_usage_index = None
        for i, month in enumerate(months_data):
            if month["answer_count"] > 0:
                first_usage_index = i
                break

        # If we found usage, trim to include one month before first usage (if available)
        if first_usage_index is not None:
            start_index = max(0, first_usage_index - 1)  # Include one month before first usage
            months_data = months_data[start_index:]
        else:
            # No usage - set up 0 data points for the current and previous month
            prev_month_year = current_year - 1 if current_month == 1 else current_year
            prev_month_month = 12 if current_month == 1 else current_month - 1
            months_data = [
                {
                    "month": f"{prev_month_year}-{prev_month_month:02d}",
                    "month_key": f"{prev_month_year}-{prev_month_month:02d}",
                    "answer_count": 0,
                    "is_current": False,
                },
                {
                    "month": f"{current_year}-{current_month:02d}",
                    "month_key": f"{current_year}-{current_month:02d}",
                    "answer_count": 0,
                    "is_current": True,
                },
            ]

        return web.json_response(
            {
                "months": months_data,
                "current_month": f"{current_year}-{current_month:02d}",
                "plan_limit": plan_limit.base_num_answers,
            }
        )

    return usage_history_handler


def create_current_month_usage_handler(bot_server: CompassBotServer):
    """Create current month usage API handler."""

    async def current_month_usage_handler(request: web.Request) -> web.Response:
        """Handle current month usage API requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)
        bot_instance = bot.bot_config

        # Get organization ID
        if not bot_instance or not bot_instance.organization_id:
            return web.json_response({"error": "No organization ID available"}, status=404)

        organization_id = bot_instance.organization_id
        analytics_store = bot.analytics_store

        # Get current month usage data using helper function
        from csbot.slackbot.webapp.billing.billing import get_organization_current_month_usage

        usage_data = await get_organization_current_month_usage(analytics_store, organization_id)

        return web.json_response(usage_data)

    return current_month_usage_handler


def create_plan_limits_handler(bot_server: CompassBotServer):
    """Create plan limits API handler."""

    async def plan_limits_handler(request: web.Request) -> web.Response:
        """Handle plan limits API requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)
        bot_instance = bot.bot_config

        # Get organization ID
        if not bot_instance or not bot_instance.organization_id:
            return web.json_response({"error": "No organization ID available"}, status=404)

        # Get subscription ID
        if not bot_instance.stripe_subscription_id:
            # No subscription means free plan - return free plan limits
            return web.json_response(
                {
                    "plan_limit": None,
                    "has_overage_available": False,
                    "bonus_answers_earned": 0,
                    "bonus_answers_used": 0,
                    "bonus_answers_remaining": 0,
                }
            )

        organization_id = bot_instance.organization_id
        analytics_store = bot.analytics_store

        # Get plan limits from cache or fallback
        plan_limits = await bot_server.get_plan_limits_from_cache_or_fallback(
            organization_id, bot_instance.stripe_subscription_id
        )

        # Get bonus answer data
        bonus_answers_earned = await analytics_store.get_organization_bonus_answer_grants(
            organization_id
        )
        bonus_answers_used = await analytics_store.get_organization_bonus_answers_consumed(
            organization_id
        )
        bonus_answers_remaining = max(0, bonus_answers_earned - bonus_answers_used)

        return web.json_response(
            {
                "plan_limit": plan_limits.base_num_answers,
                "has_overage_available": plan_limits.allow_overage,
                "bonus_answers_earned": bonus_answers_earned,
                "bonus_answers_used": bonus_answers_used,
                "bonus_answers_remaining": bonus_answers_remaining,
            }
        )

    return plan_limits_handler


def create_plan_switch_handler(bot_server: CompassBotServer):
    """Create plan switching API handler."""

    async def plan_switch_handler(request: web.Request) -> web.Response:
        """Handle plan switching requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)
        bot_instance = bot.bot_config

        # Check if Stripe client is available
        if not bot_server.stripe_client:
            return web.json_response({"error": "Billing system not available"}, status=503)

        try:
            # Parse request body
            body = await request.json()
            target_plan = body.get("plan_name")

            if not target_plan or not isinstance(target_plan, str):
                return web.json_response({"error": "Invalid plan name"}, status=400)

            # Find the target plan configuration
            target_plan_config = None
            for plan in get_plan_config(bot_server):
                plan_name = plan.get("name")
                if isinstance(plan_name, str) and plan_name.lower() == target_plan.lower():
                    target_plan_config = plan
                    break

            if not target_plan_config:
                return web.json_response({"error": "Plan not found"}, status=404)

            # Check if bot manager is available
            if not (hasattr(bot_server, "bot_manager") and bot_server.bot_manager):
                return web.json_response({"error": "Bot manager not available"}, status=503)

            # Check if user has payment methods (not required for Free plan)
            payment_methods = await asyncio.to_thread(
                bot_server.stripe_client.get_customer_payment_methods, stripe_customer_id
            )
            if not payment_methods and target_plan.lower() != "free":
                return web.json_response(
                    {"error": "Please add a payment method before switching plans"}, status=400
                )

            # Get target product ID
            target_product_id = target_plan_config.get("product_id")
            if not target_product_id or not isinstance(target_product_id, str):
                return web.json_response(
                    {"error": "Plan not available for subscription"}, status=400
                )

            existing_subscription_id = bot_instance.stripe_subscription_id

            # Use the shared subscription switching logic
            try:
                result = await switch_subscription_to_product(
                    stripe_customer_id=stripe_customer_id,
                    target_product_id=target_product_id,
                    organization_id=bot_instance.organization_id,
                    existing_subscription_id=existing_subscription_id,
                    bot_server=bot_server,
                )

                subscription_id = result["subscription_id"]
                action = result["action"]  # "updated" or "created"

                # Log plan upgrade/downgrade analytics event (with timeout for performance)
                from csbot.slackbot.slackbot_analytics import AnalyticsEventType

                try:
                    await asyncio.wait_for(
                        bot._log_analytics_event_with_context(
                            event_type=AnalyticsEventType.PLAN_UPGRADED
                            if target_plan.lower() != "free"
                            else AnalyticsEventType.PLAN_DOWNGRADED,
                            channel_id=None,
                            user_id=None,
                            metadata={
                                "old_plan": "unknown",  # Could be enhanced to track previous plan
                                "new_plan": target_plan,
                                "subscription_id": subscription_id,
                                "product_id": target_product_id,
                                "action": action,
                            },
                            send_to_segment=True,
                        ),
                        timeout=0.5,  # 500ms timeout - analytics should complete quickly
                    )
                except TimeoutError:
                    # Analytics timed out, but that's OK - main operation succeeded
                    pass
                except Exception:
                    # Analytics failed, but that's OK - main operation succeeded
                    pass

                message = (
                    f"Successfully switched to {target_plan} plan"
                    if action == "updated"
                    else f"Successfully subscribed to {target_plan} plan"
                )
                return web.json_response(
                    {
                        "success": True,
                        "message": message,
                        "subscription_id": subscription_id,
                    }
                )

            except Exception as e:
                # Log billing issue analytics event (fire-and-forget for performance)
                from csbot.slackbot.slackbot_analytics import AnalyticsEventType

                try:
                    asyncio.create_task(
                        bot._log_analytics_event_with_context(
                            event_type=AnalyticsEventType.BILLING_ISSUE,
                            channel_id=None,
                            user_id=None,
                            metadata={
                                "error_type": "plan_switch_failed",
                                "error_message": str(e),
                                "target_plan": target_plan,
                                "product_id": target_product_id,
                            },
                            send_to_segment=True,
                        )
                    )
                except Exception:
                    # Don't let analytics logging break the error response
                    pass

                return web.json_response({"error": "Failed to switch plan"}, status=500)

        except Exception as e:
            bot_server.logger.error(f"Unexpected error in plan switch: {e}", exc_info=True)
            return web.json_response({"error": "An unexpected error occurred"}, status=500)

    return plan_switch_handler


def create_setup_intent_handler(bot_server: CompassBotServer):
    """Create setup intent API handler for adding payment methods."""

    async def setup_intent_handler(request: web.Request) -> web.Response:
        """Handle setup intent creation requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)

        # Check if Stripe client is available
        if not bot_server.stripe_client:
            return web.json_response({"error": "Billing system not available"}, status=503)

        try:
            # Create setup intent
            setup_intent = await asyncio.to_thread(
                bot_server.stripe_client.create_setup_intent, stripe_customer_id
            )

            return web.json_response(
                {
                    "success": True,
                    "client_secret": setup_intent.get("client_secret"),
                    "setup_intent_id": setup_intent.get("id"),
                }
            )

        except Exception as e:
            bot_server.logger.error(f"Failed to create setup intent: {e}", exc_info=True)
            return web.json_response({"error": "Failed to create setup intent"}, status=500)

    return setup_intent_handler


def create_delete_payment_method_handler(bot_server: CompassBotServer):
    """Create payment method deletion API handler."""

    async def delete_payment_method_handler(request: web.Request) -> web.Response:
        """Handle payment method deletion requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)

        # Check if Stripe client is available
        if not bot_server.stripe_client:
            return web.json_response({"error": "Billing system not available"}, status=503)

        try:
            payment_method_id = request.match_info.get("payment_method_id")
            if not payment_method_id:
                return web.json_response({"error": "Payment method ID is required"}, status=400)

            # Verify the payment method belongs to this customer before deleting
            payment_methods = await asyncio.to_thread(
                bot_server.stripe_client.get_customer_payment_methods, stripe_customer_id
            )
            payment_method_exists = any(pm.get("id") == payment_method_id for pm in payment_methods)

            if not payment_method_exists:
                return web.json_response(
                    {"error": "Payment method not found or not associated with this account"},
                    status=404,
                )

            # Detach the payment method
            detached_pm = await asyncio.to_thread(
                bot_server.stripe_client.detach_payment_method, payment_method_id
            )

            return web.json_response(
                {
                    "success": True,
                    "message": "Payment method removed successfully",
                    "payment_method_id": detached_pm.get("id"),
                }
            )

        except Exception as e:
            bot_server.logger.error(f"Failed to remove payment method: {e}", exc_info=True)
            return web.json_response({"error": "Failed to remove payment method"}, status=500)

    return delete_payment_method_handler


def create_update_customer_handler(bot_server: CompassBotServer):
    """Create customer details update API handler."""

    async def update_customer_handler(request: web.Request) -> web.Response:
        """Handle customer details update requests."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)

        # Check if Stripe client is available
        if not bot_server.stripe_client:
            return web.json_response({"error": "Billing system not available"}, status=503)

        try:
            # Parse request body
            body = await request.json()

            # Prepare update data - only allow email field
            update_data = {}

            if "email" in body and body["email"]:
                update_data["email"] = body["email"]

            if not update_data:
                return web.json_response({"error": "No valid fields to update"}, status=400)

            # Update customer in Stripe
            updated_customer = await asyncio.to_thread(
                bot_server.stripe_client.update_customer, stripe_customer_id, **update_data
            )

            return web.json_response(
                {
                    "success": True,
                    "message": "Customer details updated successfully",
                    "customer": {
                        "id": updated_customer.get("id"),
                        "email": updated_customer.get("email"),
                    },
                }
            )

        except Exception as e:
            bot_server.logger.error(f"Failed to update customer details: {e}", exc_info=True)
            return web.json_response({"error": "Failed to update customer details"}, status=500)

    return update_customer_handler


def create_confirm_payment_method_handler(bot_server: CompassBotServer):
    """Create handler to confirm payment method setup and set as default."""

    async def confirm_payment_method_handler(request: web.Request) -> web.Response:
        """Handle payment method confirmation and set as default."""

        # Validate billing access and get bot with Stripe customer ID
        bot, stripe_customer_id = await get_validated_billing_bot(bot_server, request)

        # Check if Stripe client is available
        if not bot_server.stripe_client:
            return web.json_response({"error": "Billing system not available"}, status=503)

        try:
            # Parse request body
            body = await request.json()
            setup_intent_id = body.get("setup_intent_id")
            old_payment_method_id = body.get("old_payment_method_id")  # Optional, for updates

            if not setup_intent_id:
                return web.json_response({"error": "Setup intent ID is required"}, status=400)

            # Import stripe here to access the Stripe API directly
            import stripe

            # Retrieve the setup intent to get the payment method
            setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)

            if setup_intent.status != "succeeded":
                return web.json_response({"error": "Setup intent has not succeeded"}, status=400)

            # Extract payment method ID - handle both string ID and expandable object
            payment_method = setup_intent.payment_method
            if not payment_method:
                return web.json_response(
                    {"error": "No payment method found in setup intent"}, status=400
                )

            # Convert to string if it's an expandable object
            if isinstance(payment_method, str):
                payment_method_id = payment_method
            else:
                payment_method_id = payment_method.id

            # Set the new payment method as default
            updated_customer = await asyncio.to_thread(
                bot_server.stripe_client.set_default_payment_method,
                stripe_customer_id,
                payment_method_id,
            )

            # If this is an update (old payment method provided), remove the old one
            old_payment_method_removed = False
            if old_payment_method_id:
                try:
                    await asyncio.to_thread(
                        bot_server.stripe_client.detach_payment_method, old_payment_method_id
                    )
                    old_payment_method_removed = True
                except Exception:
                    # Log warning but continue - the new payment method was added successfully
                    pass

            # Log payment method added analytics event (with timeout for performance)
            from csbot.slackbot.slackbot_analytics import AnalyticsEventType

            try:
                await asyncio.wait_for(
                    bot._log_analytics_event_with_context(
                        event_type=AnalyticsEventType.PAYMENT_METHOD_ADDED,
                        channel_id=None,
                        user_id=None,
                        metadata={
                            "payment_method_id": payment_method_id,
                            "customer_id": updated_customer.get("id"),
                            "is_update": old_payment_method_id is not None,
                            "old_payment_method_removed": old_payment_method_removed,
                        },
                        send_to_segment=True,
                    ),
                    timeout=0.5,  # 500ms timeout - analytics should complete quickly
                )
            except TimeoutError:
                # Analytics timed out, but that's OK - main operation succeeded
                pass
            except Exception:
                # Analytics failed, but that's OK - main operation succeeded
                pass

            return web.json_response(
                {
                    "success": True,
                    "message": "Payment method confirmed and set as default",
                    "payment_method_id": payment_method_id,
                    "customer_id": updated_customer.get("id"),
                    "old_payment_method_removed": old_payment_method_removed,
                }
            )

        except Exception as e:
            bot_server.logger.error(f"Failed to confirm payment method: {e}", exc_info=True)
            return web.json_response({"error": "Failed to confirm payment method"}, status=500)

    return confirm_payment_method_handler
