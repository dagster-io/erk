"""
Unit tests for usage monitoring functionality.

Note: Slow integration tests (test_bonus_answers.py, test_data_retention.py)
have been moved to tests/integration/usage_monitoring/ as they use real
database infrastructure and test end-to-end behavior.

This subpackage contains focused test modules for usage monitoring functionality:

Test Modules:
- test_limits.py: Plan limit checking and enforcement (6 tests)
- test_streaming.py: Streaming reply usage logging (3 tests)
- test_governance.py: Governance channel warning behavior (3 tests)
- test_schema.py: Usage tracking table schema validation (3 tests)
- test_analytics_store.py: Analytics store operations and organization methods (15 tests)
- test_tracker.py: UsageTracker functionality (3 tests)
- test_cli.py: Usage tracking CLI commands (1 test)
- test_error_handling.py: Error handling scenarios (3 tests)

Shared Utilities:
- tests.usage_monitoring_helpers: Helper functions for bonus answer setup and consumption

Running Tests:
    # Run all usage monitoring tests
    cd packages/csbot && uv run pytest tests/usage_monitoring/ -v

    # Run specific module
    cd packages/csbot && uv run pytest tests/usage_monitoring/test_bonus_answers.py -v

    # Run with timing analysis
    cd packages/csbot && uv run pytest tests/usage_monitoring/ --durations=50

    # Run in parallel
    cd packages/csbot && uv run pytest tests/usage_monitoring/ -n auto

Fixtures:
All tests use fixtures from tests/conftest.py:
- compass_bot_instance: Standard bot with method mocks
- bonus_test_bot_with_db: Bot with real database-backed storage
- real_analytics_store: Real analytics store for DB tests
- mock_analytics_store: Mock analytics store for unit tests
- sql_conn_factory_transactional: Transactional connection factory

See tests/conftest.py for complete fixture documentation.
"""
