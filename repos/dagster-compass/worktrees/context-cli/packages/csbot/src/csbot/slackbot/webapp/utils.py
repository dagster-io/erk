from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


def _is_test_environment(bot_server: "CompassBotServer") -> bool:
    """Determine if running in test/development environment based on public URL scheme.

    Returns True for HTTP (local/test), False for HTTPS (production).
    This determines whether to use secure cookies (HTTPS only) or not.
    """
    return bot_server.config.public_url.startswith("http://")
