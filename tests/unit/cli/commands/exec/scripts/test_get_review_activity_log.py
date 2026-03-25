"""Tests for erk exec get-review-activity-log command."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_review_activity_log import (
    _extract_activity_log,
    get_review_activity_log,
)
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _sentinel_path():
    """Return a Path that won't be used (FakeLocalGitHub ignores repo_root)."""
    from pathlib import Path

    return Path("/unused")


class TestExtractActivityLog:
    """Tests for the _extract_activity_log helper."""

    def test_extracts_log_after_heading(self) -> None:
        body = """\
## Summary

Some summary text.

### Activity Log
- 2024-01-01: Found 2 violations
- 2024-01-02: All resolved
"""
        result = _extract_activity_log(body)
        assert "- 2024-01-01: Found 2 violations" in result
        assert "- 2024-01-02: All resolved" in result

    def test_returns_empty_when_no_heading(self) -> None:
        body = "## Summary\n\nNo activity log here."
        result = _extract_activity_log(body)
        assert result == ""

    def test_handles_heading_at_end_of_body(self) -> None:
        body = "## Summary\n\n### Activity Log\n"
        result = _extract_activity_log(body)
        assert result == ""

    def test_strips_surrounding_whitespace(self) -> None:
        body = "### Activity Log\n\n  - entry 1\n  - entry 2\n\n"
        result = _extract_activity_log(body)
        assert result.startswith("- entry 1")
        assert result.endswith("- entry 2")


class TestGetReviewActivityLog:
    """Tests for the get-review-activity-log exec command."""

    def test_no_existing_comment(self) -> None:
        """Returns found=false when no comment has the marker."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            github = FakeLocalGitHub()
            ctx = build_workspace_test_context(env, github=github)

            result = runner.invoke(
                get_review_activity_log,
                ["--pr-number", "123", "--marker", "<!-- audit-pr-docs -->"],
                obj=ctx,
            )

            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["found"] is False
            assert data["activity_log"] == ""

    def test_existing_comment_with_activity_log(self) -> None:
        """Returns found=true and extracts activity log section."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            github = FakeLocalGitHub()
            # Seed a comment containing the marker and activity log
            comment_body = (
                "<!-- audit-pr-docs -->\n\n"
                "## Summary\n\n"
                "Found 1 violation.\n\n"
                "<details>\n"
                "<summary>Details</summary>\n\n"
                "### Activity Log\n"
                "- 2024-01-15: Found 1 violation\n"
                "- 2024-01-14: Clean run\n\n"
                "</details>"
            )
            github.create_pr_comment(_sentinel_path(), 42, comment_body)

            ctx = build_workspace_test_context(env, github=github)

            result = runner.invoke(
                get_review_activity_log,
                ["--pr-number", "42", "--marker", "<!-- audit-pr-docs -->"],
                obj=ctx,
            )

            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["found"] is True
            assert "2024-01-15: Found 1 violation" in data["activity_log"]
            assert "2024-01-14: Clean run" in data["activity_log"]

    def test_existing_comment_without_activity_log_section(self) -> None:
        """Returns found=true with empty log when comment has no Activity Log heading."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            github = FakeLocalGitHub()
            # Comment has marker but no Activity Log section
            comment_body = "<!-- audit-pr-docs -->\n\n## Summary\n\nNo log here."
            github.create_pr_comment(_sentinel_path(), 42, comment_body)

            ctx = build_workspace_test_context(env, github=github)

            result = runner.invoke(
                get_review_activity_log,
                ["--pr-number", "42", "--marker", "<!-- audit-pr-docs -->"],
                obj=ctx,
            )

            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["found"] is True
            assert data["activity_log"] == ""

    def test_different_pr_number_not_found(self) -> None:
        """Comment on a different PR is not found."""
        runner = CliRunner()
        with erk_isolated_fs_env(runner, env_overrides=None) as env:
            github = FakeLocalGitHub()
            # Comment on PR 42
            github.create_pr_comment(
                _sentinel_path(), 42, "<!-- audit-pr-docs -->\n### Activity Log\n- entry"
            )

            ctx = build_workspace_test_context(env, github=github)

            # Search on PR 99
            result = runner.invoke(
                get_review_activity_log,
                ["--pr-number", "99", "--marker", "<!-- audit-pr-docs -->"],
                obj=ctx,
            )

            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["found"] is False
