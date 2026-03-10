"""Tests for upload-impl-session exec command.

Tests the session upload from implementation plan reference.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.upload_impl_session import upload_impl_session
from erk_shared.context.context import ErkContext
from erk_shared.impl_folder import get_impl_dir, save_plan_ref
from tests.fakes.gateway.git import FakeGit

BRANCH = "feature/test-branch"
"""Test branch name used across tests."""


def _make_ctx(tmp_path: Path, *, branch: str = BRANCH) -> ErkContext:
    """Create test ErkContext with FakeGit configured for the given branch."""
    return ErkContext.for_test(
        cwd=tmp_path,
        git=FakeGit(current_branches={tmp_path: branch}),
    )


def _setup_impl_with_plan_ref(tmp_path: Path, *, pr_id: str) -> None:
    """Create branch-scoped impl dir with plan.md and ref.json."""
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Test Plan", encoding="utf-8")
    save_plan_ref(
        impl_dir,
        provider="github",
        plan_id=pr_id,
        url=f"https://github.com/test/repo/issues/{pr_id}",
        labels=(),
        objective_id=None,
        node_ids=None,
    )


def test_no_impl_folder(tmp_path: Path) -> None:
    """Reports not uploaded when no impl folder exists."""
    runner = CliRunner()
    result = runner.invoke(
        upload_impl_session, ["--session-id", "abc-123"], obj=_make_ctx(tmp_path)
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["uploaded"] is False
    assert output["reason"] == "no_impl_folder"


def test_no_plan_ref(tmp_path: Path) -> None:
    """Reports not uploaded when impl folder exists but has no plan reference."""
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Test", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        upload_impl_session, ["--session-id", "abc-123"], obj=_make_ctx(tmp_path)
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["uploaded"] is False
    assert output["reason"] == "no_plan_tracking"


def test_no_session_found(tmp_path: Path) -> None:
    """Reports not uploaded when no Claude session can be found."""
    _setup_impl_with_plan_ref(tmp_path, pr_id="123")

    # ErkContext.for_test doesn't include claude_installation by default,
    # so require_claude_installation will raise SystemExit
    runner = CliRunner()
    result = runner.invoke(
        upload_impl_session, ["--session-id", "abc-123"], obj=_make_ctx(tmp_path)
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["uploaded"] is False
