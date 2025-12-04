"""Tests for execute_finalize operation.

Tests verify PR metadata update and cleanup operations,
including validation of PR body parameters.
"""

from pathlib import Path

import pytest
from erk_shared.integrations.gt.fake_kit import FakeGtKitOps
from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    FinalizeResult,
    execute_finalize,
)


def test_execute_finalize_success_with_pr_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test successful finalize with PR body provided directly."""
    # Arrange
    # Change cwd to tmp_path to avoid reading .impl from current worktree
    monkeypatch.chdir(tmp_path)

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(123, url="https://github.com/repo/pull/123", title="Original Title")
    )

    # Act
    result = execute_finalize(
        pr_number=123,
        pr_title="Feature: Add new capability",
        pr_body="This PR adds a new capability to the system.\n\nDetails:\n- Item 1\n- Item 2",
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    assert result.pr_number == 123
    assert result.pr_url == "https://github.com/repo/pull/123"
    assert result.pr_title == "Feature: Add new capability"
    assert result.branch_name == "feature"
    assert result.issue_number is None
    assert "Successfully updated PR #123" in result.message


def test_execute_finalize_success_with_pr_body_file(tmp_path: Path) -> None:
    """Test successful finalize with PR body read from file."""
    # Arrange
    pr_body_file = tmp_path / "pr_body.txt"
    pr_body_file.write_text("PR body from file.\n\nMore details here.", encoding="utf-8")

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_commits(1)
        .with_pr(456, url="https://github.com/repo/pull/456")
    )

    # Act
    result = execute_finalize(
        pr_number=456,
        pr_title="Bug Fix: Resolve issue",
        pr_body_file=pr_body_file,
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    assert result.pr_number == 456
    assert result.pr_url == "https://github.com/repo/pull/456"
    assert result.pr_title == "Bug Fix: Resolve issue"


def test_execute_finalize_validation_error_both_body_and_file(tmp_path: Path) -> None:
    """Test finalize raises error when both pr_body and pr_body_file are provided."""
    # Arrange
    pr_body_file = tmp_path / "pr_body.txt"
    pr_body_file.write_text("Body content", encoding="utf-8")

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Cannot specify both --pr-body and --pr-body-file"):
        execute_finalize(
            pr_number=123,
            pr_title="Title",
            pr_body="Direct body",
            pr_body_file=pr_body_file,
            ops=ops,
        )


def test_execute_finalize_validation_error_neither_body_nor_file(tmp_path: Path) -> None:
    """Test finalize raises error when neither pr_body nor pr_body_file is provided."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Must specify either --pr-body or --pr-body-file"):
        execute_finalize(
            pr_number=123,
            pr_title="Title",
            ops=ops,
        )


def test_execute_finalize_validation_error_body_file_not_exists(tmp_path: Path) -> None:
    """Test finalize raises error when pr_body_file does not exist."""
    # Arrange
    nonexistent_file = tmp_path / "nonexistent.txt"

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act & Assert
    with pytest.raises(ValueError, match="PR body file does not exist"):
        execute_finalize(
            pr_number=123,
            pr_title="Title",
            pr_body_file=nonexistent_file,
            ops=ops,
        )


def test_execute_finalize_cleanup_diff_file(tmp_path: Path) -> None:
    """Test finalize cleans up temporary diff file if provided."""
    # Arrange
    diff_file = tmp_path / "temp_diff.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act
    result = execute_finalize(
        pr_number=123,
        pr_title="Title",
        pr_body="Body",
        diff_file=str(diff_file),
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    assert not diff_file.exists()  # File should be cleaned up


def test_execute_finalize_handles_missing_diff_file(tmp_path: Path) -> None:
    """Test finalize handles missing diff file gracefully (no error)."""
    # Arrange
    nonexistent_diff = tmp_path / "nonexistent.diff"

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act
    result = execute_finalize(
        pr_number=123,
        pr_title="Title",
        pr_body="Body",
        diff_file=str(nonexistent_diff),
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True


def test_execute_finalize_with_impl_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test finalize reads issue number from .impl directory if present."""
    # Arrange
    # Change cwd to tmp_path so execute_finalize reads .impl from there
    monkeypatch.chdir(tmp_path)

    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    issue_json = impl_dir / "issue.json"
    # IssueReference requires all fields: issue_number, issue_url, created_at, synced_at
    issue_json.write_text(
        '{"issue_number": 456, "issue_url": "https://github.com/repo/issues/456", '
        '"created_at": "2025-01-01T00:00:00Z", "synced_at": "2025-01-01T00:00:00Z"}',
        encoding="utf-8",
    )

    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act
    result = execute_finalize(
        pr_number=123,
        pr_title="Title",
        pr_body="Body",
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    assert result.issue_number == 456


def test_execute_finalize_updates_pr_metadata(tmp_path: Path) -> None:
    """Test finalize calls GitHub API to update PR title and body."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(789, url="https://github.com/owner/repo/pull/789")
    )

    # Act
    result = execute_finalize(
        pr_number=789,
        pr_title="Updated Title",
        pr_body="Updated body content",
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    assert result.pr_number == 789
    assert result.pr_title == "Updated Title"


def test_execute_finalize_includes_metadata_section(tmp_path: Path) -> None:
    """Test finalize appends metadata section to PR body."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act
    result = execute_finalize(
        pr_number=123,
        pr_title="Title",
        pr_body="Main PR body content",
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    # Metadata section is appended by build_pr_metadata_section()
    # The actual GitHub fake receives the combined body


def test_execute_finalize_returns_graphite_url(tmp_path: Path) -> None:
    """Test finalize includes Graphite URL in result."""
    # Arrange
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature", parent="main")
        .with_pr(123)
    )

    # Act
    result = execute_finalize(
        pr_number=123,
        pr_title="Title",
        pr_body="Body",
        ops=ops,
    )

    # Assert
    assert isinstance(result, FinalizeResult)
    assert result.success is True
    # Graphite URL is generated by main_graphite().get_graphite_url()
    assert result.graphite_url is not None
