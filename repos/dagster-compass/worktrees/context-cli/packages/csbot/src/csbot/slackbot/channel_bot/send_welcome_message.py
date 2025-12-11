import json
from typing import TYPE_CHECKING, cast

from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.slackbot_analytics import (
    AnalyticsEventType,
)

if TYPE_CHECKING:
    import structlog

    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slack_types import SlackInteractivePayload


async def handle_welcome_message_try_it_payload(
    bot: "CompassChannelBaseBotInstance", payload: "SlackInteractivePayload"
):
    """Handle the welcome_try_it button action by simulating the user asking the follow-up question."""
    logger = cast("structlog.BoundLogger", bot.logger).bind(task="welcome_try_it")

    # Extract the follow-up analysis question from the button value
    actions = payload.get("actions", [])
    if not actions:
        raise ValueError("No actions found in payload")

    action = actions[0]
    if action.get("action_id") != "welcome_try_it":
        raise ValueError(f"Unexpected action_id: {action.get('action_id')}")

    value = json.loads(action.get("value", "{}"))
    follow_up_analysis_question = value.get("follow_up_analysis_question")
    if not follow_up_analysis_question:
        raise ValueError("No follow_up_analysis_question found in button value")

    # Get user information
    user_id = payload["user"]["id"]
    channel = payload.get("channel")
    if not channel:
        raise ValueError("No channel found in payload")
    channel_id = channel["id"]

    # Get message timestamp
    message = payload.get("message", {})
    message_ts = message.get("ts")

    # Get enriched user info for analytics - use cached person info
    enriched_person = await bot.get_enriched_person(user_id)

    try:
        await bot._log_analytics_event_with_context(
            event_type=AnalyticsEventType.TRY_IT_CLICKED,
            channel_id=channel_id,
            user_id=user_id,
            message_ts=message_ts,
            thread_ts=value.get("thread_ts"),
            enriched_person=enriched_person,
            send_to_segment=True,
        )
    except Exception as e:
        # Don't let analytics logging break the main functionality
        bot.logger.warning(f"Analytics logging failed (non-critical): {e}")

    try:
        user_data = await get_cached_user_info(bot.client, bot.kv_store, user_id)
        if not user_data:
            raise ValueError(f"Could not get user info for {user_id}")

        display_name = user_data.real_name
        if not display_name:
            raise ValueError(f"No display name found for {user_id}")

        profile_pic = user_data.avatar_url

        # Get bot user ID
        bot_user_id = await bot.get_bot_user_id()
        if not bot_user_id:
            raise ValueError("Could not get bot user ID")

        # Format the question to include the bot mention
        formatted_question = f"<@{bot_user_id}> {follow_up_analysis_question}"

        # Post the message as if the user sent it
        message_response = await bot.client.chat_postMessage(
            channel=channel_id,
            text=formatted_question,
            username=display_name,
            icon_url=profile_pic,
        )

        if not message_response.get("ok"):
            raise ValueError(f"Failed to post message: {message_response}")

        message_ts = message_response.get("ts")
        if not message_ts:
            raise ValueError("No message timestamp in response")

        # Mention the user in a reply so they get notified
        await bot.client.chat_postMessage(
            channel=channel_id,
            text=f"👋 <@{user_id}>",
            thread_ts=message_ts,
        )

        # Trigger the bot to handle this as a new thread
        await bot._handle_new_thread(
            bot_user_id=bot_user_id,
            channel=channel_id,
            thread_ts=message_ts,
            user=user_id,
            message_ts=message_ts,
            message_content=formatted_question,
            collapse_thinking_steps=True,
            is_automated_message=True,
        )

    except Exception as e:
        logger.error(f"Error handling try it button payload: {e}")
        # Send an error message to the user
        await bot.client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"❌ <@{user_id}> Sorry, there was an error processing your request. Please try again.",
        )
        raise e
