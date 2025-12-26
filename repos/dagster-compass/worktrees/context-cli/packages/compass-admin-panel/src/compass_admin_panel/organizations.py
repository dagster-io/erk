"""Organization management for Compass Admin Panel - API only."""

import asyncio
from typing import Any

from aiohttp import web
from csbot.slackbot.webapp.billing.routes import switch_subscription_to_product


def _get_plan_info(subscription_id: str | None, context: Any) -> dict[str, Any] | None:
    """Get plan type and limits by querying Stripe API for subscription and product details.

    Returns None if any step fails - no fallbacks or defaults.
    """
    if not subscription_id or not context.has_stripe_config or not context.stripe_client:
        return None

    stripe_config = context.stripe_config

    # Map product IDs to plan type names (limits will come from Stripe product metadata)
    plan_type_mappings = {
        stripe_config.free_product_id: "Free",
        stripe_config.starter_product_id: "Starter",
        stripe_config.team_product_id: "Team",
    }

    # Add design partner product if available
    if (
        hasattr(stripe_config, "design_partner_product_id")
        and stripe_config.design_partner_product_id
    ):
        plan_type_mappings[stripe_config.design_partner_product_id] = "Design Partner"

    try:
        # Get the subscription details from Stripe
        subscription_details = context.stripe_client.get_subscription_details(subscription_id)

        # Get the product ID from the subscription
        if "items" in subscription_details and len(subscription_details["items"]["data"]) > 0:
            product_id = subscription_details["items"]["data"][0]["price"]["product"]

            # Get the plan type from our mapping
            plan_type = plan_type_mappings.get(product_id)
            if not plan_type:
                print(f"Unknown product ID: {product_id}")
                return None

            # Get plan limits from Stripe product metadata
            plan_limits = context.stripe_client.get_product_plan_limits(product_id)
            if not plan_limits.base_num_answers:
                print(f"No base_num_answers found for product {product_id}")
                return None

            return {"plan_type": plan_type, "plan_limit": plan_limits.base_num_answers}
    except Exception as e:
        print(f"Error querying Stripe API for subscription {subscription_id}: {e}")

    return None


async def get_plan_types(request: web.Request) -> web.Response:
    """Get plan types for specific organizations asynchronously.

    Legacy endpoint - kept for backwards compatibility.
    New code should use /api/plan-types from api_routes.py
    """
    try:
        # Check if context is available
        if "context" not in request.app:
            return web.json_response({"error": "Admin panel not properly configured"}, status=500)

        context = request.app["context"]
        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get organization IDs from query parameter
        org_ids_param = request.query.get("org_ids", "")
        if not org_ids_param:
            return web.json_response({"error": "No organization IDs provided"}, status=400)

        try:
            org_ids = [int(id.strip()) for id in org_ids_param.split(",") if id.strip()]
        except ValueError:
            return web.json_response({"error": "Invalid organization ID format"}, status=400)

        if not org_ids:
            return web.json_response({"plan_types": {}})

        # Get organizations from storage for the specified IDs
        from datetime import datetime

        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year

        # Get all organizations first, then filter by the requested IDs
        all_organizations_data = await asyncio.to_thread(
            context.storage.list_organizations_with_usage_data, current_month, current_year
        )

        # Filter to only the organizations we need
        organizations_data = [
            org for org in all_organizations_data if org.organization_id in org_ids
        ]

        # Create tasks for concurrent plan info fetching
        async def fetch_plan_info_for_org(org):
            if org.stripe_subscription_id:
                plan_info = await asyncio.to_thread(
                    _get_plan_info, org.stripe_subscription_id, context
                )
                if plan_info:
                    return str(org.organization_id), {
                        "plan_type": plan_info["plan_type"],
                        "plan_limit": plan_info["plan_limit"],
                        "usage_over_limit": org.current_usage > plan_info["plan_limit"],
                    }
                else:
                    # Default for organizations without valid plan info
                    return str(org.organization_id), {
                        "plan_type": "unknown",
                        "plan_limit": 0,
                        "usage_over_limit": False,
                    }
            else:
                # Free plan (no subscription)
                return str(org.organization_id), {
                    "plan_type": "free",
                    "plan_limit": 50,  # Default free limit
                    "usage_over_limit": org.current_usage > 50,
                }

        # Execute all plan info fetches concurrently
        tasks = [fetch_plan_info_for_org(org) for org in organizations_data]
        results = await asyncio.gather(*tasks)

        # Convert results to dictionary
        plan_types = dict(results)

        return web.json_response({"plan_types": plan_types})

    except Exception as e:
        print(f"Error loading plan types: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load plan types: {str(e)}"}, status=500)


async def _validate_and_extract_conversion_request(
    request: web.Request,
) -> tuple[web.Response | None, dict[str, Any] | None]:
    """
    Validate request and extract common parameters for plan conversion.

    Returns:
        Tuple of (error_response, extracted_data)
        If error_response is not None, return it immediately.
        Otherwise, use extracted_data for conversion.
    """
    # Parse request body
    try:
        body = await request.json()
    except ValueError as e:
        return web.json_response({"error": f"Invalid JSON: {str(e)}"}, status=400), None

    organization_id = body.get("organization_id")
    stripe_customer_id = body.get("stripe_customer_id")
    existing_subscription_id = body.get("stripe_subscription_id")  # Optional

    # Validate required fields
    if not organization_id or not stripe_customer_id:
        return web.json_response(
            {"error": "Missing organization_id or stripe_customer_id"}, status=400
        ), None

    # Validate types
    if not isinstance(organization_id, int):
        return web.json_response({"error": "organization_id must be an integer"}, status=400), None

    if not isinstance(stripe_customer_id, str):
        return web.json_response({"error": "stripe_customer_id must be a string"}, status=400), None

    # Check context availability
    if "context" not in request.app:
        return web.json_response({"error": "Admin panel not properly configured"}, status=500), None

    context = request.app["context"]

    if not context.config:
        return web.json_response({"error": "Admin panel not properly configured"}, status=500), None

    if not context.stripe_client:
        return web.json_response({"error": "Stripe client not available"}, status=500), None

    return None, {
        "organization_id": organization_id,
        "stripe_customer_id": stripe_customer_id,
        "existing_subscription_id": existing_subscription_id,
        "context": context,
    }


