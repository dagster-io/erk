from __future__ import annotations

from typing import TYPE_CHECKING

from slack_bolt.async_app import AsyncApp

from erk_shared.gateway.time.abc import Time
from erkbot.config import Settings
from erkbot.slack_handlers import register_handlers

if TYPE_CHECKING:
    from erkbot.agent.bot import ErkBot


def create_app(*, settings: Settings, bot: ErkBot | None, time: Time) -> AsyncApp:
    app = AsyncApp(token=settings.slack_bot_token)
    register_handlers(app, settings=settings, bot=bot, time=time)
    return app
