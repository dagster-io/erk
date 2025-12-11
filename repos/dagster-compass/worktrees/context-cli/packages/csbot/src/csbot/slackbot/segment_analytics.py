"""Segment Analytics integration for tracking all Compass bot events.

This module provides Segment track event integration that mirrors all existing
analytics events tracked in the SlackbotAnalyticsStore. This allows for better
external analytics integration and data analysis.
"""

import asyncio
import json
import logging
import time
from collections import deque
from typing import TYPE_CHECKING, Any

try:
    import analytics
except ImportError:
    analytics = None

from .slackbot_analytics import AnalyticsEventType

if TYPE_CHECKING:
    from .channel_bot.personalization import EnrichedPerson


class SegmentAnalytics:
    """Segment Analytics integration for Compass bot events with resilience features."""

    def __init__(
        self,
        write_key: str | None = None,
        orgs_enabled: list[str] | None = None,
        debug: bool = False,
    ):
        """Initialize Segment Analytics.

        Args:
            write_key: Segment write key
            debug: Enable debug mode for testing
        """
        self.write_key = write_key
        self.orgs_enabled = orgs_enabled
        self.debug = debug
        self.enabled = write_key is not None and analytics is not None

        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_open = False
        self._max_failures = 5  # Open circuit after 5 consecutive failures
        self._reset_timeout = 300  # Reset circuit after 5 minutes

        # Event queuing and sequencing
        self._event_queue = deque()
        self._processing = False
        self._min_interval = 0.05  # Reduced to 50ms for better throughput
        self._last_call_time = 0

        if self.enabled and analytics is not None:
            analytics.write_key = write_key
            analytics.debug = debug
            analytics.sync_mode = False  # Use async mode
            # Configure timeouts for resilience
            analytics.timeout = 5  # 5 second timeout
            analytics.max_retries = 2  # Retry twice

        self.logger = logging.getLogger(__name__)

        if not analytics:
            self.logger.warning(
                "Segment analytics library not installed. Install with: pip install analytics-python. "
                "Regular analytics will continue to work normally."
            )
        elif not write_key:
            self.logger.debug(
                "No Segment write key provided - Segment analytics disabled. "
                "Regular analytics will continue to work normally."
            )

    def _disabled_for_org(self, organization_name: str):
        return self.orgs_enabled and organization_name not in self.orgs_enabled

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self._circuit_open:
            return False

        # Check if we should reset the circuit
        if time.time() - self._last_failure_time > self._reset_timeout:
            self._circuit_open = False
            self._failure_count = 0
            self.logger.info("Segment circuit breaker reset - re-enabling analytics")
            return False

        return True

    def _record_success(self) -> None:
        """Record a successful call."""
        if self._failure_count > 0:
            self._failure_count = 0
            self.logger.debug("Segment analytics recovered - failure count reset")

    def _record_failure(self) -> None:
        """Record a failed call and potentially open circuit."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._max_failures and not self._circuit_open:
            self._circuit_open = True
            self.logger.warning(
                f"Segment circuit breaker opened after {self._failure_count} failures - "
                f"analytics disabled for {self._reset_timeout} seconds"
            )

    def _should_rate_limit(self) -> bool:
        """Check if we should rate limit this call."""
        current_time = time.time()
        if current_time - self._last_call_time < self._min_interval:
            return True
        self._last_call_time = current_time
        return False

    async def _process_event_queue(self) -> None:
        """Process queued events sequentially to avoid race conditions."""
        if self._processing or not self._event_queue:
            return

        self._processing = True
        try:
            while self._event_queue:
                event = self._event_queue.popleft()
                event_type = event.get("type")

                if event_type == "identify":
                    await self._identify_async(
                        user_id=event["user_id"],
                        traits=event.get("traits"),
                        context=event.get("context"),
                    )
                elif event_type == "track":
                    await self._track_async(
                        user_id=event["user_id"],
                        event=event["event"],
                        properties=event.get("properties"),
                        context=event.get("context"),
                    )
                elif event_type == "alias":
                    await self._alias_async(
                        previous_id=event["previous_id"],
                        user_id=event["user_id"],
                    )

                # Small delay between events to prevent overwhelming Segment
                await asyncio.sleep(0.01)  # 10ms delay

        finally:
            self._processing = False

    async def _alias_async(
        self,
        previous_id: str,
        user_id: str,
    ) -> None:
        """Async wrapper for alias with proper error handling."""
        try:
            if analytics is not None:
                analytics.alias(previous_id=previous_id, user_id=user_id)
                self._record_success()
                self.logger.debug(f"Aliased Segment user {previous_id} -> {user_id}")
        except Exception as e:
            self._record_failure()
            self.logger.debug(f"Error aliasing Segment user {previous_id} -> {user_id}: {e}")

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of Segment analytics.

        Returns:
            Dictionary with health information
        """
        return {
            "enabled": self.enabled,
            "circuit_open": self._circuit_open,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time,
            "time_until_reset": max(
                0, self._reset_timeout - (time.time() - self._last_failure_time)
            )
            if self._circuit_open
            else 0,
        }

    def force_reset_circuit(self) -> None:
        """Force reset the circuit breaker (for admin use)."""
        self._circuit_open = False
        self._failure_count = 0
        self._last_failure_time = 0
        self.logger.info("Segment circuit breaker manually reset")

    def track(
        self,
        user_id: str | None,
        event: str,
        organization_name: str,
        properties: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Track an event in Segment (queued for proper sequencing).

        Args:
            user_id: User identifier (can be None for anonymous events)
            event: Event name
            properties: Event properties
            context: Additional context
        """
        if not self.enabled:
            self.logger.debug(f"Segment analytics disabled - skipping track event: {event}")
            return

        if self._disabled_for_org(organization_name):
            self.logger.debug(
                f"Segment analytics disabled for org {organization_name} - skipping track event: {event}"
            )
            return

        if self._is_circuit_open():
            self.logger.debug(
                f"Segment analytics circuit breaker open - skipping track event: {event}"
            )
            return

        # Use anonymous user ID if none provided
        if not user_id:
            user_id = "anonymous"

        # Queue the event for sequential processing
        self._event_queue.append(
            {
                "type": "track",
                "user_id": user_id,
                "event": event,
                "properties": properties,
                "context": context,
            }
        )

        # Start processing if not already running
        asyncio.create_task(self._process_event_queue())

    async def _track_async(
        self,
        user_id: str,
        event: str,
        properties: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Async wrapper for track with proper error handling."""
        try:
            if analytics is not None:
                analytics.track(
                    user_id=user_id,
                    event=event,
                    properties=properties or {},
                    context=context or {},
                )
                self._record_success()
                self.logger.debug(f"Tracked Segment event: {event} for user: {user_id}")
        except Exception as e:
            self._record_failure()
            # Never let analytics errors break the main flow
            self.logger.debug(f"Error tracking Segment event {event}: {e}")

    def identify(
        self,
        user_id: str,
        organization_name: str,
        traits: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Identify a user in Segment (queued for proper sequencing).

        Args:
            user_id: User identifier
            traits: User traits
            context: Additional context
        """
        if not self.enabled:
            self.logger.debug(f"Segment analytics disabled - skipping identify for user: {user_id}")
            return

        if self._disabled_for_org(organization_name):
            self.logger.debug(
                f"Segment analytics disabled for org {organization_name} - skipping identity for user: {user_id}"
            )
            return

        if self._is_circuit_open():
            self.logger.debug(
                f"Segment analytics circuit breaker open - skipping identify for user: {user_id}"
            )
            return

        # Queue the event for sequential processing (identify gets priority)
        self._event_queue.appendleft(
            {  # Use appendleft to prioritize identify calls
                "type": "identify",
                "user_id": user_id,
                "traits": traits,
                "context": context,
            }
        )

        # Start processing if not already running
        asyncio.create_task(self._process_event_queue())

    async def _identify_async(
        self,
        user_id: str,
        traits: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Async wrapper for identify with proper error handling."""
        try:
            if analytics is not None:
                analytics.identify(
                    user_id=user_id,
                    traits=traits or {},
                    context=context or {},
                )
                self._record_success()
                self.logger.debug(f"Identified Segment user: {user_id}")
        except Exception as e:
            self._record_failure()
            self.logger.debug(f"Error identifying Segment user {user_id}: {e}")

    def track_analytics_event(
        self,
        event_type: AnalyticsEventType,
        bot_id: str,
        organization_name: str,
        channel_id: str | None = None,
        user_id: str | None = None,
        thread_ts: str | None = None,
        message_ts: str | None = None,
        metadata: str | None = None,
        tokens_used: int | None = None,
        enriched_person: "EnrichedPerson | None" = None,
        # New optional parameters for enhanced context
        organization_id: int | None = None,
        channel_name: str | None = None,
        team_id: str | None = None,
        onboarding_type: str | None = None,
    ) -> None:
        """Track an analytics event in Segment (mirrors SlackbotAnalyticsStore).

        Args:
            event_type: Type of analytics event
            bot_id: Bot identifier
            organization_name: organization
            channel_id: Slack channel ID
            user_id: Slack user ID
            thread_ts: Thread timestamp
            message_ts: Message timestamp
            metadata: JSON metadata string
            tokens_used: Number of tokens used
            enriched_person: Enriched user information
            onboarding_type: Type of onboarding flow (e.g., 'standard', 'prospector')
        """
        if not self.enabled:
            self.logger.debug(
                f"Segment analytics disabled - skipping analytics event: {event_type.value}"
            )
            return

        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                self.logger.debug(f"Failed to parse metadata for event {event_type.value}")

        # Build event properties with enhanced context
        properties = {
            "bot_id": bot_id,
            "event_type": event_type.value,
        }

        # Add channel and organization context
        if channel_id:
            properties["channel_id"] = channel_id
        if channel_name:
            properties["channel_name"] = channel_name
        if team_id:
            properties["team_id"] = team_id
        properties["organization_name"] = organization_name
        if organization_id is not None:
            properties["organization_id"] = str(organization_id)

        # Add optional properties
        if thread_ts:
            properties["thread_ts"] = thread_ts
        if message_ts:
            properties["message_ts"] = message_ts
        if tokens_used is not None:
            properties["tokens_used"] = str(tokens_used)
        if onboarding_type is not None:
            properties["onboarding_type"] = onboarding_type

        # Merge metadata into properties (ensure all values are strings)
        if parsed_metadata:
            for key, value in parsed_metadata.items():
                if value is not None:
                    properties[key] = str(value)

        # Add enriched user information
        if enriched_person:
            user_props: dict[str, str] = {}
            if enriched_person.real_name:
                user_props["user_real_name"] = enriched_person.real_name
            if enriched_person.timezone:
                user_props["user_timezone"] = enriched_person.timezone
            # Only add email if it exists and has a value
            if enriched_person.email:
                user_props["user_email"] = enriched_person.email
            properties.update(user_props)

        # Build context
        context = {
            "app": {
                "name": "Compass Bot",
                "version": "1.0",
            },
            "library": {
                "name": "compass-bot-analytics",
                "version": "1.0",
            },
        }

        # Determine the best user_id to use with robust fallback strategy
        segment_user_id = user_id or "anonymous"  # Fallback to anonymous if no user_id
        user_traits = {}

        # Prefer email as user_id for consistency, with Slack user_id as fallback
        if enriched_person and enriched_person.email:
            if enriched_person.email.strip():  # Ensure email is not empty
                segment_user_id = enriched_person.email
                user_traits.update(
                    {
                        "email": enriched_person.email,
                        "real_name": enriched_person.real_name,
                        "timezone": enriched_person.timezone,
                    }
                )
                # Keep Slack user_id as trait for linking/reference
                if user_id:
                    user_traits["slack_user_id"] = user_id

                self.logger.debug(f"Using email {enriched_person.email} as Segment user_id")
            elif enriched_person.real_name or enriched_person.timezone:
                # No email, but we have other user info - use Slack user_id with traits
                user_traits.update(
                    {
                        "real_name": enriched_person.real_name,
                        "timezone": enriched_person.timezone,
                        "identified_via": "slack_profile",  # Track how we identified them
                    }
                )
                self.logger.debug(
                    f"No email available, using Slack user_id {user_id} with profile traits"
                )

        # Auto-identify user only for significant events to update their profile
        significant_events = {
            AnalyticsEventType.USER_JOINED_CHANNEL,
            AnalyticsEventType.FIRST_SUCCESSFUL_QUERY,
            AnalyticsEventType.NEW_CONVERSATION,
        }

        if event_type in significant_events and user_traits:
            self.identify(
                user_id=segment_user_id, organization_name=organization_name, traits=user_traits
            )

        # Track the event
        self.track(
            user_id=segment_user_id,
            event=self._format_event_name(event_type),
            organization_name=organization_name,
            properties=properties,
            context=context,
        )

    def _format_event_name(self, event_type: AnalyticsEventType) -> str:
        """Format event type as a human-readable event name.

        Args:
            event_type: Analytics event type enum

        Returns:
            Formatted event name for Segment
        """
        # Convert snake_case to Title Case
        return event_type.value.replace("_", " ").title()


# Global instance that can be configured
segment_analytics: SegmentAnalytics | None = None


def init_segment_analytics(
    write_key: str | None = None, orgs_enabled: list[str] | None = None, debug: bool = False
) -> None:
    """Initialize the global Segment analytics instance.

    Args:
        write_key: Segment write key
        orgs_enabled: if provided, only events for these orgs will be sent to segment
        debug: Enable debug mode
    """
    global segment_analytics
    segment_analytics = SegmentAnalytics(
        write_key=write_key,
        orgs_enabled=orgs_enabled,
        debug=debug,
    )


def track_event(
    event_type: AnalyticsEventType,
    bot_id: str,
    organization_name: str,
    channel_id: str | None = None,
    user_id: str | None = None,
    thread_ts: str | None = None,
    message_ts: str | None = None,
    metadata: str | None = None,
    tokens_used: int | None = None,
    enriched_person: "EnrichedPerson | None" = None,
    # Enhanced context parameters
    organization_id: int | None = None,
    channel_name: str | None = None,
    team_id: str | None = None,
    onboarding_type: str | None = None,
) -> None:
    """Track an event using the global Segment analytics instance.

    This is a convenience function that mirrors the SlackbotAnalyticsStore interface
    with enhanced organization and channel context.
    """
    if segment_analytics:
        segment_analytics.track_analytics_event(
            event_type=event_type,
            bot_id=bot_id,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            metadata=metadata,
            tokens_used=tokens_used,
            enriched_person=enriched_person,
            organization_name=organization_name,
            organization_id=organization_id,
            channel_name=channel_name,
            team_id=team_id,
            onboarding_type=onboarding_type,
        )


def track_onboarding_event(
    step_name: str,
    organization: str,
    email: str,
    additional_info: dict[str, str] | None = None,
) -> None:
    """Track an onboarding event in Segment with automatic user identification.

    Args:
        step_name: Name of the onboarding step
        organization: Organization name
        email: User email
        additional_info: Additional information
    """
    if not segment_analytics:
        return

    # Identify the user first (creates/updates user profile)
    segment_analytics.identify(
        user_id=email,
        organization_name=organization,
        traits={
            "email": email,
            "organization": organization,
            "onboarding_step": step_name,
            "product": "Compass Bot",
        },
    )

    # Track the onboarding event
    properties = {
        "organization": organization,
        "email": email,
        "step": step_name,
    }

    if additional_info:
        properties.update(additional_info)

    segment_analytics.track(
        user_id=email,
        event=f"Onboarding {step_name}",
        organization_name=organization,
        properties=properties,
    )