async def convert_to_design_partner(request: web.Request) -> web.Response:
    """Convert an organization to Design Partner plan."""
    try:
        # Validate and extract request data
        error_response, data = await _validate_and_extract_conversion_request(request)
        if error_response:
            return error_response

        context = data["context"]
        config = context.config

        # Check if design_partner_product_id is configured
        if (
            not hasattr(config.stripe, "design_partner_product_id")
            or not config.stripe.design_partner_product_id
        ):
            return web.json_response(
                {"error": "Design Partner product not configured in staging config"}, status=500
            )

        print(f"Converting organization {data['organization_id']} to Design Partner plan")

        # Use the shared subscription switching logic
        result = await switch_subscription_to_product(
            stripe_customer_id=data["stripe_customer_id"],
            target_product_id=config.stripe.design_partner_product_id,
            organization_id=data["organization_id"],
            existing_subscription_id=data["existing_subscription_id"],
            stripe_client=context.stripe_client,
            storage=context.storage,
        )

        return web.json_response(
            {
                "success": True,
                "message": "Successfully converted organization to Design Partner plan",
                "subscription_id": result["subscription_id"],
            }
        )

    except Exception as e:
        print(f"Error in convert_to_design_partner: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to convert organization: {str(e)}"}, status=500)


async def convert_to_free_plan(request: web.Request) -> web.Response:
    """Convert an organization to free plan."""
    try:
        # Validate and extract request data
        error_response, data = await _validate_and_extract_conversion_request(request)
        if error_response:
            return error_response

        context = data["context"]
        config = context.config

        # Check if free_product_id is configured
        if not hasattr(config.stripe, "free_product_id") or not config.stripe.free_product_id:
            return web.json_response(
                {"error": "Free product not configured in staging config"}, status=500
            )

        print(f"Converting organization {data['organization_id']} to Free plan")

        # Use the shared subscription switching logic
        result = await switch_subscription_to_product(
            stripe_customer_id=data["stripe_customer_id"],
            target_product_id=config.stripe.free_product_id,
            organization_id=data["organization_id"],
            existing_subscription_id=data["existing_subscription_id"],
            stripe_client=context.stripe_client,
            storage=context.storage,
        )

        return web.json_response(
            {
                "success": True,
                "message": "Successfully converted organization to Free plan",
                "subscription_id": result["subscription_id"],
            }
        )

    except Exception as e:
        print(f"Error in convert_to_free_plan: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to convert organization: {str(e)}"}, status=500)


async def convert_to_starter_plan(request: web.Request) -> web.Response:
    """Convert an organization to Starter plan."""
    try:
        # Validate and extract request data
        error_response, data = await _validate_and_extract_conversion_request(request)
        if error_response:
            return error_response

        context = data["context"]
        config = context.config

        # Check if starter_product_id is configured
        if not hasattr(config.stripe, "starter_product_id") or not config.stripe.starter_product_id:
            return web.json_response(
                {"error": "Starter product not configured in staging config"}, status=500
            )

        print(f"Converting organization {data['organization_id']} to Starter plan")

        # Use the shared subscription switching logic
        result = await switch_subscription_to_product(
            stripe_customer_id=data["stripe_customer_id"],
            target_product_id=config.stripe.starter_product_id,
            organization_id=data["organization_id"],
            existing_subscription_id=data["existing_subscription_id"],
            stripe_client=context.stripe_client,
            storage=context.storage,
        )

        return web.json_response(
            {
                "success": True,
                "message": "Successfully converted organization to Starter plan",
                "subscription_id": result["subscription_id"],
            }
        )

    except Exception as e:
        print(f"Error in convert_to_starter_plan: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to convert organization: {str(e)}"}, status=500)


async def convert_to_team_plan(request: web.Request) -> web.Response:
    """Convert an organization to Team plan."""
    try:
        # Validate and extract request data
        error_response, data = await _validate_and_extract_conversion_request(request)
        if error_response:
            return error_response

        context = data["context"]
        config = context.config

        # Check if team_product_id is configured
        if not hasattr(config.stripe, "team_product_id") or not config.stripe.team_product_id:
            return web.json_response(
                {"error": "Team product not configured in staging config"}, status=500
            )

        print(f"Converting organization {data['organization_id']} to Team plan")

        # Use the shared subscription switching logic
        result = await switch_subscription_to_product(
            stripe_customer_id=data["stripe_customer_id"],
            target_product_id=config.stripe.team_product_id,
            organization_id=data["organization_id"],
            existing_subscription_id=data["existing_subscription_id"],
            stripe_client=context.stripe_client,
            storage=context.storage,
        )

        return web.json_response(
            {
                "success": True,
                "message": "Successfully converted organization to Team plan",
                "subscription_id": result["subscription_id"],
            }
        )

    except Exception as e:
        print(f"Error in convert_to_team_plan: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to convert organization: {str(e)}"}, status=500)
