"""Tests for debug_timing module."""

import logging

import pytest
from erk_shared.debug_timing import log_graphql_query, timed_operation


def test_timed_operation_logs_start_and_completion(caplog: pytest.LogCaptureFixture) -> None:
    """Verify timed_operation logs start and completion with timing."""
    with caplog.at_level(logging.DEBUG):
        with timed_operation("test operation"):
            pass

    assert len(caplog.records) == 2
    assert "Starting: test operation" in caplog.records[0].message
    assert "Completed in" in caplog.records[1].message
    assert "test operation" in caplog.records[1].message


def test_timed_operation_logs_timing_on_exception(caplog: pytest.LogCaptureFixture) -> None:
    """Verify timed_operation logs completion even when exception occurs."""
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError, match="test error"):
            with timed_operation("failing operation"):
                raise ValueError("test error")

    assert len(caplog.records) == 2
    assert "Starting: failing operation" in caplog.records[0].message
    assert "Completed in" in caplog.records[1].message
    assert "failing operation" in caplog.records[1].message


def test_log_graphql_query_preserves_multiline(caplog: pytest.LogCaptureFixture) -> None:
    """Verify log_graphql_query preserves multi-line query content."""
    query = "query {\n  repository {\n    name\n  }\n}"

    with caplog.at_level(logging.DEBUG):
        log_graphql_query(query)

    assert len(caplog.records) == 1
    assert "GraphQL query:" in caplog.records[0].message
    assert "repository" in caplog.records[0].message


def test_log_graphql_query_single_line(caplog: pytest.LogCaptureFixture) -> None:
    """Verify log_graphql_query works with single-line queries."""
    query = "query { viewer { login } }"

    with caplog.at_level(logging.DEBUG):
        log_graphql_query(query)

    assert len(caplog.records) == 1
    assert "GraphQL query:" in caplog.records[0].message
    assert "viewer" in caplog.records[0].message
