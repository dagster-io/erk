from typing import TYPE_CHECKING

from csbot.slackbot.storage.onboarding_state import BotInstanceType

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig

DAILY_EXPLORATION_EXEMPT_ORGANIZATION_IDS = {
    30,  # Index Ventures
    59,  # Airbyte
}

WELCOME_MESSAGE_EXEMPT_ORGANIZATION_IDS = {
    30,  # Index Ventures
}


def is_exempt_from_daily_exploration(bot: "CompassChannelBaseBotInstance") -> bool:
    """Check if bot is exempt from daily exploration.

    Exempt organizations include:
    - Specific hardcoded organizations upon request (e.g. Index Ventures)
    """
    return bot.bot_config.organization_id in DAILY_EXPLORATION_EXEMPT_ORGANIZATION_IDS


def is_exempt_from_welcome_message(bot: "CompassChannelBaseBotInstance") -> bool:
    return bot.bot_config.organization_id in WELCOME_MESSAGE_EXEMPT_ORGANIZATION_IDS


# Compass can run in 4 modes:
# 1. Normal mode, which is what our design partners use today. They sign up for
#    an account, we load the bot into a few of their channels, and they can chat
#    with their data.
# 2. Prospector mode, an upcoming simplified version of the product where users
#    don't have to connect to a data warehouse and can instead just chat with
#    the People Data Labs data set.
# 3. Community Prospector mode, a version of Prospector that is run in large
#    untrusted communities like VCs and revops collectives. Since it is open to
#    lots of untrusted users, it has special rate limits, billing, and does not
#    allow updates of the context store.
# 4. Dagster Community mode, which is identical to Community Prospector mode,
#    except that it is run in the Dagster community slack and has some extra
#    "nerd snipey" data sets, and can be managed via a governance channel by our
#    team.


def is_dagster_community_mode(bot_config: "CompassBotSingleChannelConfig") -> bool:
    return (
        # Dagster community channel
        bot_config.organization_id == 96
        or (
            # Enable community mode for org 155 only if staging community channel
            bot_config.organization_id == 155
            and bot_config.organization_name == "Staging Community"
            and bot_config.channel_name == "staging-community-compass"
        )
    )


def is_prospector_mode(bot: "CompassChannelBaseBotInstance") -> bool:
    """Check if bot is running in prospector mode (organization_type = 'prospector')."""
    return bot.bot_config.is_prospector


def is_community_prospector_mode(bot_config: "CompassBotSingleChannelConfig") -> bool:
    # COMMUNITY PROSPECTOR MODE
    return bot_config.instance_type == BotInstanceType.COMMUNITY_PROSPECTOR


def is_community_prospector_token(token: str) -> bool:
    return token == "COMMUNITY"


def is_prospector_grant_token(token: str) -> bool:
    return token == "PROSPECTING"


def is_any_community_mode(bot: "CompassChannelBaseBotInstance") -> bool:
    return is_dagster_community_mode(bot.bot_config) or is_community_prospector_mode(bot.bot_config)


def is_any_prospector_mode(bot: "CompassChannelBaseBotInstance") -> bool:
    return is_prospector_mode(bot) or is_community_prospector_mode(bot.bot_config)


def is_normal_mode(bot: "CompassChannelBaseBotInstance") -> bool:
    return not is_any_community_mode(bot) and not is_any_prospector_mode(bot)


def is_dagsterlabs_internal(bot: "CompassChannelBaseBotInstance") -> bool:
    return bot.bot_config.organization_id in (1, 2, 45, 158)
