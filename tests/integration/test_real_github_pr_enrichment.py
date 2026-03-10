"""Tests for RealLocalGitHub PR enrichment methods.

Tests _enrich_prs_via_graphql() and _merge_rest_graphql_pr_data() which
combine REST and GraphQL data for the plan dashboard.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

from erk_shared.gateway.github.pr_data_parsing import merge_rest_graphql_pr_data
from erk_shared.gateway.github.types import GitHubRepoId, GitHubRepoLocation
from tests.integration.test_helpers import mock_subprocess_run
from tests.test_utils.context_builders import real_github_for_test

# ============================================================================
# _enrich_prs_via_graphql() Tests
# ============================================================================


def _make_graphql_pr_node(
    *,
    is_draft: bool = False,
    mergeable: str = "MERGEABLE",
    merge_state_status: str = "CLEAN",
    head_ref_name: str = "feature-branch",
    base_ref_name: str = "main",
    checks_state: str = "SUCCESS",
    total_checks: int = 5,
    resolved_threads: int = 2,
    total_threads: int = 3,
    review_decision: str = "APPROVED",
) -> dict[str, Any]:
    """Build a realistic GraphQL PR node for test fixtures."""
    return {
        "isDraft": is_draft,
        "mergeable": mergeable,
        "mergeStateStatus": merge_state_status,
        "isCrossRepository": False,
        "baseRefName": base_ref_name,
        "headRefName": head_ref_name,
        "statusCheckRollup": {
            "state": checks_state,
            "contexts": {
                "totalCount": total_checks,
                "checkRunCountsByState": [{"state": "SUCCESS", "count": total_checks}],
                "statusContextCountsByState": [],
            },
        },
        "reviewThreads": {
            "totalCount": total_threads,
            "nodes": [{"isResolved": i < resolved_threads} for i in range(total_threads)],
        },
        "reviewDecision": review_decision,
    }


def test_enrich_prs_via_graphql_single_pr(monkeypatch: MonkeyPatch) -> None:
    """Enriching a single PR returns its GraphQL data keyed by number."""
    location = GitHubRepoLocation(
        root=Path("/repo"),
        repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
    )
    pr_node = _make_graphql_pr_node(head_ref_name="my-branch")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        response = {"data": {"repository": {"pr_42": pr_node}}}
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(response), stderr=""
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = real_github_for_test()
        result = ops._enrich_prs_via_graphql(location, [42])

    assert 42 in result
    assert result[42]["headRefName"] == "my-branch"
    assert result[42]["isDraft"] is False


def test_enrich_prs_via_graphql_multiple_prs(monkeypatch: MonkeyPatch) -> None:
    """Enriching multiple PRs returns all of them in a single call."""
    location = GitHubRepoLocation(
        root=Path("/repo"),
        repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
    )
    node_10 = _make_graphql_pr_node(head_ref_name="branch-10")
    node_20 = _make_graphql_pr_node(head_ref_name="branch-20", is_draft=True)

    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        response = {"data": {"repository": {"pr_10": node_10, "pr_20": node_20}}}
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(response), stderr=""
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = real_github_for_test()
        result = ops._enrich_prs_via_graphql(location, [10, 20])

    # Single API call for both PRs
    assert len(called_with) == 1
    assert 10 in result
    assert 20 in result
    assert result[10]["headRefName"] == "branch-10"
    assert result[20]["isDraft"] is True


def test_enrich_prs_via_graphql_command_failure_returns_empty(monkeypatch: MonkeyPatch) -> None:
    """When gh command fails, returns empty dict instead of raising."""
    location = GitHubRepoLocation(
        root=Path("/repo"),
        repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh command failed")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = real_github_for_test()
        result = ops._enrich_prs_via_graphql(location, [42])

    assert result == {}


def test_enrich_prs_via_graphql_empty_pr_list(monkeypatch: MonkeyPatch) -> None:
    """Enriching empty PR list still makes a call and returns empty dict."""
    location = GitHubRepoLocation(
        root=Path("/repo"),
        repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        response = {"data": {"repository": {}}}
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(response), stderr=""
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = real_github_for_test()
        result = ops._enrich_prs_via_graphql(location, [])

    assert result == {}


def test_enrich_prs_via_graphql_partial_response(monkeypatch: MonkeyPatch) -> None:
    """When GraphQL returns data for only some PRs, missing ones are omitted."""
    location = GitHubRepoLocation(
        root=Path("/repo"),
        repo_id=GitHubRepoId(owner="test-owner", repo="test-repo"),
    )
    node_42 = _make_graphql_pr_node()

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Only pr_42 is returned, pr_99 is missing (e.g., deleted PR)
        response = {"data": {"repository": {"pr_42": node_42}}}
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(response), stderr=""
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = real_github_for_test()
        result = ops._enrich_prs_via_graphql(location, [42, 99])

    assert 42 in result
    assert 99 not in result


# ============================================================================
# _merge_rest_graphql_pr_data() Tests
# ============================================================================


def _make_rest_pr_item(
    *,
    number: int = 42,
    title: str = "Test PR",
    state: str = "open",
    body: str = "PR body",
    head_ref: str = "feature-branch",
    labels: list[str] | None = None,
    author: str = "test-user",
) -> dict[str, Any]:
    """Build a realistic REST API PR item for test fixtures."""
    return {
        "number": number,
        "html_url": f"https://github.com/test-owner/test-repo/pull/{number}",
        "title": title,
        "body": body,
        "state": state,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T14:00:00Z",
        "labels": [{"name": label} for label in (labels or [])],
        "user": {"login": author},
        "pull_request": {"head": {"ref": head_ref}},
    }


def test_merge_rest_graphql_single_pr() -> None:
    """Merging a single REST item with GraphQL enrichment produces correct output."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [_make_rest_pr_item(number=42, title="Fix bug")]
    enrichment = {42: _make_graphql_pr_node(head_ref_name="fix-branch", mergeable="MERGEABLE")}

    pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data(
        rest_items, enrichment, repo_id
    )

    assert len(pr_details_list) == 1
    pr = pr_details_list[0]
    assert pr.number == 42
    assert pr.title == "Fix bug"
    assert pr.state == "OPEN"
    assert pr.head_ref_name == "fix-branch"
    assert pr.owner == "test-owner"
    assert pr.repo == "test-repo"
    assert pr.mergeable == "MERGEABLE"
    assert pr.author == "test-user"

    assert 42 in pr_linkages
    pr_info = pr_linkages[42][0]
    assert pr_info.number == 42
    assert pr_info.has_conflicts is False
    assert pr_info.checks_passing is True
    assert pr_info.head_branch == "fix-branch"
    assert pr_info.review_decision == "APPROVED"
    assert unenriched_count == 0


