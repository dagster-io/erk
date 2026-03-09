"""Tests for impl-verify kit CLI command.

Tests the guardrail that ensures implementation folder is preserved after implementation.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_verify import impl_verify
from erk_shared.context.context import ErkContext
from erk_shared.fakes.git import FakeGit
from erk_shared.impl_folder import create_impl_folder

BRANCH = "feature/test-branch"
"""Test branch name used across tests."""


def _make_ctx(tmp_path: Path, *, branch: str = BRANCH) -> ErkContext:
    """Create test ErkContext with FakeGit configured for the given branch."""
    return ErkContext.for_test(
        cwd=tmp_path,
        git=FakeGit(current_branches={tmp_path: branch}),
    )


def test_impl_verify_succeeds_when_branch_scoped_impl_exists(tmp_path: Path) -> None:
    """Test impl-verify returns success JSON when branch-scoped impl exists."""
    create_impl_folder(tmp_path, "# Plan\n", branch_name=BRANCH, overwrite=False)

    runner = CliRunner()
    result = runner.invoke(impl_verify, obj=_make_ctx(tmp_path))

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert "impl_dir" in data


def test_impl_verify_fails_when_impl_missing(tmp_path: Path) -> None:
    """Test impl-verify returns error JSON when no impl folder is found."""
    runner = CliRunner()
    result = runner.invoke(impl_verify, obj=_make_ctx(tmp_path))

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert "error" in data
    assert "deleted" in data["error"]
    assert "action" in data


def test_impl_verify_empty_impl_context_not_found(tmp_path: Path) -> None:
    """Test impl-verify returns error when .erk/impl-context/ exists but has no plan.md subdirs."""
    impl_context_dir = tmp_path / ".erk" / "impl-context"
    impl_context_dir.mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(impl_verify, obj=_make_ctx(tmp_path))

    # Should fail because no subdir with plan.md exists
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
