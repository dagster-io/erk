"""Pytest configuration for csbot tests."""

import os
import warnings

import pytest
from testcontainers.postgres import PostgresContainer

from tests.utils.postgres_utils import wait_for_startup

# Suppress testcontainers deprecation warnings
# The @wait_container_is_ready decorator is deprecated in testcontainers library
# We don't control this code and the library maintainers will fix it
warnings.filterwarnings(
    "ignore",
    message="The @wait_container_is_ready decorator is deprecated.*",
    category=DeprecationWarning,
    module="testcontainers.*",
)

# Suppress aiomonitor click deprecation warning
# aiomonitor uses click.get_terminal_size() which is deprecated
# This is only used in development and aiomonitor will fix it upstream
warnings.filterwarnings(
    "ignore",
    message=".*click.get_terminal_size.*",
    category=DeprecationWarning,
)


def pytest_addoption(parser):
    """Add custom command line options for snapshot testing."""
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="Update snapshot files instead of comparing against them",
    )
    parser.addoption(
        "--view",
        action="store_true",
        default=False,
        help="Open generated HTML snapshots in the browser for visual inspection",
    )


def pytest_configure(config):
    """Configure pytest with environment variables for snapshot testing."""
    # Set environment variables based on CLI flags so they're available everywhere
    if config.getoption("--snapshot-update"):
        os.environ["PYTEST_SNAPSHOT_UPDATE"] = "1"
    if config.getoption("--view"):
        os.environ["PYTEST_SNAPSHOT_VIEW"] = "1"


@pytest.fixture
def snapshot_update(request):
    """Fixture that provides the --snapshot-update flag value."""
    return request.config.getoption("--snapshot-update")


@pytest.fixture
def snapshot_view(request):
    """Fixture that provides the --view flag value."""
    return request.config.getoption("--view")


@pytest.fixture(scope="session")
def postgres_container():
    """Session-scoped PostgreSQL container for testing."""
    if test_db_url := os.environ.get("TEST_DATABASE_URL"):
        if test_db_url.startswith("postgresql://"):
            yield test_db_url
            return
    container = PostgresContainer(
        image="public.ecr.aws/docker/library/postgres:16-alpine3.21",
        username="test",
        password="test",
        dbname="test_db",
        driver="psycopg",
    )
    with container:
        # Wait for PostgreSQL to be ready to accept connections
        # The container's start() method has a built-in readiness check,
        # but we add an explicit verification step
        database_url = container.get_connection_url()
        wait_for_startup(database_url)
        os.environ["TEST_DATABASE_URL"] = database_url
        yield database_url
        del os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def db_schema_session(postgres_container, tmp_path_factory):
    """
    Session-scoped fixture that initializes database schema once.
    All tables, indexes, and constraints are created at test session start.

    This eliminates repeated schema creation overhead across 30+ PostgreSQL tests.

    Uses file locking to prevent race conditions when running with pytest-xdist.
    Only one worker initializes the schema; others wait for completion.
    """
    from csbot.slackbot.config import DatabaseConfig
    from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory
    from csbot.slackbot.storage.schema_changes import SchemaManager

    # Create connection factory from database URL
    conn_factory = PostgresqlConnectionFactory.from_db_config(
        DatabaseConfig.from_uri(postgres_container)
    )

    # Use file locking to ensure only one worker initializes the schema
    # tmp_path_factory.getbasetemp() returns a path shared across all workers
    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    schema_lock_file = root_tmp_dir / "db_schema_init.lock"
    schema_done_file = root_tmp_dir / "db_schema_done"

    # Use filelock for cross-process synchronization
    from filelock import FileLock

    lock = FileLock(str(schema_lock_file))

    with lock:
        if not schema_done_file.exists():
            # This worker won the race - initialize the schema
            with conn_factory.with_conn() as conn:
                schema_manager = SchemaManager()
                schema_manager.apply_all_changes(conn)
                conn.commit()

            # Mark schema as initialized
            schema_done_file.write_text("initialized")
        # else: Another worker already initialized the schema

    yield conn_factory

    # Cleanup not needed - container destroyed at session end


