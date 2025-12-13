"""
Integration tests for usage monitoring functionality.

These are integration tests that use real database infrastructure and test
end-to-end behavior from bot methods through to database state. They are
expected to be slower than unit tests (seconds vs milliseconds).

Test files:
- test_bonus_answers.py: Uses PostgreSQL via testcontainers, creates actual
  organizations in database (~1-2s setup), tests end-to-end bot behavior
- test_data_retention.py: Uses SQLite with real persistence, has explicit
  asyncio.sleep(1.1) for timestamp verification

These tests were moved from tests/usage_monitoring/ to separate them from
fast unit tests, allowing the unit test suite to run quickly while preserving
comprehensive integration test coverage.
"""
