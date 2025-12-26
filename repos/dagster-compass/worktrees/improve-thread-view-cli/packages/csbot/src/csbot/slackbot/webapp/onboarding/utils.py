from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


async def is_token_valid(
    token: str | None, organization_id: int | str, bot_server: "CompassBotServer"
) -> tuple[bool, str]:
    bot_server.logger.info(
        f"Validating token for organization {organization_id}. "
        f"Token={token[:8] if isinstance(token, str) else None}..."
    )
    if token and isinstance(token, str) and token.strip():
        token_status = await bot_server.bot_manager.storage.is_referral_token_valid(token)

        if not token_status.is_valid:
            return False, "Invalid token"

        if token_status.has_been_consumed and token_status.is_single_use:
            return False, "Single-use token already consumed"

        bot_server.logger.info(
            f"Valid token for organization {organization_id}. . Token={token[:8]}..."
        )
    return True, ""
