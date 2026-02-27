"""Integration tests for check-impl kit CLI command.

Tests the complete validation workflow for .erk/impl-context/ folder structure and issue tracking.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.check_impl import (
    check_impl,
)
from erk_shared.context.context import ErkContext


@pytest.fixture
def impl_folder(tmp_path: Path) -> Path:
    """Create .erk/impl-context/<branch>/ folder with test files."""
    # Create branch-scoped impl directory
    impl_dir = tmp_path / ".erk" / "impl-context" / "test-branch"
    impl_dir.mkdir(parents=True)

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


def test_check_impl_validates_complete_plan_ref(impl_folder: Path, tmp_path: Path) -> None:
    """Test that check-impl validates plan-ref.json has all required fields."""
    plan_ref = impl_folder / "plan-ref.json"

    # Write COMPLETE format
    plan_ref_data = {
        "provider": "github",
        "plan_id": "123",
        "url": "https://github.com/org/repo/issues/123",
        "created_at": "2025-01-01T00:00:00Z",
        "synced_at": "2025-01-01T00:00:00Z",
        "labels": [],
        "objective_id": None,
    }
    plan_ref.write_text(json.dumps(plan_ref_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        ["--dry-run"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_plan_tracking"] is True
    assert data["plan_length"] > 0


def test_check_impl_handles_incomplete_plan_ref(impl_folder: Path, tmp_path: Path) -> None:
    """Test that incomplete plan-ref.json is detected and tracking disabled."""
    plan_ref = impl_folder / "plan-ref.json"

    # Write incomplete format (missing required fields: plan_id, url, etc.)
    plan_ref_data = {
        "provider": "github",
    }
    plan_ref.write_text(json.dumps(plan_ref_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        ["--dry-run"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_plan_tracking"] is False  # Tracking disabled due to incomplete format


def test_check_impl_handles_missing_issue_json(impl_folder: Path, tmp_path: Path) -> None:
    """Test that missing issue.json is handled gracefully."""
    # No issue.json file created

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        ["--dry-run"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["has_plan_tracking"] is False


def test_check_impl_errors_on_missing_plan(tmp_path: Path) -> None:
    """Test error when plan.md is missing."""
    impl_dir = tmp_path / ".erk" / "impl-context" / "test-branch"
    impl_dir.mkdir(parents=True)

    # Create progress.md but NOT plan.md
    progress_md = impl_dir / "progress.md"
    progress_md.write_text("# Progress\n\n- [ ] Step 1", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        ["--dry-run"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    assert "No plan.md found" in result.output


def test_check_impl_errors_on_missing_progress(tmp_path: Path) -> None:
    """Test error when progress.md is missing."""
    impl_dir = tmp_path / ".erk" / "impl-context" / "test-branch"
    impl_dir.mkdir(parents=True)

    # Create plan.md but NOT progress.md
    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Plan\n\n1. Do thing", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        ["--dry-run"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    assert "No progress.md found" in result.output


def test_check_impl_errors_on_missing_impl_folder(tmp_path: Path) -> None:
    """Test error when .impl/ folder doesn't exist."""
    # No .impl/ folder created

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        ["--dry-run"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    assert "No implementation folder found" in result.output


def test_check_impl_normal_mode_with_tracking(impl_folder: Path, tmp_path: Path) -> None:
    """Test normal mode outputs instructions with tracking enabled."""
    plan_ref = impl_folder / "plan-ref.json"
    plan_ref.write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "456",
                "url": "https://github.com/org/repo/issues/456",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": [],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        [],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    assert "plan.md" in result.output
    assert "GitHub tracking: ENABLED (plan #456)" in result.output
    assert "/erk:plan-implement" in result.output


def test_check_impl_normal_mode_without_tracking(impl_folder: Path, tmp_path: Path) -> None:
    """Test normal mode outputs instructions with tracking disabled."""
    # No issue.json file created

    runner = CliRunner()
    result = runner.invoke(
        check_impl,
        [],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 0
    assert "plan.md" in result.output
    assert "GitHub tracking: DISABLED" in result.output
    assert "/erk:plan-implement" in result.output
