"""Tests for setup-impl consolidated exec command.

Tests the auto-detection paths: --file setup and no-plan-found error.
Issue-based setup is tested via test_setup_impl_from_issue.py.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.setup_impl import setup_impl
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub


def test_file_setup_creates_impl(tmp_path: Path) -> None:
    """--file creates .impl/ with plan content and exits 0."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# My Feature Plan\n\nSome content here.\n", encoding="utf-8")

    git = FakeGit(current_branches={tmp_path: "master"})
    github = FakeGitHub()
    ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=git,
        github=github,
        repo_root=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(setup_impl, ["--file", str(plan_file)], obj=ctx)

    assert result.exit_code == 0
    # .impl/ should be created
    assert (tmp_path / ".impl" / "plan.md").exists()
    plan_content = (tmp_path / ".impl" / "plan.md").read_text(encoding="utf-8")
    assert "My Feature Plan" in plan_content


def test_no_plan_found_exits_1(tmp_path: Path) -> None:
    """Exits 1 when no plan source can be determined."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    github = FakeGitHub()
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
    """Auto-detects existing .impl/ without plan tracking."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Existing Plan\n\nContent.\n", encoding="utf-8")

    git = FakeGit(current_branches={tmp_path: "some-branch"})
    github = FakeGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(setup_impl, obj=ctx)

    assert result.exit_code == 0


def test_branch_detection_p_prefix(tmp_path: Path) -> None:
    """P-prefix branches no longer auto-detect plan numbers."""
    # P-prefix branches no longer resolve to issue numbers
    git = FakeGit(current_branches={tmp_path: "P9999-feature"})
    github = FakeGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(setup_impl, obj=ctx)

    # Should fail with no_plan_found since branch doesn't resolve
    assert result.exit_code == 1
    assert "no_plan_found" in result.output
