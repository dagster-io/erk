"""JSON API routes for Compass Admin Panel React frontend."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from aiohttp import web
from csbot.slackbot.storage.interface import SlackbotStorage
from csbot.slackbot.storage.onboarding_state import OnboardingStep
from csbot.slackbot.storage.utils import is_postgresql
from csbot.slackbot.webapp.referral.utils import (
    is_valid_promo_token,
    is_valid_uuid_token,
)

from compass_admin_panel.organizations import (
    _get_plan_info,
)
from compass_admin_panel.types import ThreadData

if TYPE_CHECKING:
    from compass_admin_panel.types import AdminPanelContext


async def list_organizations_api(request: web.Request) -> web.Response:
    """Get organizations with usage data (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get pagination parameters
        page = int(request.query.get("page", "1"))
        limit = int(request.query.get("limit", "25"))

        # Ensure valid pagination
        page = max(1, page)
        limit = max(1, min(limit, 200))

        # Get current month/year
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year

        # Calculate offset
        offset = (page - 1) * limit

        # Get total count first
        all_organizations_data = await asyncio.to_thread(
            context.storage.list_organizations_with_usage_data, current_month, current_year
        )
        total_count = len(all_organizations_data)

        # Get paginated results
        organizations_data = await asyncio.to_thread(
            context.storage.list_organizations_with_usage_data,
            current_month,
            current_year,
            limit,
            offset,
        )

        organizations = [
            {
                "id": org.organization_id,
                "name": org.organization_name,
                "industry": org.organization_industry,
                "stripe_customer_id": org.stripe_customer_id,
                "stripe_subscription_id": org.stripe_subscription_id,
                "bot_count": org.bot_count,
                "current_usage": org.current_usage,
                "bonus_answers": org.bonus_answers,
            }
            for org in organizations_data
        ]

        return web.json_response(
            {"organizations": organizations, "total": total_count, "page": page, "limit": limit}
        )

    except Exception as e:
        print(f"Error in list_organizations_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load organizations: {str(e)}"}, status=500)


async def get_plan_types_api(request: web.Request) -> web.Response:
    """Get plan types for specific organizations (JSON API).

    Returns list format for easier frontend processing.
    """
    try:
        context: AdminPanelContext = request.app["context"]

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
            return web.json_response([])

        # Get organizations from storage
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year

        all_organizations_data = await asyncio.to_thread(
            context.storage.list_organizations_with_usage_data, current_month, current_year
        )

        # Filter to only the organizations we need
        organizations_data = [
            org for org in all_organizations_data if org.organization_id in org_ids
        ]

        # Create tasks for concurrent plan info fetching
        async def fetch_plan_info_for_org(org):
            plan_type = "Unknown"
            plan_limits = None

            if org.stripe_subscription_id:
                plan_info = await asyncio.to_thread(
                    _get_plan_info, org.stripe_subscription_id, context
                )
                if plan_info:
                    plan_type = plan_info["plan_type"]
                    # Get detailed limits from Stripe
                    if context.stripe_client:
                        try:
                            subscription_details = await asyncio.to_thread(
                                context.stripe_client.get_subscription_details,
                                org.stripe_subscription_id,
                            )
                            if (
                                "items" in subscription_details
                                and len(subscription_details["items"]["data"]) > 0
                            ):
                                product_id = subscription_details["items"]["data"][0]["price"][
                                    "product"
                                ]
                                limits = await asyncio.to_thread(
                                    context.stripe_client.get_product_plan_limits, product_id
                                )
                                plan_limits = {
                                    "base_num_answers": limits.base_num_answers,
                                    "allow_overage": limits.allow_overage,
                                    "num_channels": limits.num_channels,
                                    "allow_additional_channels": limits.allow_additional_channels,
                                }
                        except Exception as e:
                            print(f"Error fetching plan limits for org {org.organization_id}: {e}")
            else:
                # Free plan (no subscription)
                plan_type = "Free"

            return {
                "organization_id": org.organization_id,
                "plan_type": plan_type,
                "plan_limits": plan_limits,
            }

        # Execute all plan info fetches concurrently
        tasks = [fetch_plan_info_for_org(org) for org in organizations_data]
        results = await asyncio.gather(*tasks)

        return web.json_response(results)

    except Exception as e:
        print(f"Error in get_plan_types_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load plan types: {str(e)}"}, status=500)


