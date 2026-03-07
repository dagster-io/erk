"""Tests for setup-impl consolidated exec command.

Tests the auto-detection paths: --file setup, no-plan-found error,
and PR-based setup via _handle_issue_setup.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.setup_impl import setup_impl
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.impl_folder import get_impl_dir
from erk_shared.plan_store.planned_pr import PlannedPRBackend

BRANCH = "test/branch"
"""Test branch name used across tests."""


def test_file_setup_creates_impl(tmp_path: Path) -> None:
    """--file creates .impl/ with plan content and exits 0."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# My Feature Plan\n\nSome content here.\n", encoding="utf-8")

    git = FakeGit(current_branches={tmp_path: "master"})
    github = FakeLocalGitHub()
    ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=git,
        github=github,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(setup_impl, ["--file", str(plan_file)], obj=ctx)

    assert result.exit_code == 0
    # Impl folder should be created (branch-scoped under .erk/impl-context/)
    impl_plan = tmp_path / ".erk" / "impl-context" / "my-feature-plan" / "plan.md"
    assert impl_plan.exists()
    plan_content = impl_plan.read_text(encoding="utf-8")
    assert "My Feature Plan" in plan_content


def test_no_plan_found_exits_1(tmp_path: Path) -> None:
    """Exits 1 when no plan source can be determined."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    github = FakeLocalGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(setup_impl, obj=ctx)

    assert result.exit_code == 1
    # Should have JSON error on stdout
    lines = result.output.strip().split("\n")
    last_line = lines[-1]
    output = json.loads(last_line)
    assert output["success"] is False
    assert output["error"] == "no_plan_found"


def test_existing_impl_no_tracking(tmp_path: Path) -> None:
    """Auto-detects existing branch-scoped impl folder without plan tracking."""
    impl_dir = get_impl_dir(tmp_path, branch_name=BRANCH)
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Existing Plan\n\nContent.\n", encoding="utf-8")

    git = FakeGit(current_branches={tmp_path: BRANCH})
    github = FakeLocalGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(setup_impl, obj=ctx)

    assert result.exit_code == 0


def test_branch_detection_p_prefix(tmp_path: Path) -> None:
    """P-prefix branches no longer auto-detect plan numbers."""
    # P-prefix branches no longer resolve to issue numbers
    git = FakeGit(current_branches={tmp_path: "P9999-feature"})
    github = FakeLocalGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(setup_impl, obj=ctx)

    # Should fail with no_plan_found since branch doesn't resolve
    assert result.exit_code == 1
    assert "no_plan_found" in result.output


def test_issue_setup_invokes_setup_impl_from_issue(tmp_path: Path) -> None:
    """--issue delegates to setup_impl_from_issue without TypeError.

    Regression test: setup_impl previously passed branch_slug= to
    setup_impl_from_issue which doesn't accept that parameter.
    """
    plan_branch = "plan-fix-branch-slug-02-24"
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    plan_result = backend.create_plan(
        repo_root=tmp_path,
        title="Fix branch slug",
        content="# Fix\n\nRemove dead branch_slug parameter.",
        labels=("erk-plan",),
        metadata={"branch_name": plan_branch},
        summary=None,
    )
    pr_number = int(plan_result.plan_id)

    fake_git = FakeGit(
        current_branches={tmp_path: plan_branch},
    )

    ctx = context_for_test(
        github=fake_github,
        git=fake_git,
        graphite=FakeGraphite(),
        cwd=tmp_path,
        repo_root=tmp_path,
        plan_store=backend,
    )

    runner = CliRunner()
    result = runner.invoke(
        setup_impl,
        ["--issue", str(pr_number)],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    output_lines = result.output.strip().split("\n")
    json_lines = [line for line in reversed(output_lines) if line.startswith("{")]
    assert json_lines, "Expected JSON output"
    output = json.loads(json_lines[0])
    assert output["success"] is True
    assert output["plan_number"] == pr_number
