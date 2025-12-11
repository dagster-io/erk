"""Onboarding tracking for Compass Admin Panel - API only (legacy HTML removed)."""

from typing import Any

from csbot.slackbot.slackbot_analytics import ERROR_EVENT_TYPES

# Usage milestone events to track
MILESTONE_EVENTS = [
    ("user_joined_channel", "User Joined Channel"),
    ("governance_welcome_sent", "User Governance Welcome Sent"),
    ("welcome_message_sent", "User Compass Welcome Message Sent"),
    ("channel_compass_welcome_sent", "Channel Compass Welcome Sent"),
    ("channel_governance_welcome_sent", "Channel Governance Welcome Sent"),
    ("connection_management_accessed", "Connection Management Accessed"),
    ("first_dataset_sync", "First Dataset Sync"),
]


async def _build_analytics_data(storage: Any, organization_id: int) -> dict[str, Any]:
    """Build usage milestones and error events from analytics data.

    This is extracted as a separate function to support lazy loading.
    """
    # Build list of event types we care about (milestones + errors)
    milestone_event_types = [event_type for event_type, _ in MILESTONE_EVENTS]
    relevant_event_types = list(set(milestone_event_types) | set(ERROR_EVENT_TYPES))

    # Query analytics for only the event types we need
    # This significantly reduces data transfer compared to fetching all events
    analytics_events, _, _ = await storage.get_analytics_for_organization(
        organization_id, limit=1000, offset=0, event_types=relevant_event_types
    )

    # Build a map of event types to their first occurrence
    event_type_map = {}
    error_events = []
    for event in analytics_events:
        event_type = event.get("event_type")
        if event_type:
            # Track first occurrence of each event type
            if event_type not in event_type_map:
                event_type_map[event_type] = event.get("created_at")

            # Collect error and drop-off events - check for actual error event types
            if event_type in ERROR_EVENT_TYPES:
                error_events.append(event)

    usage_milestones = []
    for event_type, event_name in MILESTONE_EVENTS:
        event_completed = event_type in event_type_map
        event_date = event_type_map.get(event_type)

        usage_milestones.append(
            {
                "name": event_name,
                "completed": event_completed,
                "completed_at": event_date,
            }
        )

    return {
        "usage_milestones": usage_milestones,
        "error_events": error_events,
    }