async def list_tokens_api(request: web.Request) -> web.Response:
    """Get all invite tokens (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get tokens from storage
        tokens_data = await context.storage.list_invite_tokens()

        tokens = [
            {
                "id": token.id,
                "token": token.token,
                "created_at": token.created_at,
                "consumed_at": token.consumed_at,
                "is_single_use": token.is_single_use,
                "consumer_bonus_answers": token.consumer_bonus_answers,
                "consumed_by_organization_ids": token.consumed_by_organization_ids,
                "organization_name": token.organization_name,
                "organization_id": token.organization_id,
            }
            for token in tokens_data
        ]

        return web.json_response({"tokens": tokens})

    except Exception as e:
        print(f"Error in list_tokens_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load tokens: {str(e)}"}, status=500)


async def create_token_api(request: web.Request) -> web.Response:
    """Create a new invite token (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Parse JSON body
        try:
            body = await request.json()
        except ValueError as e:
            return web.json_response({"error": f"Invalid JSON: {str(e)}"}, status=400)

        # Get token from body or generate UUID
        token = body.get("token", "").strip()
        if not token:
            token = str(uuid.uuid4())

        # Validate token format
        if not (is_valid_uuid_token(token) or is_valid_promo_token(token)):
            return web.json_response(
                {
                    "error": "Invalid token format. Must be UUID or uppercase alphanumeric (max 20 chars)"
                },
                status=400,
            )

        # Get parameters
        is_single_use = body.get("is_single_use", False)
        consumer_bonus_answers = body.get("consumer_bonus_answers", 150)

        # Create token
        def _create_token_sync(
            storage: SlackbotStorage, token: str, is_single_use: bool, bonus_answers: int
        ):
            storage.create_invite_token(
                token, is_single_use=is_single_use, consumer_bonus_answers=bonus_answers
            )

        await asyncio.get_event_loop().run_in_executor(
            None, _create_token_sync, context.storage, token, is_single_use, consumer_bonus_answers
        )

        return web.json_response({"success": True, "token": token})

    except Exception as e:
        print(f"Error in create_token_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to create token: {str(e)}"}, status=500)


async def list_onboarding_states_api(request: web.Request) -> web.Response:
    """Get onboarding states for all organizations (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        limit = int(request.query.get("limit", "100"))

        # Get onboarding states
        onboarding_states = await context.storage.list_onboarding_states(limit=limit)

        states = []
        for state in onboarding_states:
            # Map steps to dict format
            initial_setup_steps = {}
            usage_milestones = {}
            error_events = {}

            for step in OnboardingStep.all_steps():
                step_completed = step in state.completed_steps
                step_data = {
                    "completed": step_completed,
                    "completed_at": str(state.completed_at)
                    if step == OnboardingStep.COMPLETED and step_completed
                    else None,
                }
                initial_setup_steps[step.value] = step_data

            # Calculate setup status
            completed_steps = len([s for s in initial_setup_steps.values() if s["completed"]])
            total_steps = len(initial_setup_steps)

            if state.error_message:
                setup_status = "Error"
            elif completed_steps == total_steps:
                setup_status = "Complete"
            else:
                setup_status = "Incomplete"

            states.append(
                {
                    "organization_id": state.organization_id,
                    "organization_name": state.organization_name,
                    "setup_status": setup_status,
                    "initial_setup_steps": initial_setup_steps,
                    "usage_milestones": usage_milestones,  # Loaded separately
                    "error_events": error_events,  # Loaded separately
                }
            )

        return web.json_response({"states": states})

    except Exception as e:
        print(f"Error in list_onboarding_states_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response(
            {"error": f"Failed to load onboarding states: {str(e)}"}, status=500
        )


async def get_onboarding_details_api(request: web.Request) -> web.Response:
    """Get detailed analytics for an organization's onboarding (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get organization_id from path parameter
        org_id = request.match_info.get("org_id")
        if not org_id:
            return web.json_response({"error": "Missing organization_id"}, status=400)

        try:
            org_id_int = int(org_id)
        except ValueError:
            return web.json_response({"error": "Invalid organization_id"}, status=400)

        # Get analytics summary stats
        analytics_events, total_count, _ = await context.storage.get_analytics_for_organization(
            org_id_int, limit=1000, offset=0
        )

        event_types = list(
            {event.get("event_type") for event in analytics_events if event.get("event_type")}
        )
        first_event = analytics_events[-1].get("created_at") if analytics_events else None
        last_event = analytics_events[0].get("created_at") if analytics_events else None

        return web.json_response(
            {
                "analytics_summary": {
                    "total_events": total_count,
                    "event_types": event_types,
                    "first_event": first_event,
                    "last_event": last_event,
                }
            }
        )

    except Exception as e:
        print(f"Error in get_onboarding_details_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response(
            {"error": f"Failed to load onboarding details: {str(e)}"}, status=500
        )


