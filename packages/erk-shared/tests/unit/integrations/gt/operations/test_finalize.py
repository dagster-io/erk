"""Tests for execute_finalize operation with event assertions.

Tests the finalize phase which updates PR metadata and cleans up temp files.
"""

from pathlib import Path

import pytest
from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.types import FinalizeResult

from tests.unit.integrations.gt.operations.conftest import (
    collect_events,
    has_event_containing,
)


class TestFinalizeSuccess:
    """Tests for successful finalize execution."""

    def test_success_with_pr_body(self, tmp_path: Path) -> None:
        """Test successful finalize with pr_body parameter."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
        )

        events, result = collect_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title="Add new feature",
                pr_body="This is the PR body.",
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.pr_number == 123
        assert result.pr_title == "Add new feature"
        assert result.branch_name == "feature-branch"

        # Assert key events
        assert has_event_containing(events, "Updating PR metadata")
        assert has_event_containing(events, "PR metadata updated")

    def test_success_with_pr_body_file(self, tmp_path: Path) -> None:
        """Test successful finalize with pr_body_file parameter."""
        # Create a temporary body file
        body_file = tmp_path / "pr_body.md"
        body_file.write_text("Body from file.", encoding="utf-8")

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(456)
        )

        events, result = collect_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=456,
                pr_title="Another feature",
                pr_body_file=body_file,
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True
        assert result.pr_number == 456

        # Assert key events
        assert has_event_containing(events, "Updating PR metadata")
        assert has_event_containing(events, "PR metadata updated")

    def test_success_cleans_up_diff_file(self, tmp_path: Path) -> None:
        """Test that diff file is cleaned up on success."""
        # Create a temporary diff file
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("some diff content", encoding="utf-8")
        assert diff_file.exists()

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
        )

        events, result = collect_events(
            execute_finalize(
                ops,
                tmp_path,
                pr_number=123,
                pr_title="Feature",
                pr_body="Body",
                diff_file=str(diff_file),
            )
        )

        assert isinstance(result, FinalizeResult)
        assert result.success is True

        # Diff file should be cleaned up
        assert not diff_file.exists()
        assert has_event_containing(events, "Cleaned up temp file")


class TestFinalizeValidationErrors:
    """Tests for validation error scenarios."""

    def test_neither_body_nor_file_raises(self, tmp_path: Path) -> None:
        """Test error when neither pr_body nor pr_body_file is provided."""
        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
        )

        with pytest.raises(ValueError, match="Must specify either"):
            # Consume the generator to trigger the error
            list(
                execute_finalize(
                    ops,
                    tmp_path,
                    pr_number=123,
                    pr_title="Feature",
                )
            )

    def test_both_body_and_file_raises(self, tmp_path: Path) -> None:
        """Test error when both pr_body and pr_body_file are provided."""
        body_file = tmp_path / "pr_body.md"
        body_file.write_text("Body from file.", encoding="utf-8")

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
        )

        with pytest.raises(ValueError, match="Cannot specify both"):
            # Consume the generator to trigger the error
            list(
                execute_finalize(
                    ops,
                    tmp_path,
                    pr_number=123,
                    pr_title="Feature",
                    pr_body="Inline body",
                    pr_body_file=body_file,
                )
            )

    def test_body_file_not_exists_raises(self, tmp_path: Path) -> None:
        """Test error when pr_body_file does not exist."""
        nonexistent_file = tmp_path / "nonexistent.md"

        ops = (
            FakeGtKitOps()
            .with_repo_root(str(tmp_path))
            .with_branch("feature-branch", parent="main")
            .with_pr(123)
        )

        with pytest.raises(ValueError, match="does not exist"):
            # Consume the generator to trigger the error
            list(
                execute_finalize(
                    ops,
                    tmp_path,
                    pr_number=123,
                    pr_title="Feature",
                    pr_body_file=nonexistent_file,
                )
            )