@pytest.fixture
def db_transaction(db_schema_session):
    """
    Function-scoped fixture wrapping each test in a database transaction.

    All database changes within the test are automatically rolled back,
    providing perfect isolation without DELETE or DROP operations.

    Rollback is ~100x faster than DELETE (0.001s vs 0.05-0.1s per test).
    """
    from contextlib import contextmanager

    # Get a connection from the pool via the connection factory
    with db_schema_session.with_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        # Wrap cursor to intercept explicit transaction SQL commands
        class CursorWrapper:
            def __init__(self, wrapped_cursor):
                self._cursor = wrapped_cursor

            def __getattr__(self, name):
                return getattr(self._cursor, name)

            def execute(self, query, *args, **kwargs):
                # Intercept explicit transaction commands and make them no-ops
                query_normalized = query.strip().upper() if isinstance(query, str) else ""
                if query_normalized in ("BEGIN", "COMMIT", "ROLLBACK"):
                    # No-op: ignore explicit transaction commands within test transaction
                    return
                return self._cursor.execute(query, *args, **kwargs)

        # Wrap connection to intercept commit() and rollback() calls
        class ConnectionWrapper:
            def __init__(self, wrapped_conn):
                self._conn = wrapped_conn

            def __getattr__(self, name):
                return getattr(self._conn, name)

            def commit(self):
                # No-op: don't commit within test transaction
                # Changes are visible within the transaction without commit
                pass

            def rollback(self):
                # No-op: don't rollback within test transaction
                # The outer ROLLBACK will handle everything
                pass

            def cursor(self):
                # Return wrapped cursor that intercepts transaction commands
                return CursorWrapper(self._conn.cursor())

        conn_wrapper = ConnectionWrapper(conn)

        # Create a wrapper that returns the same connection every time
        @contextmanager
        def transactional_conn():
            yield conn_wrapper

        # Create a connection factory wrapper that delegates to the underlying factory
        # but returns our transactional connection
        # This preserves isinstance() checks for database type detection
        class TransactionalConnectionFactory(type(db_schema_session)):
            def __init__(self, underlying_factory):
                self._underlying_factory = underlying_factory

            def with_conn(self):
                return transactional_conn()

            @property
            def seconds_now(self):
                return self._underlying_factory.seconds_now

            def supports_analytics(self) -> bool:
                """Check if the connection factory supports analytics."""
                return self._underlying_factory.supports_analytics()

        yield TransactionalConnectionFactory(db_schema_session)

        # Rollback happens automatically, even on test failure
        cursor.execute("ROLLBACK")


@pytest.fixture
def sql_conn_factory_transactional(db_transaction):
    """
    Provides connection factory operating within test transaction.

    Drop-in replacement for sql_conn_factory fixture in transactional tests.
    Maintains backward compatibility while enabling transaction isolation.
    """
    return db_transaction


# ============================================================================
# Bot Instance Fixtures for Usage Monitoring Tests
# ============================================================================


@pytest.fixture
def mock_bot_key():
    """
    Provides a mock bot key with to_bot_id() method.

    Returns a Mock object that can be used as a bot key in tests.
    The default bot_id is 'test-bot', but can be customized by setting
    mock_bot_key.to_bot_id.return_value in your test.

    Example:
        def test_something(mock_bot_key):
            mock_bot_key.to_bot_id.return_value = "custom-bot-id"
    """
    from unittest.mock import Mock

    mock_key = Mock()
    mock_key.to_bot_id.return_value = "test-bot"
    return mock_key


