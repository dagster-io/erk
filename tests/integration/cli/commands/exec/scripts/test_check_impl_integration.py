"""Integration tests for check-impl kit CLI command.

Tests the complete validation workflow for .impl/ folder structure and issue tracking.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.check_impl import (
    check_impl,
)


@pytest.fixture
def impl_folder(tmp_path: Path) -> Path:
    """Create .impl/ folder with test files."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text(
        "# Test Plan\n\n## Steps\n1. Do thing\n2. Do other thing",
        encoding="utf-8",
    )

    # Create progress.md
    progress_md = impl_dir / "progress.md"
    progress_content = (
        "---\ncompleted_steps: 0\ntotal_steps: 2\n---\n\n- [ ] 1. Do thing\n- [ ] 2. Do other thing"
    )
    progress_md.write_text(progress_content, encoding="utf-8")

    return impl_dir


def test_check_impl_validates_complete_issue_json(impl_folder: Path, monkeypatch) -> None:
    """Test that check-impl validates issue.json has all required fields."""
    issue_json = impl_folder / "issue.json"

    # Write COMPLETE format
    issue_data = {
        "issue_number": 123,
        "issue_url": "https://github.com/org/repo/issues/123",
        "created_at": "2025-01-01T00:00:00Z",
        "synced_at": "2025-01-01T00:00:00Z",
    }
    issue_json.write_text(json.dumps(issue_data), encoding="utf-8")

    # Change to parent directory for test
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(check_impl, ["--dry-run"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_issue_tracking"] is True
    assert data["plan_length"] > 0


def test_check_impl_handles_incomplete_issue_json(impl_folder: Path, monkeypatch) -> None:
    """Test that incomplete issue.json is detected and tracking disabled."""
    issue_json = impl_folder / "issue.json"

    # Write SIMPLE format (missing timestamps)
    issue_data = {
        "issue_number": 123,
        "issue_url": "https://github.com/org/repo/issues/123",
    }
    issue_json.write_text(json.dumps(issue_data), encoding="utf-8")

    # Change to parent directory for test
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(check_impl, ["--dry-run"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_issue_tracking"] is False  # Tracking disabled due to incomplete format


def test_check_impl_handles_missing_issue_json(impl_folder: Path, monkeypatch) -> None:
    """Test that missing issue.json is handled gracefully."""
    # No issue.json file created

    # Change to parent directory for test
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(check_impl, ["--dry-run"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_issue_tracking"] is False


def test_check_impl_errors_on_missing_plan(tmp_path: Path, monkeypatch) -> None:
    """Test error when plan.md is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create progress.md but NOT plan.md
    progress_md = impl_dir / "progress.md"
    progress_md.write_text("# Progress\n\n- [ ] Step 1", encoding="utf-8")

    # Change to parent directory for test
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_impl, ["--dry-run"])

    assert result.exit_code == 1
    assert "No plan.md found" in result.output


def test_check_impl_errors_on_missing_progress(tmp_path: Path, monkeypatch) -> None:
    """Test error when progress.md is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md but NOT progress.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Plan\n\n1. Do thing", encoding="utf-8")

    # Change to parent directory for test
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_impl, ["--dry-run"])

    assert result.exit_code == 1
    assert "No progress.md found" in result.output


def test_check_impl_errors_on_missing_impl_folder(tmp_path: Path, monkeypatch) -> None:
    """Test error when .impl/ folder doesn't exist."""
    # No .impl/ folder created

    # Change to directory for test
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_impl, ["--dry-run"])

    assert result.exit_code == 1
    assert "No .impl/ folder found" in result.output


def test_check_impl_normal_mode_with_tracking(impl_folder: Path, monkeypatch) -> None:
    """Test normal mode outputs instructions with tracking enabled."""
    issue_json = impl_folder / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 456,
                "issue_url": "https://github.com/org/repo/issues/456",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    # Change to parent directory for test
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(check_impl, [])

    assert result.exit_code == 0
    assert "Plan loaded from .impl/plan.md" in result.output
    assert "GitHub tracking: ENABLED (issue #456)" in result.output
    assert "/erk:system:impl-execute" in result.output


def test_check_impl_normal_mode_without_tracking(impl_folder: Path, monkeypatch) -> None:
    """Test normal mode outputs instructions with tracking disabled."""
    # No issue.json file created

    # Change to parent directory for test
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(check_impl, [])

    assert result.exit_code == 0
    assert "Plan loaded from .impl/plan.md" in result.output
    assert "GitHub tracking: DISABLED (no issue.json)" in result.output
    assert "/erk:system:impl-execute" in result.output
