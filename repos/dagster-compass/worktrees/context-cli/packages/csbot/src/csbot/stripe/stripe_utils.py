"""Shared utility functions for managing plan limits table updates."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from csbot.slackbot.storage.interface import PlanManager
from csbot.stripe.stripe_client import StripeClient

if TYPE_CHECKING:
    from csbot.slackbot.storage.interface import SlackbotStorage


logger = logging.getLogger(__name__)


async def update_plan_limits_from_product(
    stripe_client: StripeClient,
    plan_manager: PlanManager,
    product_id: str,
    organization_id: int,
    provided_logger: logging.Logger | None = None,
) -> None:
    """Update plan limits for an organization based on Stripe product metadata.

    Args:
        bot_server: The CompassBotServer instance with stripe_client and bot_manager
        product_id: The Stripe product ID to get limits from
        organization_id: The organization ID to update limits for
        logger: Optional logger for debugging (falls back to bot_server.logger)

    Raises:
        Exception: If plan limits update fails (should be caught by caller)
    """
    provided_logger = provided_logger or logger
    plan_limits = await asyncio.to_thread(stripe_client.get_product_plan_limits, product_id)
    base_num_answers = plan_limits.base_num_answers
    allow_overage = plan_limits.allow_overage
    num_channels = plan_limits.num_channels
    allow_additional_channels = plan_limits.allow_additional_channels

    await plan_manager.set_plan_limits(
        organization_id=organization_id,
        base_num_answers=base_num_answers,
        allow_overage=allow_overage,
        num_channels=num_channels,
        allow_additional_channels=allow_additional_channels,
    )
    logger.info(
        f"Successfully updated plan limits for org {organization_id}: "
        f"{base_num_answers} answers, overage {'allowed' if allow_overage else 'not allowed'}, "
        f"{num_channels} channels, additional channels {'allowed' if allow_additional_channels else 'not allowed'}"
    )


async def update_plan_limits_with_dependencies(
    stripe_client: Any,  # StripeClient type
    storage: "SlackbotStorage",
    product_id: str,
    organization_id: int,
    logger: logging.Logger | None = None,
) -> None:
    """Update plan limits for an organization based on Stripe product metadata using direct dependencies.

    This is an alternative to update_plan_limits_from_product that accepts individual
    dependencies instead of requiring a full CompassBotServer instance.

    Args:
        stripe_client: The Stripe client instance
        storage: The storage instance for plan limits updates
        product_id: The Stripe product ID to get limits from
        organization_id: The organization ID to update limits for
        logger: Optional logger for debugging

    Raises:
        Exception: If plan limits update fails (should be caught by caller)
    """
    if not stripe_client:
        raise ValueError("Stripe client not available")

    if not storage:
        raise ValueError("Storage not available")

    plan_limits = await asyncio.to_thread(stripe_client.get_product_plan_limits, product_id)
    base_num_answers = plan_limits.base_num_answers
    allow_overage = plan_limits.allow_overage
    num_channels = plan_limits.num_channels
    allow_additional_channels = plan_limits.allow_additional_channels

    # Update plan limits in storage if base_num_answers is available
    if base_num_answers is not None:
        await storage.set_plan_limits(
            organization_id=organization_id,
            base_num_answers=base_num_answers,
            allow_overage=allow_overage,
            num_channels=num_channels,
            allow_additional_channels=allow_additional_channels,
        )
        if logger is not None:
            logger.info(
                f"Successfully updated plan limits for org {organization_id}: "
                f"{base_num_answers} answers, overage {'allowed' if allow_overage else 'not allowed'}, "
                f"{num_channels} channels, additional channels {'allowed' if allow_additional_channels else 'not allowed'}"
            )
    else:
        if logger is not None:
            logger.warning(
                f"No base_num_answers found in product {product_id} metadata, "
                "skipping plan limits setup"
            )