@pytest.fixture
def mock_analytics_store():
    """
    Provides an AsyncMock for SlackbotAnalyticsStore.

    Use this when tests don't need real database-backed analytics.
    For database-backed analytics, use real_analytics_store fixture.

    Example:
        async def test_something(compass_bot_instance, mock_analytics_store):
            # Mock analytics calls
            mock_analytics_store.increment_usage.return_value = None
    """
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.fixture
def mock_bot_storage():
    """
    Provides an AsyncMock for bot storage with default get_plan_limits behavior.

    By default, get_plan_limits returns None (no limits).
    Override in tests to return PlanLimits objects for limit testing.

    Example:
        async def test_with_limits(compass_bot_instance, mock_bot_storage):
            from csbot.slackbot.storage.interface import PlanLimits
            mock_bot_storage.get_plan_limits.return_value = PlanLimits(...)
    """
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.get_plan_limits.return_value = None
    return mock


@pytest.fixture
def mock_bot_config(mock_bot_key):
    """
    Provides a Mock for bot configuration with organization_id = 123.

    Override organization_id in tests if needed by setting:
        mock_bot_config.organization_id = your_org_id

    Example:
        def test_something(mock_bot_config, bonus_test_organization_id):
            mock_bot_config.organization_id = bonus_test_organization_id
    """
    from unittest.mock import Mock

    config = Mock()
    config.organization_id = 123
    return config


@pytest.fixture
def mock_server_config():
    """
    Provides a Mock for CompassBotServerConfig with thread_health_inspector_config = None.

    This is the minimal server config needed for most tests.
    """
    from unittest.mock import Mock

    from csbot.slackbot.slackbot_core import CompassBotServerConfig

    config = Mock(spec=CompassBotServerConfig)
    config.thread_health_inspector_config = None
    return config


@pytest.fixture
def compass_bot_instance_factory(
    mock_bot_key, mock_analytics_store, mock_bot_storage, mock_bot_config, mock_server_config
):
    """
    Factory fixture that creates CompassChannelQANormalBotInstance with customizable parameters.

    Returns a callable that accepts **overrides to customize any constructor argument.
    Use this when you need to override specific arguments (e.g., use real_analytics_store).

    Args (defaults provided):
        key: Bot key (mock_bot_key)
        logger: Mock logger
        github_config: Mock GitHub config
        local_context_store: Mock context store
        client: AsyncMock Slack client
        bot_background_task_manager: AsyncMock task manager
        ai_config: AnthropicConfig with test settings
        kv_store: AsyncMock key-value store
        governance_alerts_channel: "governance"
        analytics_store: mock_analytics_store fixture
        profile: Mock profile
        csbot_client: Mock csbot client
        data_request_github_creds: Mock GitHub credentials
        slackbot_github_monitor: Mock GitHub monitor
        scaffold_branch_enabled: False
        bot_config: mock_bot_config fixture
        bot_type: BotTypeQA()
        server_config: mock_server_config fixture
        storage: mock_bot_storage fixture
        issue_creator: GithubIssueCreator(Mock())

    Example:
        def test_with_real_analytics(compass_bot_instance_factory, real_analytics_store):
            bot = compass_bot_instance_factory(analytics_store=real_analytics_store)

        def test_with_real_storage(compass_bot_instance_factory, real_bot_storage):
            bot = compass_bot_instance_factory(storage=real_bot_storage)
    """
    from unittest.mock import AsyncMock, Mock

    from pydantic import SecretStr

    from csbot.slackbot.channel_bot.bot import (
        BotTypeQA,
        CompassChannelQANormalBotInstance,
    )
    from csbot.slackbot.issue_creator.github import GithubIssueCreator
    from csbot.slackbot.slackbot_core import AnthropicConfig

    def create_bot(**overrides):
        defaults = {
            "key": mock_bot_key,
            "logger": Mock(),
            "github_config": Mock(),
            "local_context_store": Mock(),
            "client": AsyncMock(),
            "bot_background_task_manager": AsyncMock(),
            "ai_config": AnthropicConfig(
                provider="anthropic",
                api_key=SecretStr("test_api_key"),
                model="claude-sonnet-4-20250514",
            ),
            "kv_store": AsyncMock(),
            "governance_alerts_channel": "governance",
            "analytics_store": mock_analytics_store,
            "profile": Mock(),
            "csbot_client": Mock(),
            "data_request_github_creds": Mock(),
            "slackbot_github_monitor": Mock(),
            "scaffold_branch_enabled": False,
            "bot_config": mock_bot_config,
            "bot_type": BotTypeQA(),
            "server_config": mock_server_config,
            "storage": mock_bot_storage,
            "issue_creator": GithubIssueCreator(Mock()),
        }
        defaults.update(overrides)
        return CompassChannelQANormalBotInstance(**defaults)

    return create_bot


