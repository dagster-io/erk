"""Tests for pr_data_parsing pure parsing functions."""

from datetime import UTC, datetime
from typing import Any

from erk_shared.gateway.github.pr_data_parsing import (
    merge_rest_graphql_pr_data,
    parse_mergeable_status,
    parse_review_thread_counts,
    parse_status_rollup,
    parse_workflow_runs_nodes_response,
)
from erk_shared.gateway.github.types import GitHubRepoId

# ============================================================================
# parse_status_rollup
# ============================================================================


def test_parse_status_rollup_none_returns_none_pair() -> None:
    """None input returns (None, None)."""
    assert parse_status_rollup(None) == (None, None)


def test_parse_status_rollup_success() -> None:
    """SUCCESS state returns checks_passing=True."""
    checks_passing, _ = parse_status_rollup({"state": "SUCCESS"})
    assert checks_passing is True


def test_parse_status_rollup_failure() -> None:
    """FAILURE state returns checks_passing=False."""
    checks_passing, _ = parse_status_rollup({"state": "FAILURE"})
    assert checks_passing is False


def test_parse_status_rollup_error() -> None:
    """ERROR state returns checks_passing=False."""
    checks_passing, _ = parse_status_rollup({"state": "ERROR"})
    assert checks_passing is False


def test_parse_status_rollup_pending_returns_none() -> None:
    """PENDING state returns checks_passing=None."""
    checks_passing, _ = parse_status_rollup({"state": "PENDING"})
    assert checks_passing is None


def test_parse_status_rollup_no_contexts_returns_none_counts() -> None:
    """Missing contexts returns None for checks_counts."""
    _, checks_counts = parse_status_rollup({"state": "SUCCESS"})
    assert checks_counts is None


# ============================================================================
# parse_mergeable_status
# ============================================================================


def test_parse_mergeable_conflicting() -> None:
    """CONFLICTING returns True (has conflicts)."""
    assert parse_mergeable_status("CONFLICTING") is True


def test_parse_mergeable_mergeable() -> None:
    """MERGEABLE returns False (no conflicts)."""
    assert parse_mergeable_status("MERGEABLE") is False


def test_parse_mergeable_unknown() -> None:
    """UNKNOWN returns None."""
    assert parse_mergeable_status("UNKNOWN") is None


def test_parse_mergeable_none() -> None:
    """None input returns None."""
    assert parse_mergeable_status(None) is None


# ============================================================================
# parse_review_thread_counts
# ============================================================================


def test_parse_review_thread_counts_none() -> None:
    """None input returns None."""
    assert parse_review_thread_counts(None) is None


def test_parse_review_thread_counts_zero_total() -> None:
    """Zero totalCount returns (0, 0)."""
    assert parse_review_thread_counts({"totalCount": 0}) == (0, 0)


def test_parse_review_thread_counts_with_resolved() -> None:
    """Counts resolved threads correctly."""
    data = {
        "totalCount": 3,
        "nodes": [
            {"isResolved": True},
            {"isResolved": False},
            {"isResolved": True},
        ],
    }
    assert parse_review_thread_counts(data) == (2, 3)


def test_parse_review_thread_counts_all_unresolved() -> None:
    """All unresolved returns (0, total)."""
    data = {
        "totalCount": 2,
        "nodes": [{"isResolved": False}, {"isResolved": False}],
    }
    assert parse_review_thread_counts(data) == (0, 2)


def test_parse_review_thread_counts_skips_none_nodes() -> None:
    """None nodes are skipped."""
    data = {
        "totalCount": 2,
        "nodes": [None, {"isResolved": True}],
    }
    assert parse_review_thread_counts(data) == (1, 2)


# ============================================================================
# parse_workflow_runs_nodes_response
# ============================================================================


def test_parse_workflow_runs_completed_success() -> None:
    """Completed+success maps correctly."""
    response: dict[str, Any] = {
        "data": {
            "nodes": [
                {
                    "id": "WFR_1",
                    "databaseId": 123,
                    "createdAt": "2024-01-15T10:00:00Z",
                    "checkSuite": {
                        "status": "COMPLETED",
                        "conclusion": "SUCCESS",
                        "commit": {"oid": "abc123"},
                    },
                }
            ]
        }
    }
    result = parse_workflow_runs_nodes_response(response, ["WFR_1"])
    run = result["WFR_1"]
    assert run is not None
    assert run.status == "completed"
    assert run.conclusion == "success"
    assert run.head_sha == "abc123"
    assert run.run_id == "123"


