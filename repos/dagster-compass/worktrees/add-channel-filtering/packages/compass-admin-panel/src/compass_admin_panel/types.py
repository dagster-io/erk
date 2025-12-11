"""Shared types for Compass Admin Panel."""

from dataclasses import dataclass
from typing import Any

from csbot.slackbot.slackbot_core import CompassBotServerConfig, StripeConfig
from csbot.slackbot.storage.interface import SlackbotStorage
from pydantic import BaseModel


class ThreadData(BaseModel):
    """Thread data for admin panel display."""

    bot_id: str
    channel_id: str
    thread_ts: str
    event_count: int
    organization_id: int
    organization_name: str


@dataclass
class AdminPanelContext:
    """Structured context for admin panel operations."""

    config: CompassBotServerConfig | None
    storage: SlackbotStorage | None
    stripe_client: Any | None  # StripeClient type

    @property
    def has_stripe_config(self) -> bool:
        """Check if Stripe configuration is available."""
        return self.config is not None and hasattr(self.config, "stripe")

    @property
    def stripe_config(self) -> StripeConfig:
        """Get Stripe configuration."""
        if not self.has_stripe_config or not self.config:
            raise ValueError("Stripe configuration not available")
        return self.config.stripe