@pytest.fixture
def compass_bot_instance(compass_bot_instance_factory):
    """
    Provides a standard CompassChannelQANormalBotInstance with all common method mocks applied.

    This is the most commonly used bot fixture. It includes mocks for:
    - get_system_prompt() -> "System prompt"
    - get_tools_for_message() -> {}
    - _handle_claude_error() -> None
    - _stream_claude_response() -> AsyncMock()
    - _warn_plan_limit_reached_no_overages() -> None
    - _possibly_warn_plan_limit_reached_overages() -> None
    - _send_governance_plan_limit_warning() -> None

    Use this fixture for most tests. For custom bot configuration,
    use compass_bot_instance_factory directly.

    Example:
        async def test_something(compass_bot_instance):
            # Bot ready to use with all standard mocks
            await compass_bot_instance.process_message(...)
    """
    from unittest.mock import AsyncMock

    bot = compass_bot_instance_factory()

    # Apply standard method mocks
    bot.get_system_prompt = AsyncMock(return_value="System prompt")
    bot.get_tools_for_message = AsyncMock(return_value={})
    bot._handle_claude_error = AsyncMock()
    bot._stream_claude_response = AsyncMock()
    bot._warn_plan_limit_reached_no_overages = AsyncMock()
    bot._possibly_warn_plan_limit_reached_overages = AsyncMock()
    bot._send_governance_plan_limit_warning = AsyncMock()

    return bot


@pytest.fixture(scope="module")
def bonus_test_organization_id(db_schema_session):
    """
    Module-scoped fixture that creates a test organization once per test module.

    This is THE KEY OPTIMIZATION for TestBonusAnswerUsage tests.
    Organization creation is expensive (~1-2 seconds), so we create it once
    and reuse across all tests in the module. Transactional isolation ensures
    test independence despite shared organization.

    Returns:
        int: Organization ID that can be used across multiple tests

    Example:
        def test_something(bonus_test_organization_id, sql_conn_factory_transactional):
            # Use bonus_test_organization_id in your test
            # Each test still gets isolated via transaction
    """
    import asyncio

    from csbot.slackbot.config import UnsupportedKekConfig
    from csbot.slackbot.envelope_encryption import KekProvider
    from csbot.slackbot.storage.postgresql import SlackbotPostgresqlStorage

    kek_provider = KekProvider(UnsupportedKekConfig())
    postgres_storage = SlackbotPostgresqlStorage(db_schema_session, kek_provider)

    org_id = asyncio.run(
        postgres_storage.create_organization(
            name="Test Organization Bonus",
            industry="Software",
            has_governance_channel=True,
            contextstore_github_repo="test/repo",
        )
    )

    # Also create bot instance in database for bonus answer queries
    asyncio.run(
        postgres_storage.create_bot_instance(
            channel_name="bot_bonus",
            governance_alerts_channel="governance",
            contextstore_github_repo="test/repo",
            slack_team_id="test",
            bot_email="test@example.com",
            organization_id=org_id,
        )
    )

    return org_id