def test_parse_workflow_runs_in_progress() -> None:
    """In-progress maps correctly."""
    response: dict[str, Any] = {
        "data": {
            "nodes": [
                {
                    "id": "WFR_2",
                    "databaseId": 456,
                    "checkSuite": {"status": "IN_PROGRESS", "conclusion": None},
                }
            ]
        }
    }
    result = parse_workflow_runs_nodes_response(response, ["WFR_2"])
    run = result["WFR_2"]
    assert run is not None
    assert run.status == "in_progress"
    assert run.conclusion is None


def test_parse_workflow_runs_missing_node_returns_none() -> None:
    """Requested node_id not in response gets None."""
    response: dict[str, Any] = {"data": {"nodes": []}}
    result = parse_workflow_runs_nodes_response(response, ["WFR_missing"])
    assert result["WFR_missing"] is None


def test_parse_workflow_runs_null_node_skipped() -> None:
    """Null nodes in response are skipped."""
    response: dict[str, Any] = {"data": {"nodes": [None]}}
    result = parse_workflow_runs_nodes_response(response, ["WFR_1"])
    assert result["WFR_1"] is None


def test_parse_workflow_runs_failure_conclusion() -> None:
    """FAILURE conclusion maps to 'failure'."""
    response: dict[str, Any] = {
        "data": {
            "nodes": [
                {
                    "id": "WFR_3",
                    "databaseId": 789,
                    "checkSuite": {"status": "COMPLETED", "conclusion": "FAILURE"},
                }
            ]
        }
    }
    result = parse_workflow_runs_nodes_response(response, ["WFR_3"])
    assert result["WFR_3"] is not None
    assert result["WFR_3"].conclusion == "failure"


def test_parse_workflow_runs_cancelled_conclusion() -> None:
    """CANCELLED conclusion maps to 'cancelled'."""
    response: dict[str, Any] = {
        "data": {
            "nodes": [
                {
                    "id": "WFR_4",
                    "databaseId": 101,
                    "checkSuite": {"status": "COMPLETED", "conclusion": "CANCELLED"},
                }
            ]
        }
    }
    result = parse_workflow_runs_nodes_response(response, ["WFR_4"])
    assert result["WFR_4"] is not None
    assert result["WFR_4"].conclusion == "cancelled"


def test_parse_workflow_runs_created_at_parsed() -> None:
    """createdAt is parsed into datetime."""
    response: dict[str, Any] = {
        "data": {
            "nodes": [
                {
                    "id": "WFR_5",
                    "databaseId": 200,
                    "createdAt": "2024-06-01T12:30:00Z",
                    "checkSuite": {"status": "COMPLETED", "conclusion": "SUCCESS"},
                }
            ]
        }
    }
    result = parse_workflow_runs_nodes_response(response, ["WFR_5"])
    run = result["WFR_5"]
    assert run is not None
    assert run.created_at == datetime(2024, 6, 1, 12, 30, 0, tzinfo=UTC)


# ============================================================================
# merge_rest_graphql_pr_data (basic tests beyond integration tests)
# ============================================================================


def _make_rest_item(
    *,
    number: int,
    title: str = "Test PR",
    state: str = "open",
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "html_url": f"https://github.com/test/repo/pull/{number}",
        "body": "PR body",
        "state": state,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T14:00:00Z",
        "labels": [],
        "user": {"login": "test-user"},
        "pull_request": {"head": {"ref": "feature"}},
    }


def test_merge_empty_items() -> None:
    """Empty input returns empty output."""
    repo_id = GitHubRepoId(owner="o", repo="r")
    details, linkages, unenriched_count = merge_rest_graphql_pr_data([], {}, repo_id)
    assert details == []
    assert linkages == {}
    assert unenriched_count == 0


def test_merge_without_enrichment_skips_pr_linkage() -> None:
    """Missing GraphQL enrichment creates PRDetails but skips PullRequestInfo linkage."""
    repo_id = GitHubRepoId(owner="o", repo="r")
    items = [_make_rest_item(number=42)]

    details, linkages, unenriched_count = merge_rest_graphql_pr_data(items, {}, repo_id)

    assert len(details) == 1
    assert details[0].mergeable == "UNKNOWN"
    assert details[0].is_draft is False
    # Unenriched PRs are excluded from pr_linkages to avoid misleading defaults
    assert 42 not in linkages
    assert unenriched_count == 1
