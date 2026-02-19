"""Tests for subprocess_utils module."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock, patch

from erk_shared.subprocess_utils import (
    _GH_COMMAND_TIMEOUT,
    _build_timing_description,
    copied_env_for_git_subprocess,
    execute_gh_command,
)


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


def test_copied_env_for_git_subprocess_sets_git_terminal_prompt() -> None:
    """copied_env_for_git_subprocess sets GIT_TERMINAL_PROMPT=0."""
    env = copied_env_for_git_subprocess()
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_copied_env_for_git_subprocess_preserves_existing_env() -> None:
    """copied_env_for_git_subprocess preserves existing environment variables."""
    env = copied_env_for_git_subprocess()
    # PATH should always be present in the environment
    assert "PATH" in env


def test_execute_gh_command_forwards_timeout() -> None:
    """execute_gh_command passes _GH_COMMAND_TIMEOUT to run_subprocess_with_context."""
    with patch("erk_shared.subprocess_utils.run_subprocess_with_context") as mock_run:
        mock_run.return_value = Mock(spec=CompletedProcess, stdout="output")

        execute_gh_command(["gh", "pr", "list"], Path("/repo"))

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["timeout"] == _GH_COMMAND_TIMEOUT
