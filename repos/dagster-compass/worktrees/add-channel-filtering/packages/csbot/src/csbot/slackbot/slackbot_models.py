"""Shared data models for slackbot to avoid circular imports."""

from typing import Literal

from pydantic import BaseModel


class PrInfo(BaseModel):
    """Information about a pull request created by the bot."""

    type: Literal["context_update_created", "scheduled_analysis_created"]
    bot_id: str
