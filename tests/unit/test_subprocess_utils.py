"""Tests for subprocess_utils module."""

from erk_shared.subprocess_utils import _build_timing_description


def test_build_timing_description_regular_command() -> None:
    """Non-GraphQL commands are passed through unchanged."""
    cmd = ["gh", "pr", "list", "--json", "number"]
    result = _build_timing_description(cmd)
    assert result == "gh pr list --json number"


def test_build_timing_description_graphql_truncates_query() -> None:
    """GraphQL query content is replaced with character count."""
    query = "query { repository { name } }"
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    result = _build_timing_description(cmd)

    # Query text should NOT appear in output
    assert "repository" not in result
    # Character count should appear
    assert f"query=<{len(query)} chars>" in result
    # Other args should remain
    assert result == f"gh api graphql -f query=<{len(query)} chars>"


def test_build_timing_description_graphql_multiline_query() -> None:
    """Multi-line GraphQL queries are also truncated."""
    query = """fragment Fields on Issue {
        title
        body
    }
    query {
        repository {
            issue(number: 1) {
                ...Fields
            }
        }
    }"""
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    result = _build_timing_description(cmd)

    # Query content should NOT appear
    assert "repository" not in result
    assert "fragment" not in result
    # Character count should appear
    assert f"query=<{len(query)} chars>" in result
