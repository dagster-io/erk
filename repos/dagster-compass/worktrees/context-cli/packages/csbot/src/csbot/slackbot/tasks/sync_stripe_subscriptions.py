"""Background task to sync Stripe subscription data and update plan limits."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

import structlog
from ddtrace.trace import tracer

from csbot.slackbot.storage.interface import Organization, PlanManager
from csbot.slackbot.tasks import BackgroundTask
from csbot.slackbot.usage_tracking import UsageTracker
from csbot.stripe.stripe_client import StripeClient
from csbot.stripe.stripe_utils import update_plan_limits_from_product

logger = structlog.get_logger(__name__)


class SyncStripeSubscriptions(BackgroundTask):
    """Background task to sync plan limits and submit usage data to Stripe."""

    def __init__(
        self,
        stripe_client: StripeClient,
        usage_tracker: UsageTracker,
        plan_manager: PlanManager,
        organizations_provider: Callable[[], Awaitable[list[Organization]]],
        interval_hours: int = 24,
    ):
        self._stripe_client = stripe_client
        self._usage_tracker = usage_tracker
        self._organizations_provider = organizations_provider
        self._plan_manager = plan_manager
        self.interval_seconds = interval_hours * 60 * 60
        super().__init__(execute_on_init=True)

    @property
    def logger(self):
        return logger

    def get_sleep_seconds(self) -> float:
        """Return the sleep seconds."""
        return self.interval_seconds

    async def execute_tick(self) -> None:
        """Sync plan limits from Stripe subscriptions for all organizations."""

        # Get all organizations from database
        try:
            organizations = await self._organizations_provider()
        except Exception as e:
            self.logger.error(f"Failed to fetch organizations: {e}", exc_info=True)
            return

        if not organizations:
            self.logger.info("No organizations found, skipping sync")
            return

        self.logger.info(f"Starting sync for {len(organizations)} organizations")

        synced_count = 0
        error_count = 0

        for org in organizations:
            try:
                with tracer.trace("SyncScripeSubscriptions.execute_tick_for_org"):
                    await self.execute_tick_for_org(org, self._usage_tracker)
                synced_count += 1
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to sync organization '{org.organization_name}' (ID: {org.organization_id}): {e}",
                    organization=org.organization_name,
                    exc_info=True,
                )

        self.logger.info(
            f"Sync completed: {synced_count} organizations synced, {error_count} errors"
        )

    async def execute_tick_for_org(self, org: Organization, usage_tracker: UsageTracker) -> None:
        """Execute sync for a single organization with tracing."""
        org_id = org.organization_id
        org_name = org.organization_name
        subscription_id = org.stripe_subscription_id

        # Set organization name on the current span
        current_span = tracer.current_span()
        if current_span:
            current_span.set_tag("organization_name", org_name)
            current_span.set_tag("organization_id", org_id)

        if not subscription_id:
            if current_span:
                current_span.set_tag("missing_subscription", True)
            logger.debug(
                f"Organization '{org_name}' (ID: {org_id}) has no Stripe subscription, skipping",
                organization=org_name,
            )
            return

        # Get subscription details from Stripe
        subscription = await asyncio.to_thread(
            self._stripe_client.get_subscription_details, subscription_id
        )

        if not subscription or subscription.get("status") != "active":
            logger.warning(
                f"Organization '{org_name}' (ID: {org_id}) has inactive subscription {subscription_id}, skipping",
                organization=org_name,
            )
            return

        # Extract product ID from subscription
        product_id = None
        items_data = subscription.get("items", {}).get("data", [])
        if items_data:
            first_item = items_data[0]
            price_info = first_item.get("price", {})
            product_id = price_info.get("product")

        if not product_id:
            logger.warning(
                f"No product ID found in subscription {subscription_id} for organization '{org_name}' (ID: {org_id})",
                organization=org_name,
            )
            return

        # Update plan limits using the shared utility
        await update_plan_limits_from_product(
            stripe_client=self._stripe_client,
            plan_manager=self._plan_manager,
            product_id=product_id,
            organization_id=org_id,
        )

        # Submit usage data to Stripe meter for this organization
        await self._submit_usage_for_organization(
            organization=org,
            usage_tracker=usage_tracker,
        )

        self.logger.debug(
            f"Successfully synced plan limits for organization '{org_name}' (ID: {org_id})"
        )

    async def _submit_usage_for_organization(
        self,
        organization: Organization,
        usage_tracker: UsageTracker,
    ) -> None:
        """Submit usage data to Stripe meter for a single organization."""

        if not organization.stripe_customer_id:
            logger.debug(
                f"Organization '{organization.organization_name}' (ID: {organization.organization_id}) has no Stripe customer ID, skipping usage submission",
                organization=organization.organization_name,
            )
            return

        try:
            # Get current date for month/year calculations
            now = datetime.now()
            current_month = now.month
            current_year = now.year

            # Calculate previous month and year
            if current_month == 1:
                prev_month = 12
                prev_year = current_year - 1
            else:
                prev_month = current_month - 1
                prev_year = current_year

            # Aggregate usage across all bots for this organization
            total_current_usage = (
                await usage_tracker.analytics_store.get_organization_usage_for_month(
                    organization.organization_id,
                    current_month,
                    current_year,
                    include_bonus_answers=False,
                )
            )
            total_prev_usage = await usage_tracker.analytics_store.get_organization_usage_for_month(
                organization.organization_id, prev_month, prev_year, include_bonus_answers=False
            )
            logger.info(
                f"Current month usage for organization '{organization.organization_name}' (ID: {organization.organization_id}): {total_current_usage}, previous month usage: {total_prev_usage}",
                organization=organization.organization_name,
            )

            # Submit current month usage if any
            if total_current_usage > 0:
                await asyncio.to_thread(
                    self._stripe_client.submit_meter_usage,
                    meter_name="answers",
                    customer_id=organization.stripe_customer_id,
                    usage_value=total_current_usage,
                )
                logger.debug(
                    f"Submitted {total_current_usage} answers usage for current month ({current_year}-{current_month:02d}) "
                    f"for organization '{organization.organization_name}' (ID: {organization.organization_id})",
                    organization=organization.organization_name,
                )

            # Submit previous month usage if within 24 hours of last month and has usage
            if total_prev_usage > 0 and self._should_submit_previous_month():
                await asyncio.to_thread(
                    self._stripe_client.submit_meter_usage,
                    meter_name="answers",
                    customer_id=organization.stripe_customer_id,
                    usage_value=total_prev_usage,
                )
                logger.debug(
                    f"Submitted {total_prev_usage} answers usage for previous month ({prev_year}-{prev_month:02d}) "
                    f"for organization '{organization.organization_name}' (ID: {organization.organization_id})",
                    organization=organization.organization_name,
                )

        except Exception as e:
            logger.error(
                f"Failed to submit usage data for organization '{organization.organization_name}' (ID: {organization.organization_id}): {e}",
                organization=organization.organization_name,
                exc_info=True,
            )

    def _should_submit_previous_month(self) -> bool:
        """Check if we should submit previous month usage (within 24 hours of month start)."""
        now = datetime.now()
        # If it's the first day of the month, we're within 24 hours
        return now.day == 1