async def list_analytics_api(request: web.Request) -> web.Response:
    """Get analytics events for an organization (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get parameters
        try:
            organization_id = int(request.query.get("organization_id", "0"))
        except ValueError:
            return web.json_response({"error": "Invalid organization_id"}, status=400)

        if organization_id == 0:
            return web.json_response({"error": "organization_id is required"}, status=400)

        page = int(request.query.get("page", "1"))
        limit = int(request.query.get("limit", "50"))

        # Ensure valid pagination
        page = max(1, page)
        limit = max(1, min(limit, 200))

        # Calculate offset
        offset = (page - 1) * limit

        # Get analytics events
        analytics_events, total_count, _ = await context.storage.get_analytics_for_organization(
            organization_id, limit=limit, offset=offset
        )

        events = [
            {
                "id": event.get("id"),
                "organization_id": organization_id,
                "event_type": event.get("event_type"),
                "event_timestamp": event.get("created_at"),
                "metadata": event.get("metadata"),
                "user_id": event.get("user_id"),
                "channel_id": event.get("channel_id"),
            }
            for event in analytics_events
        ]

        return web.json_response(
            {
                "events": events,
                "organization_id": organization_id,
                "total": total_count,
                "page": page,
                "limit": limit,
            }
        )

    except Exception as e:
        print(f"Error in list_analytics_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load analytics: {str(e)}"}, status=500)


async def search_organizations_api(request: web.Request) -> web.Response:
    """Search organizations by name (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get search query
        query = request.query.get("q", "").strip()
        if len(query) < 2:
            return web.json_response({"error": "Query must be at least 2 characters"}, status=400)

        limit = int(request.query.get("limit", "10"))
        limit = max(1, min(limit, 50))  # Between 1 and 50

        # Get current month/year for usage data
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year

        # Fetch all organizations
        all_orgs = await asyncio.to_thread(
            context.storage.list_organizations_with_usage_data, current_month, current_year
        )

        # Filter by name (case-insensitive)
        query_lower = query.lower()
        matching_orgs = [org for org in all_orgs if query_lower in org.organization_name.lower()]

        # Limit results for autocomplete
        limited_results = matching_orgs[:limit]

        organizations = [
            {
                "id": org.organization_id,
                "name": org.organization_name,
                "industry": org.organization_industry,
                "stripe_customer_id": org.stripe_customer_id,
                "stripe_subscription_id": org.stripe_subscription_id,
                "bot_count": org.bot_count,
                "current_usage": org.current_usage,
                "bonus_answers": org.bonus_answers,
            }
            for org in limited_results
        ]

        return web.json_response(
            {"organizations": organizations, "total_matches": len(matching_orgs), "query": query}
        )

    except Exception as e:
        print(f"Error in search_organizations_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to search organizations: {str(e)}"}, status=500)


