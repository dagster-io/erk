"""Unit tests for Graphite parsing functions with JSON fixtures."""

from erk_shared.integrations.graphite.parsing import (
    _graphite_url_to_github_url,
    parse_graphite_cache,
    parse_graphite_pr_info,
)
from tests.conftest import load_fixture


def test_parse_graphite_pr_info():
    """Test parsing Graphite PR info JSON."""
    json_data = load_fixture("graphite/graphite_pr_info.json")
    result = parse_graphite_pr_info(json_data)

    assert len(result) == 3

    # Check first feature PR
    assert "feature-stack-1" in result
    pr1 = result["feature-stack-1"]
    assert pr1.number == 101
    assert pr1.state == "OPEN"
    assert pr1.url == "https://github.com/dagster-io/erk/pull/101"
    assert pr1.is_draft is False
    assert pr1.checks_passing is None  # CI status not available from Graphite
    assert pr1.owner == "dagster-io"
    assert pr1.repo == "erk"

    # Check merged PR
    assert "feature-stack-2" in result
    pr2 = result["feature-stack-2"]
    assert pr2.number == 102
    assert pr2.state == "MERGED"

    # Check draft PR
    assert "draft-feature" in result
    pr3 = result["draft-feature"]
    assert pr3.number == 103
    assert pr3.is_draft is True
    assert pr3.owner == "owner"
    assert pr3.repo == "repo"


def test_parse_graphite_pr_info_empty():
    """Test parsing empty Graphite PR info."""
    json_data = load_fixture("graphite/graphite_empty.json")
    result = parse_graphite_pr_info(json_data)

    assert result == {}


def test_parse_graphite_pr_info_malformed_url():
    """Test parsing PR info with malformed URLs (should skip)."""
    json_str = """{
        "prInfos": [
            {
                "headRefName": "bad-url-branch",
                "url": "https://not-graphite.com/something",
                "prNumber": 999,
                "state": "OPEN",
                "isDraft": false
            }
        ]
    }"""
    result = parse_graphite_pr_info(json_str)
    # Should skip PRs that can't be converted to valid GitHub URLs
    assert len(result) == 0


def test_parse_graphite_cache():
    """Test parsing Graphite cache with branch metadata."""
    json_data = load_fixture("graphite/graphite_cache_persist.json")

    # Simulate git branch heads
    git_branch_heads = {
        "main": "abc123",
        "feature-1": "def456",
        "feature-1-sub": "ghi789",
        "feature-2": "jkl012",
    }

    result = parse_graphite_cache(json_data, git_branch_heads)

    assert len(result) == 4

    # Check main (trunk) branch
    assert "main" in result
    main = result["main"]
    assert main.name == "main"
    assert main.parent is None
    assert main.children == ["feature-1", "feature-2"]
    assert main.is_trunk is True
    assert main.commit_sha == "abc123"

    # Check feature-1 branch
    assert "feature-1" in result
    f1 = result["feature-1"]
    assert f1.name == "feature-1"
    assert f1.parent == "main"
    assert f1.children == ["feature-1-sub"]
    assert f1.is_trunk is False
    assert f1.commit_sha == "def456"

    # Check feature-1-sub branch
    assert "feature-1-sub" in result
    f1_sub = result["feature-1-sub"]
    assert f1_sub.name == "feature-1-sub"
    assert f1_sub.parent == "feature-1"
    assert f1_sub.children == []
    assert f1_sub.is_trunk is False

    # Check feature-2 branch
    assert "feature-2" in result
    f2 = result["feature-2"]
    assert f2.name == "feature-2"
    assert f2.parent == "main"
    assert f2.children == []
    assert f2.is_trunk is False


def test_parse_graphite_cache_empty():
    """Test parsing empty Graphite cache."""
    json_str = '{"branches": []}'
    git_branch_heads = {}
    result = parse_graphite_cache(json_str, git_branch_heads)

    assert result == {}


def test_parse_graphite_cache_missing_git_heads():
    """Test parsing cache when git branch heads are missing."""
    json_data = load_fixture("graphite/graphite_cache_persist.json")

    # Empty git branch heads
    git_branch_heads = {}

    result = parse_graphite_cache(json_data, git_branch_heads)

    assert len(result) == 4
    # All branches should have empty commit SHA
    for _branch_name, branch_meta in result.items():
        assert branch_meta.commit_sha == ""


def test_parse_graphite_cache_invalid_data():
    """Test parsing cache with invalid branch data."""
    json_str = """{
        "branches": [
            ["valid-branch", {
                "validationResult": "VALID",
                "parentBranchName": "main",
                "children": []
            }],
            ["invalid-branch", "not-a-dict"],
            ["missing-fields", {}]
        ]
    }"""

    git_branch_heads = {"valid-branch": "abc123", "missing-fields": "def456"}
    result = parse_graphite_cache(json_str, git_branch_heads)

    # Should have valid-branch and missing-fields (with defaults)
    assert len(result) == 2
    assert "valid-branch" in result
    assert "missing-fields" in result
    assert "invalid-branch" not in result

    # Check missing-fields has defaults
    mf = result["missing-fields"]
    assert mf.parent is None
    assert mf.children == []
    assert mf.is_trunk is True  # Branches with no parent are trunk branches


def test_graphite_url_to_github_url():
    """Test converting Graphite URLs to GitHub URLs."""
    # Standard Graphite URL
    url = _graphite_url_to_github_url("https://app.graphite.com/github/pr/dagster-io/erk/42")
    assert url == "https://github.com/dagster-io/erk/pull/42"

    # Different org/repo
    url = _graphite_url_to_github_url("https://app.graphite.com/github/pr/facebook/react/999")
    assert url == "https://github.com/facebook/react/pull/999"

    # Not a Graphite URL - should return unchanged
    url = _graphite_url_to_github_url("https://github.com/owner/repo/pull/123")
    assert url == "https://github.com/owner/repo/pull/123"

    # Malformed URL - should return unchanged
    url = _graphite_url_to_github_url("https://example.com/something")
    assert url == "https://example.com/something"

    # Short URL - should return unchanged
    url = _graphite_url_to_github_url("https://app.graphite.com/pr/123")
    assert url == "https://app.graphite.com/pr/123"
