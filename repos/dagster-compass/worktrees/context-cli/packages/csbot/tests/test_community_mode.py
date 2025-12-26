from unittest.mock import AsyncMock, Mock

import pytest

from csbot.slackbot.channel_bot.bot import BotTypeQA, CompassChannelQACommunityBotInstance
from csbot.slackbot.community_bot_mixin import (
    QuotaCheckResult,
)


class MockCommunityBotInstance(CompassChannelQACommunityBotInstance):
    """Mock bot instance subclass that allows setting community mode quotas for testing."""

    def __init__(
        self,
        *args,
        max_answers_per_user_24h: int = 5,
        max_answers_per_user_7d: int = 10,
        max_answers_per_bot_24h: int = 20,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(self, "max_answers_per_user_24h", max_answers_per_user_24h)
        object.__setattr__(self, "max_answers_per_user_7d", max_answers_per_user_7d)
        object.__setattr__(self, "max_answers_per_bot_24h", max_answers_per_bot_24h)


class DictBackedKVStore:
    """A simple dictionary-backed implementation of SlackbotInstanceStorage for testing."""

    def __init__(self):
        self._store = {}

    async def get(self, family: str, key: str) -> str | None:
        """Get a value by family and key."""
        full_key = f"{family}:{key}"
        return self._store.get(full_key)

    async def set(
        self, family: str, key: str, value: str, expiry_seconds: int | None = None
    ) -> None:
        """Set a value by family and key with optional expiry."""
        full_key = f"{family}:{key}"
        self._store[full_key] = value
        # Note: expiry_seconds is ignored in this simple in-memory implementation

    async def get_and_set(
        self, key: str, subkey: str, value_factory, expiry_seconds: int | None = None
    ):
        """Get and set implementation backed by a dictionary."""
        full_key = f"{key}:{subkey}"

        # Check if the key exists (simulating duplicate detection)
        current_value = self._store.get(full_key)

        # Call the value_factory with the current value
        new_value = value_factory(current_value)

        # Store the new value
        self._store[full_key] = new_value

        return new_value

    async def get_channel_id(self, channel_name: str) -> str | None:
        """Get the channel ID for a given channel name."""
        # Normalize channel name (lowercase, strip whitespace and # prefix)
        normalized_name = channel_name.lower().strip().strip("#")
        full_key = f"channel_name_to_id:{normalized_name}"
        return self._store.get(full_key)


class TestCheckAndBumpAnswerQuotas:
    """Test scaffold for check_and_bump_answer_quotas function."""

    @pytest.fixture
    def kv_store(self):
        """Create a dictionary-backed kv_store for realistic testing."""
        return DictBackedKVStore()

    @pytest.fixture
    def bot(self, kv_store):
        """Create bot instance with mocked dependencies."""
        mock_logger = Mock()
        mock_client = AsyncMock()
        mock_github_config = Mock()
        mock_local_context_store = Mock()

        # Create a proper mock for AIConfig (which is AnthropicConfig | OpenAIConfig)
        mock_ai_config = Mock()
        mock_ai_config.provider = "anthropic"
        mock_ai_config.api_key = Mock()
        mock_ai_config.api_key.get_secret_value.return_value = "test-api-key"
        mock_ai_config.model = "claude-sonnet-4-20250514"

        mock_analytics_store = Mock()
        mock_profile = Mock()
        mock_csbot_client = Mock()
        mock_github_monitor = Mock()
        mock_bot_config = Mock()

        # Create a proper bot_type instance
        bot_type = BotTypeQA()

        # Create the bot instance with mocked dependencies and test quotas
        return MockCommunityBotInstance(
            key=Mock(),
            logger=mock_logger,
            github_config=mock_github_config,
            local_context_store=mock_local_context_store,
            client=mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=mock_ai_config,
            kv_store=kv_store,  # type: ignore
            governance_alerts_channel="test-channel",
            analytics_store=mock_analytics_store,
            profile=mock_profile,
            csbot_client=mock_csbot_client,
            data_request_github_creds=mock_github_config,
            slackbot_github_monitor=mock_github_monitor,
            scaffold_branch_enabled=False,
            bot_config=mock_bot_config,
            bot_type=bot_type,
            server_config=Mock(),
            storage=Mock(),
            issue_creator=AsyncMock(),
            # Test quotas for community mode
            max_answers_per_user_24h=5,
            max_answers_per_user_7d=10,
            max_answers_per_bot_24h=20,
        )

    @pytest.mark.asyncio
    async def test_check_and_bump_answer_quotas_smoke(self, bot):
        """Test scaffold for check_and_bump_answer_quotas - basic functionality test."""

        now = 0

        async def bump(user: str, seconds_delta: int = 1) -> QuotaCheckResult:
            nonlocal now
            now += seconds_delta
            return await bot.check_and_bump_answer_quotas(now, bot, user)

        for _ in range(5):
            assert await bump("user1") == QuotaCheckResult.OK

        assert await bump("user1") == QuotaCheckResult.USER_24H_QUOTA_EXCEEDED

        for _ in range(5):
            assert await bump("user2") == QuotaCheckResult.OK

        assert await bump("user2") == QuotaCheckResult.USER_24H_QUOTA_EXCEEDED

        # advance the clock a day
        now += 24 * 60 * 60
        for _ in range(5):
            assert await bump("user1") == QuotaCheckResult.OK

        assert await bump("user1") == QuotaCheckResult.USER_24H_QUOTA_EXCEEDED

        # advance the clock another day. this user has consumed their
        # weekly quota
        now += 24 * 60 * 60
        assert await bump("user1") == QuotaCheckResult.USER_7D_QUOTA_EXCEEDED

        # advance the clock a week, they have some quota again
        now += 7 * 24 * 60 * 60
        for _ in range(5):
            assert await bump("user1") == QuotaCheckResult.OK

        assert await bump("user1") == QuotaCheckResult.USER_24H_QUOTA_EXCEEDED

        # next we test that many users cannot exceed the 24h quota
        # of 20 messages

        # first advance to a fresh week
        now += 7 * 24 * 60 * 60
        for _ in range(4):
            assert await bump("user1") == QuotaCheckResult.OK
            assert await bump("user2") == QuotaCheckResult.OK
            assert await bump("user3") == QuotaCheckResult.OK
            assert await bump("user4") == QuotaCheckResult.OK
            assert await bump("user5") == QuotaCheckResult.OK

        assert await bump("user1") == QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED
        assert await bump("user2") == QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED
        assert await bump("user3") == QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED
        assert await bump("user4") == QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED
        assert await bump("user5") == QuotaCheckResult.BOT_24H_QUOTA_EXCEEDED

        # next day the quota is back
        now += 24 * 60 * 60
        assert await bump("user1") == QuotaCheckResult.OK
        assert await bump("user2") == QuotaCheckResult.OK
        assert await bump("user3") == QuotaCheckResult.OK
        assert await bump("user4") == QuotaCheckResult.OK
        assert await bump("user5") == QuotaCheckResult.OK
