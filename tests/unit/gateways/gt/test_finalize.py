"""Tests for finalize phase closing reference preservation."""

from pathlib import Path

import pytest

from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.finalize import execute_finalize
from erk_shared.gateway.gt.types import FinalizeResult
from tests.unit.gateways.gt.fake_ops import FakeGtKitOps


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repository root."""
    return tmp_path


class TestFinalizeClosingReferencePreservation:
    """Tests for closing reference preservation when .impl/issue.json is missing."""

    def test_preserves_same_repo_closing_reference_when_impl_missing(self, tmp_repo: Path) -> None:
        """Test that closing reference is preserved from existing PR body.

        When .impl/issue.json is missing but the PR already has a closing reference
        in its footer, finalize should preserve that reference.
        """
        existing_body = (
            "## Summary\n\nThis PR does things.\n---\n\n"
            "Closes #123\n\n"
            "To checkout this PR in a fresh worktree..."
        )
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_pr(42, body=existing_body)
            .with_remote_url("https://github.com/dagster-io/erk.git")
        )

        # No .impl folder exists, so issue.json cannot be read

        result = render_events(
            execute_finalize(
                ops=ops,
                cwd=tmp_repo,
                pr_number=42,
                pr_title="New Title",
                pr_body="New body content",
                pr_body_file=None,
                diff_file=None,
                plans_repo=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        # The issue_number should be extracted from the existing PR body
        assert result.issue_number == 123

    def test_preserves_cross_repo_closing_reference_when_impl_missing(self, tmp_repo: Path) -> None:
        """Test that cross-repo closing reference is preserved.

        When the existing PR body has a cross-repo closing reference like
        "Closes owner/repo#456", it should be preserved when .impl/issue.json is missing.
        """
        existing_body = (
            "## Summary\n\nThis PR does things.\n---\n\n"
            "Closes dagster-io/plans#456\n\n"
            "To checkout this PR..."
        )
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_pr(42, body=existing_body)
            .with_remote_url("https://github.com/dagster-io/erk.git")
        )

        result = render_events(
            execute_finalize(
                ops=ops,
                cwd=tmp_repo,
                pr_number=42,
                pr_title="New Title",
                pr_body="New body content",
                pr_body_file=None,
                diff_file=None,
                plans_repo=None,  # Will be overridden by extracted value
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        # Issue number should be extracted from cross-repo reference
        assert result.issue_number == 456

    def test_impl_issue_json_takes_precedence_over_existing_body(self, tmp_repo: Path) -> None:
        """Test that .impl/issue.json takes precedence over existing PR body.

        When both .impl/issue.json exists and the PR body has a closing reference,
        the .impl/issue.json value should be used (authoritative source).
        """
        existing_body = (
            "## Summary\n---\n\n"
            "Closes #999\n\n"  # Old reference in body
            "To checkout this PR..."
        )
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_pr(42, body=existing_body)
            .with_remote_url("https://github.com/dagster-io/erk.git")
        )

        # Create .impl/issue.json with different issue number
        impl_dir = tmp_repo / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        # Must include all required fields for read_issue_reference to succeed
        issue_json.write_text(
            '{"issue_number": 777, "issue_url": "https://github.com/org/repo/issues/777", '
            '"created_at": "2024-01-01T00:00:00Z", "synced_at": "2024-01-01T00:00:00Z", '
            '"labels": []}',
            encoding="utf-8",
        )

        result = render_events(
            execute_finalize(
                ops=ops,
                cwd=tmp_repo,
                pr_number=42,
                pr_title="New Title",
                pr_body="New body content",
                pr_body_file=None,
                diff_file=None,
                plans_repo=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        # .impl/issue.json value (777) should take precedence over body (999)
        assert result.issue_number == 777

    def test_no_closing_reference_when_none_exists(self, tmp_repo: Path) -> None:
        """Test that no closing reference is added when none exists.

        When neither .impl/issue.json nor the existing PR body has a closing
        reference, the result should have no issue_number.
        """
        existing_body = (
            "## Summary\n\nThis PR does things.\n---\n\n"
            "To checkout this PR..."  # No closing reference
        )
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_pr(42, body=existing_body)
            .with_remote_url("https://github.com/dagster-io/erk.git")
        )

        result = render_events(
            execute_finalize(
                ops=ops,
                cwd=tmp_repo,
                pr_number=42,
                pr_title="New Title",
                pr_body="New body content",
                pr_body_file=None,
                diff_file=None,
                plans_repo=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.issue_number is None

    def test_no_closing_reference_when_no_footer(self, tmp_repo: Path) -> None:
        """Test handling of PR body without footer delimiter.

        When the existing PR body has no --- delimiter (no footer section),
        there's nothing to extract and no issue_number should be set.
        """
        existing_body = "## Summary\n\nThis PR does things."  # No footer
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_pr(42, body=existing_body)
            .with_remote_url("https://github.com/dagster-io/erk.git")
        )

        result = render_events(
            execute_finalize(
                ops=ops,
                cwd=tmp_repo,
                pr_number=42,
                pr_title="New Title",
                pr_body="New body content",
                pr_body_file=None,
                diff_file=None,
                plans_repo=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.issue_number is None

    def test_no_closing_reference_when_empty_body(self, tmp_repo: Path) -> None:
        """Test handling of PR with empty body.

        When the existing PR body is empty, no closing reference can be extracted.
        """
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_repo))
            .with_branch("feature-branch", parent="main")
            .with_pr(42, body="")
            .with_remote_url("https://github.com/dagster-io/erk.git")
        )

        result = render_events(
            execute_finalize(
                ops=ops,
                cwd=tmp_repo,
                pr_number=42,
                pr_title="New Title",
                pr_body="New body content",
                pr_body_file=None,
                diff_file=None,
                plans_repo=None,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.issue_number is None