async def get_thread_detail_api(request: web.Request) -> web.Response:
    """Get thread detail HTML for viewing (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get path parameters
        team_id = request.match_info.get("team_id")
        channel_id = request.match_info.get("channel_id")
        thread_ts = request.match_info.get("thread_ts")

        if not team_id or not channel_id or not thread_ts:
            return web.json_response({"error": "Missing required parameters"}, status=400)

        # Get bot_id from query parameter (if provided)
        bot_id = request.query.get("bot_id")

        # If bot_id not provided, we need to find it by looking up bot instances for this team
        if not bot_id:

            def _find_bot_id(storage: SlackbotStorage, team_id: str, channel_id: str) -> str | None:
                conn_factory = storage._sql_conn_factory  # type: ignore[attr-defined]
                with conn_factory.with_conn() as conn:
                    cursor = conn.cursor()
                    placeholder = "%s" if is_postgresql(conn) else "?"

                    # Try to find a bot instance with this team_id that has threads in this channel
                    cursor.execute(
                        f"SELECT slack_team_id, channel_name FROM bot_instances WHERE slack_team_id = {placeholder}",
                        (team_id,),
                    )
                    rows = cursor.fetchall()

                    # Check each potential bot_id to see if it has this thread
                    for row in rows:
                        potential_bot_id = f"{row[0]}-{row[1]}"
                        # We'll return the first one and let the thread lookup determine if it exists
                        return potential_bot_id

                    return None

            bot_id = await asyncio.to_thread(_find_bot_id, context.storage, team_id, channel_id)

        if not bot_id:
            return web.json_response(
                {"error": "Could not find bot instance for this thread"}, status=404
            )

        # Get the thread HTML
        instance_storage = context.storage.for_instance(bot_id)
        thread_key = f"{channel_id}:{thread_ts}"

        # Try to get HTML first
        html = await instance_storage.get("slack_thread_html", thread_key)

        # If no HTML, get events and format them
        if not html:
            events_json = await instance_storage.get("slack_thread_events", thread_key)
            if not events_json:
                return web.json_response({"error": "Thread not found"}, status=404)

            try:
                events = json.loads(events_json)
            except (json.JSONDecodeError, TypeError):
                return web.json_response({"error": "Invalid thread data"}, status=500)

            # Format events as simple HTML if no rendered HTML exists
            html = _format_events_as_html(events, bot_id, channel_id, thread_ts)

        return web.json_response(
            {
                "bot_id": bot_id,
                "team_id": team_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "html": html,
            }
        )

    except Exception as e:
        print(f"Error in get_thread_detail_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load thread: {str(e)}"}, status=500)


def _format_events_as_html(events: list[dict], bot_id: str, channel_id: str, thread_ts: str) -> str:
    """Format thread events as simple HTML when no rendered HTML is available."""
    html_parts = [
        "<div style='font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;'>",
        "<div style='background: #f5f5f5; padding: 12px; border-radius: 6px; margin-bottom: 20px; font-size: 13px;'>",
        "<strong>Thread Info:</strong><br>",
        f"Bot ID: <code>{bot_id}</code><br>",
        f"Channel: <code>{channel_id}</code><br>",
        f"Thread TS: <code>{thread_ts}</code>",
        "</div>",
    ]

    for i, event in enumerate(events):
        role = event.get("role", "unknown")
        content = event.get("content", "")

        role_bg = "#e3f2fd" if role == "user" else "#f3e5f5"
        role_label = role.capitalize()

        html_parts.append(f"""
            <div style='background: {role_bg}; padding: 16px; border-radius: 8px; margin-bottom: 12px;'>
                <div style='font-weight: bold; margin-bottom: 8px; color: #424242;'>{role_label}</div>
                <div style='white-space: pre-wrap; color: #212121;'>{content}</div>
            </div>
        """)

    html_parts.append("</div>")
    return "".join(html_parts)


async def list_threads_api(request: web.Request) -> web.Response:
    """Get threads for an organization (JSON API)."""
    try:
        context: AdminPanelContext = request.app["context"]

        if not context.storage:
            return web.json_response({"error": "Storage not available"}, status=500)

        # Get organization_id from query parameter
        try:
            organization_id = int(request.query.get("organization_id", "0"))
        except ValueError:
            return web.json_response({"error": "Invalid organization_id"}, status=400)

        if organization_id == 0:
            return web.json_response({"error": "organization_id is required"}, status=400)

        # Get optional channel_id filter
        channel_id_filter = request.query.get("channel_id", "").strip()

        # Get pagination parameters
        page = int(request.query.get("page", "1"))
        limit = int(request.query.get("limit", "50"))

        # Ensure valid pagination
        page = max(1, page)
        limit = max(1, min(limit, 200))

        # Calculate offset
        offset = (page - 1) * limit

        # Get organization information
        org = await context.storage.get_organization_by_id(organization_id)
        if not org:
            return web.json_response({"error": "Organization not found"}, status=404)

        # Get all bot instances for this organization
        def _get_bot_instances_for_org(storage: SlackbotStorage, org_id: int) -> list[str]:
            conn_factory = storage._sql_conn_factory  # type: ignore[attr-defined]
            with conn_factory.with_conn() as conn:
                cursor = conn.cursor()
                # Determine placeholder based on database type
                placeholder = "%s" if is_postgresql(conn) else "?"
                cursor.execute(
                    f"SELECT slack_team_id, channel_name, governance_alerts_channel FROM bot_instances WHERE organization_id = {placeholder}",
                    (org_id,),
                )
                rows = cursor.fetchall()
                bot_ids = []
                for row in rows:
                    slack_team_id = row[0]
                    channel_name = row[1]
                    governance_alerts_channel = row[2]

                    # Add bot_id for channel_name
                    bot_ids.append(f"{slack_team_id}-{channel_name}")

                    # Add bot_id for governance_alerts_channel if it exists and is different
                    if governance_alerts_channel and governance_alerts_channel != channel_name:
                        bot_ids.append(f"{slack_team_id}-{governance_alerts_channel}")

                return bot_ids

        bot_ids = await asyncio.to_thread(
            _get_bot_instances_for_org, context.storage, organization_id
        )

        if not bot_ids:
            return web.json_response(
                {
                    "threads": [],
                    "organization_id": organization_id,
                    "total": 0,
                    "page": page,
                    "limit": limit,
                }
            )

        # Collect all threads from all bots for this organization
        # Use a dict to deduplicate by (channel_id, thread_ts)
        threads_dict: dict[tuple[str, str], ThreadData] = {}

        for bot_id in bot_ids:
            instance_storage = context.storage.for_instance(bot_id)
            keys = await instance_storage.list("slack_thread_events")

            for key in keys:
                # Parse the key to extract channel_id and thread_ts
                if ":" not in key:
                    continue  # Skip malformed keys

                channel_id, thread_ts = key.split(":", 1)

                # Apply channel_id filter if provided
                if channel_id_filter and channel_id != channel_id_filter:
                    continue

                # Create unique key for deduplication
                thread_key = (channel_id, thread_ts)

                # Skip if we've already seen this thread
                if thread_key in threads_dict:
                    continue

                # Get the value to count events
                value = await instance_storage.get("slack_thread_events", key)
                if not value:
                    continue

                # Parse the events JSON to get event count
                try:
                    events = json.loads(value)
                    event_count = len(events) if isinstance(events, list) else 0
                except (json.JSONDecodeError, TypeError):
                    event_count = 0

                threads_dict[thread_key] = ThreadData(
                    bot_id=bot_id,
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    event_count=event_count,
                    organization_id=organization_id,
                    organization_name=org.organization_name,
                )

        # Convert dict to list and sort by channel_id and thread_ts for consistent ordering
        all_threads = list(threads_dict.values())
        all_threads.sort(key=lambda t: (t.channel_id, t.thread_ts))

        # Apply pagination
        total_count = len(all_threads)
        paginated_threads = all_threads[offset : offset + limit]

        return web.json_response(
            {
                "threads": [thread.model_dump() for thread in paginated_threads],
                "organization_id": organization_id,
                "total": total_count,
                "page": page,
                "limit": limit,
            }
        )

    except Exception as e:
        print(f"Error in list_threads_api: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return web.json_response({"error": f"Failed to load threads: {str(e)}"}, status=500)
