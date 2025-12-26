import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance

DEFAULT_MAX_ANSWERS_PER_USER_24H = 100
DEFAULT_MAX_ANSWERS_PER_USER_7D = 500
DEFAULT_MAX_ANSWERS_PER_BOT_24H = 5000


class QuotaCheckResult(Enum):
    OK = "ok"
    BOT_24H_QUOTA_EXCEEDED = "bot_24h_quota_exceeded"
    USER_7D_QUOTA_EXCEEDED = "user_7d_quota_exceeded"
    USER_24H_QUOTA_EXCEEDED = "user_24h_quota_exceeded"


@dataclass(frozen=True)
class CommunityBotMixin:
    max_answers_per_user_24h: int = DEFAULT_MAX_ANSWERS_PER_USER_24H
    max_answers_per_user_7d: int = DEFAULT_MAX_ANSWERS_PER_USER_7D
    max_answers_per_bot_24h: int = DEFAULT_MAX_ANSWERS_PER_BOT_24H

    def __post_init__(self):
        # Validate quotas
        if self.max_answers_per_user_24h > self.max_answers_per_user_7d:
            raise ValueError(
                "max_answers_per_user_24h must be greater than max_answers_per_user_7d"
            )
        if self.max_answers_per_bot_24h < self.max_answers_per_user_24h:
            raise ValueError(
                "max_answers_per_bot_24h must be greater than max_answers_per_user_24h"
            )

    def is_quota_exceeded(
        self, period_seconds: int, max_allowed: int, timestamps: list[int]
    ) -> bool:
        if len(timestamps) < max_allowed + 1:
            # entity has never done more than max_allowed events
            return False

        timestamp_before_window = timestamps[-(max_allowed + 1)]
        last_timestamp_in_window = timestamps[-1]
        if last_timestamp_in_window - timestamp_before_window < period_seconds:
            # entity has done max_allowed events within the period
            return True

        return False

    async def check_and_bump_answer_quotas(
        self,
        now_seconds: float | int,
        bot: "CompassChannelBaseBotInstance",
        user: str,
    ) -> QuotaCheckResult:
        # you always need to keep 1 extra timestamp to check if the quota is exceeded
        num_timestamps_to_keep_user = self.max_answers_per_user_7d + 1
        num_timestamps_to_keep_bot = self.max_answers_per_bot_24h + 1

        now = int(now_seconds)

        user_timestamps_raw, bot_timestamps_raw = await asyncio.gather(
            bot.kv_store.get("community_mode.user_timestamps", user),
            bot.kv_store.get("community_mode.bot_timestamps", bot.key.to_bot_id()),
        )

        user_timestamps = json.loads(user_timestamps_raw or "{}").get("ts", [])
        bot_timestamps = json.loads(bot_timestamps_raw or "{}").get("ts", [])

        user_timestamps = [*user_timestamps, now][-num_timestamps_to_keep_user:]
        bot_timestamps = [*bot_timestamps, now][-num_timestamps_to_keep_bot:]

        is_quota_exceeded_user_24h = self.is_quota_exceeded(
            24 * 60 * 60, self.max_answers_per_user_24h, user_timestamps
        )

        if is_quota_exceeded_user_24h:
            return QuotaCheckResult.USER_24H_QUOTA_EXCEEDED

        is_quota_exceeded_user_7d = self.is_quota_exceeded(
            7 * 24 * 60 * 60, self.max_answers_per_user_7d, user_timestamps
        )

        if is_quota_exceeded_user_7d:
            return QuotaCheckResult.USER_7D_QUOTA_EXCEEDED

        is_quota_exceeded_bot_24h = self.is_quota_exceeded(
            24 * 60 * 60, self.max_answers_per_bot_24h, bot_timestamps
        )

        if is_quota_exceeded_bot_24h:
            return QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED

        ONE_MONTH_SECONDS = 30 * 24 * 60 * 60
        await asyncio.gather(
            bot.kv_store.set(
                "community_mode.user_timestamps",
                user,
                json.dumps({"ts": user_timestamps}),
                expiry_seconds=ONE_MONTH_SECONDS,
            ),
            bot.kv_store.set(
                "community_mode.bot_timestamps",
                bot.key.to_bot_id(),
                json.dumps({"ts": bot_timestamps}),
                expiry_seconds=ONE_MONTH_SECONDS,
            ),
        )

        return QuotaCheckResult.OK

    def get_community_mode_quota_message_markdown(
        self, result: QuotaCheckResult, user_id: str, organization_id: int | None
    ) -> str:
        upsell = self.get_upsell_message(organization_id=organization_id)
        if result == QuotaCheckResult.OK:
            raise ValueError("result cannot be ok")

        elif result == QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED:
            return f"❌ hey <@{user_id}>, this channel has reached its limit for the day. please try again tomorrow.{upsell}"
        elif result == QuotaCheckResult.USER_7D_QUOTA_EXCEEDED:
            return f"❌ hey <@{user_id}>, you have used all your free quota for the week. please try again next week.{upsell}"
        elif result == QuotaCheckResult.USER_24H_QUOTA_EXCEEDED:
            return f"❌ hey <@{user_id}>, you have used all your free quota for the day. please try again tomorrow.{upsell}"

        raise ValueError(f"Invalid quota result: {result}")

    def get_upsell_message(self, organization_id: int | None):
        utm_content = (
            f"utm_content=community_{organization_id}"
            if organization_id
            else "utm_content=community_unknown"
        )
        url_str = f"<https://compass.dagster.io?utm_source=slack&utm_medium=referral&utm_campaign=slack_community_upsell&{utm_content}|https://compass.dagster.io/>"
        demo_url_utm = f"https://compass.dagster.io/request-a-demo?utm_source=slack&utm_medium=referral&utm_campaign=slack_community_upsell&{utm_content}"
        demo_url_str = f"<{demo_url_utm}|https://compass.dagster.io/request-a-demo>"

        return (
            f"\n\nif you would like more quota, sign up for your own free account at {url_str}. "
            f"\n\nif you're not sure which option is right for you, request a demo with our team at {demo_url_str}"
        )