@pytest.fixture
def real_analytics_store(sql_conn_factory_transactional):
    """
    Provides a real SlackbotAnalyticsStore backed by transactional database.

    Use this when tests need to verify actual database operations for analytics.
    All changes are rolled back after the test completes.

    Example:
        async def test_usage_tracking(real_analytics_store, sql_conn_factory_transactional):
            await real_analytics_store.increment_usage(...)
            count = await real_analytics_store.get_usage_count(...)
            assert count == 1
    """
    from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore

    return SlackbotAnalyticsStore(sql_conn_factory_transactional)


@pytest.fixture
def real_bot_storage(sql_conn_factory_transactional, mock_bot_key):
    """
    Provides a real SlackbotInstancePostgresqlStorage backed by transactional database.

    Use this when tests need to verify actual storage operations.
    All changes are rolled back after the test completes.

    Example:
        async def test_plan_limits(real_bot_storage):
            limits = await real_bot_storage.get_plan_limits()
            assert limits is not None
    """
    from unittest.mock import Mock

    from csbot.slackbot.storage.postgresql import SlackbotInstancePostgresqlStorage

    return SlackbotInstancePostgresqlStorage(
        sql_conn_factory_transactional, Mock(), mock_bot_key.to_bot_id()
    )


@pytest.fixture
def bonus_test_bot_with_db(
    compass_bot_instance_factory,
    real_analytics_store,
    real_bot_storage,
    bonus_test_organization_id,
    mock_bot_key,
    mock_bot_config,
):
    """
    Provides a bot instance configured with real database-backed storage and analytics.

    This fixture combines the factory with real stores and applies standard method mocks.
    Returns a tuple of (bot, org_id) for use in bonus answer tests.

    The bot_id is configured as "test-bot_bonus" to match the database bot instance
    created in bonus_test_organization_id.

    Returns:
        tuple[CompassChannelQANormalBotInstance, int]: (bot instance, organization ID)

    Example:
        @pytest.mark.asyncio
        async def test_bonus_answers(bonus_test_bot_with_db, real_analytics_store):
            bot, org_id = bonus_test_bot_with_db
            # Bot has real storage and analytics
            await bot.streaming_reply_to_thread_with_ai(...)
    """
    from unittest.mock import AsyncMock

    # Configure mock_bot_key to return the correct bot_id
    mock_bot_key.to_bot_id.return_value = "test-bot_bonus"

    # Configure mock_bot_config with the real organization_id
    mock_bot_config.organization_id = bonus_test_organization_id

    # Create bot with real stores
    bot = compass_bot_instance_factory(
        key=mock_bot_key,
        analytics_store=real_analytics_store,
        storage=real_bot_storage,
        bot_config=mock_bot_config,
    )

    # Apply standard method mocks
    bot.get_system_prompt = AsyncMock(return_value="System prompt")
    bot.get_tools_for_message = AsyncMock(return_value={})
    bot._handle_claude_error = AsyncMock()
    bot._stream_claude_response = AsyncMock()
    bot._warn_plan_limit_reached_no_overages = AsyncMock()
    bot._possibly_warn_plan_limit_reached_overages = AsyncMock()
    bot._send_governance_plan_limit_warning = AsyncMock()

    return bot, bonus_test_organization_id


@pytest.fixture
def mock_billing_url():
    """
    Context manager fixture that patches billing URL creation for governance channel tests.

    Returns a mock configured to return 'https://example.com/billing/test-token'.

    Use this fixture with async context manager syntax when testing governance warnings.

    Example:
        async def test_governance_warning(compass_bot_instance, mock_billing_url):
            with mock_billing_url:
                # Test code that uses billing URL
                await bot.send_governance_warning(...)
    """
    from unittest.mock import patch

    with patch("csbot.slackbot.channel_bot.bot.create_billing_url") as mock:
        mock.return_value = "https://example.com/billing/test-token"
        yield mock
