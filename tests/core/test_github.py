"""Tests for GitHub operations batched CI status and mergeability fetching."""

import subprocess
from pathlib import Path

import pytest
from erk_shared.github.real import RealGitHub
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.time.fake import FakeTime
from pytest import MonkeyPatch


@pytest.fixture
def sample_prs():
    """Sample PRs for testing."""
    return {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Add new feature 1",
            checks_passing=None,
            owner="owner",
            repo="repo",
            has_conflicts=None,
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/owner/repo/pull/456",
            is_draft=False,
            title="Add new feature 2",
            checks_passing=None,
            owner="owner",
            repo="repo",
            has_conflicts=None,
        ),
    }


def test_enrich_prs_with_ci_status_batch_includes_mergeability(
    monkeypatch: MonkeyPatch, sample_prs
):
    """Test CI batch method also enriches mergeability."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Mock GraphQL response with both CI status and mergeability data
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="""{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": {
                    "number": 456,
                    "mergeable": "CONFLICTING",
                    "mergeStateStatus": "DIRTY",
                    "commits": {
                        "nodes": []
                    }
                }
            }
        }
    }""",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", mock_run)

    github_ops = RealGitHub(FakeTime())
    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify PRs were enriched with mergeability
    assert result["feature-1"].has_conflicts is False  # MERGEABLE
    assert result["feature-2"].has_conflicts is True  # CONFLICTING

    # Verify other fields unchanged
    assert result["feature-1"].number == 123
    assert result["feature-2"].number == 456


def test_enrich_prs_with_ci_status_batch_empty(monkeypatch: MonkeyPatch):
    """Test empty input returns empty dict without API call."""
    call_count = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        call_count.append(1)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr("subprocess.run", mock_run)

    github_ops = RealGitHub(FakeTime())
    result = github_ops.enrich_prs_with_ci_status_batch({}, Path("/test/repo"))

    # Verify no API call made
    assert len(call_count) == 0

    # Verify empty dict returned
    assert result == {}


def test_enrich_prs_with_ci_status_batch_partial_failure(monkeypatch: MonkeyPatch, sample_prs):
    """Test partial failures don't break entire batch."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Mock response with one PR missing
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="""{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": null
            }
        }
    }""",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", mock_run)

    github_ops = RealGitHub(FakeTime())
    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify successful PR got mergeability
    assert result["feature-1"].has_conflicts is False

    # Verify failed PR has has_conflicts=None
    assert result["feature-2"].has_conflicts is None


def test_enrich_prs_with_ci_status_batch_unknown_mergeability(monkeypatch: MonkeyPatch, sample_prs):
    """Test UNKNOWN mergeability state handled correctly."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Mock response with UNKNOWN state
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="""{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeable": "UNKNOWN",
                    "mergeStateStatus": "UNKNOWN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": {
                    "number": 456,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                }
            }
        }
    }""",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", mock_run)

    github_ops = RealGitHub(FakeTime())
    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify UNKNOWN state returns None (not True or False)
    assert result["feature-1"].has_conflicts is None

    # Verify other PR works correctly
    assert result["feature-2"].has_conflicts is False


def test_enrich_prs_with_ci_status_batch_missing_mergeable_field(
    monkeypatch: MonkeyPatch, sample_prs
):
    """Test missing mergeable field handled gracefully."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Mock response with missing mergeable field
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="""{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": {
                    "number": 456,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                }
            }
        }
    }""",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", mock_run)

    github_ops = RealGitHub(FakeTime())
    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify missing field returns None
    assert result["feature-1"].has_conflicts is None

    # Verify other PR works correctly
    assert result["feature-2"].has_conflicts is False


def test_build_batch_pr_query_includes_mergeability():
    """Test GraphQL query builder includes mergeability fields."""
    github_ops = RealGitHub(FakeTime())
    pr_numbers = [123, 456]
    owner = "test-owner"
    repo = "test-repo"

    query = github_ops._build_batch_pr_query(pr_numbers, owner, repo)

    # Verify query contains fragment definition with both CI and mergeability fields
    assert "fragment PRCICheckFields on PullRequest" in query
    assert "mergeable" in query
    assert "mergeStateStatus" in query
    assert "statusCheckRollup" in query

    # Verify query contains aliased PR queries
    assert "pr_123: pullRequest(number: 123)" in query
    assert "pr_456: pullRequest(number: 456)" in query

    # Verify query contains fragment spreads
    assert "...PRCICheckFields" in query

    # Verify repository query
    assert f'repository(owner: "{owner}", name: "{repo}")' in query


def test_parse_pr_mergeability_conflicting():
    """Test parsing CONFLICTING mergeability status."""
    github_ops = RealGitHub(FakeTime())
    pr_data = {"mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is True


def test_parse_pr_mergeability_mergeable():
    """Test parsing MERGEABLE mergeability status."""
    github_ops = RealGitHub(FakeTime())
    pr_data = {"mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is False


def test_parse_pr_mergeability_unknown():
    """Test parsing UNKNOWN mergeability status."""
    github_ops = RealGitHub(FakeTime())
    pr_data = {"mergeable": "UNKNOWN", "mergeStateStatus": "UNKNOWN"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is None


def test_parse_pr_mergeability_none_input():
    """Test parsing None input."""
    github_ops = RealGitHub(FakeTime())
    result = github_ops._parse_pr_mergeability(None)
    assert result is None


def test_parse_pr_mergeability_missing_field():
    """Test parsing data with missing mergeable field."""
    github_ops = RealGitHub(FakeTime())
    pr_data = {"mergeStateStatus": "CLEAN"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is None
