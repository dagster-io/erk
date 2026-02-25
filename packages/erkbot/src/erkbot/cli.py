import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from erk_shared.gateway.time.real import RealTime
from erkbot.agent.bot import ErkBot
from erkbot.app import create_app
from erkbot.config import Settings
from erkbot.prompts import get_erk_system_prompt

logger = logging.getLogger(__name__)


async def _run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    load_dotenv()
    settings = Settings()
    time = RealTime()

    bot: ErkBot | None = None
    if settings.anthropic_api_key is not None and settings.erk_repo_path is not None:
        repo_path = Path(settings.erk_repo_path)
        if repo_path.is_dir():
            bot = ErkBot(
                model=settings.erk_model,
                max_turns=settings.max_turns,
                cwd=repo_path,
                system_prompt=get_erk_system_prompt(repo_root=repo_path),
                permission_mode="bypassPermissions",
            )
        else:
            logger.warning(
                "startup: erk_repo_path=%s is not a valid directory,"
                " falling back to slack-only mode",
                settings.erk_repo_path,
            )

    if bot is not None:
        logger.info(
            "startup: mode=agent-enabled model=%s repo_path=%s max_turns=%d",
            settings.erk_model,
            settings.erk_repo_path,
            settings.max_turns,
        )
    else:
        logger.info("startup: mode=slack-only")

    app = create_app(settings=settings, bot=bot, time=time)
    handler = AsyncSocketModeHandler(app, settings.slack_app_token)
    await handler.start_async()


def main() -> None:
    asyncio.run(_run())