def test_merge_rest_graphql_without_enrichment() -> None:
    """When GraphQL enrichment is missing, PRDetails are created but pr_linkages are skipped."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [_make_rest_pr_item(number=99)]
    enrichment: dict[int, dict[str, Any]] = {}

    pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data(
        rest_items, enrichment, repo_id
    )

    assert len(pr_details_list) == 1
    pr = pr_details_list[0]
    assert pr.number == 99
    # GraphQL fields fall back to defaults in PRDetails
    assert pr.is_draft is False
    assert pr.mergeable == "UNKNOWN"
    assert pr.merge_state_status == "UNKNOWN"

    # Unenriched PRs are excluded from pr_linkages
    assert 99 not in pr_linkages
    assert unenriched_count == 1


def test_merge_rest_graphql_multiple_prs() -> None:
    """Merging multiple REST items produces matching output for each."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [
        _make_rest_pr_item(number=10, title="PR 10"),
        _make_rest_pr_item(number=20, title="PR 20", state="closed"),
    ]
    enrichment = {
        10: _make_graphql_pr_node(is_draft=True, checks_state="FAILURE"),
        20: _make_graphql_pr_node(mergeable="CONFLICTING"),
    }

    pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data(
        rest_items, enrichment, repo_id
    )

    assert len(pr_details_list) == 2
    assert pr_details_list[0].number == 10
    assert pr_details_list[0].is_draft is True
    assert pr_details_list[1].number == 20
    assert pr_details_list[1].state == "CLOSED"

    assert pr_linkages[10][0].checks_passing is False
    assert pr_linkages[20][0].has_conflicts is True
    assert unenriched_count == 0


def test_merge_rest_graphql_partial_enrichment() -> None:
    """When only some PRs have enrichment, unenriched ones are excluded from linkages."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [
        _make_rest_pr_item(number=10, title="PR 10"),
        _make_rest_pr_item(number=20, title="PR 20"),
    ]
    enrichment = {10: _make_graphql_pr_node(head_ref_name="branch-10")}

    pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data(
        rest_items, enrichment, repo_id
    )

    assert len(pr_details_list) == 2
    assert 10 in pr_linkages
    assert 20 not in pr_linkages
    assert unenriched_count == 1


def test_merge_rest_graphql_labels_parsed() -> None:
    """REST labels are correctly extracted into PRDetails."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [_make_rest_pr_item(number=42, labels=["erk-plan", "bug"])]
    enrichment = {42: _make_graphql_pr_node()}

    pr_details_list, _, _ = merge_rest_graphql_pr_data(rest_items, enrichment, repo_id)

    assert pr_details_list[0].labels == ("erk-plan", "bug")


def test_merge_rest_graphql_timestamps_parsed() -> None:
    """REST timestamps are parsed into datetime objects."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [_make_rest_pr_item(number=42)]
    enrichment = {42: _make_graphql_pr_node()}

    pr_details_list, _, _ = merge_rest_graphql_pr_data(rest_items, enrichment, repo_id)

    pr = pr_details_list[0]
    assert pr.created_at == datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
    assert pr.updated_at == datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC)


def test_merge_rest_graphql_review_thread_counts() -> None:
    """Review thread counts from GraphQL are passed through to PullRequestInfo."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")
    rest_items = [_make_rest_pr_item(number=42)]
    enrichment = {42: _make_graphql_pr_node(resolved_threads=3, total_threads=5)}

    _, pr_linkages, _ = merge_rest_graphql_pr_data(rest_items, enrichment, repo_id)

    pr_info = pr_linkages[42][0]
    assert pr_info.review_thread_counts == (3, 5)


def test_merge_rest_graphql_empty_items() -> None:
    """Empty REST items list produces empty output."""
    repo_id = GitHubRepoId(owner="test-owner", repo="test-repo")

    pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data([], {}, repo_id)

    assert pr_details_list == []
    assert pr_linkages == {}
    assert unenriched_count == 0
