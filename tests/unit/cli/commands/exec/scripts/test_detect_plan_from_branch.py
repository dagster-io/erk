"""Tests for detect-plan-from-branch exec command.

Tests both the implementation logic (_detect_plan_from_branch_impl)
and the CLI command (detect_plan_from_branch).
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.detect_plan_from_branch import (
    _detect_plan_from_branch_impl,
    detect_plan_from_branch,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub

# --- Implementation Logic Tests ---


def test_detect_impl_branch_name_p_prefix() -> None:
    """P-prefix branches no longer resolve to plan numbers."""
    result = _detect_plan_from_branch_impl(
        current_branch="P2521-fix-auth-bug-01-15-1430",
        pr_lookup=lambda: None,
    )
    assert result == {"found": False}


def test_detect_impl_branch_name_no_prefix() -> None:
    """Non-P branches don't resolve to plan numbers either."""
    result = _detect_plan_from_branch_impl(
        current_branch="42-fix-bug",
        pr_lookup=lambda: None,
    )
    assert result == {"found": False}


def test_detect_impl_pr_lookup_fallback() -> None:
    """Falls back to PR lookup when branch name has no issue number."""
    result = _detect_plan_from_branch_impl(
        current_branch="plnd/fix-auth-bug-01-15-1430",
        pr_lookup=lambda: 7890,
    )
    assert result == {"found": True, "plan_number": 7890, "detection_method": "pr_lookup"}


def test_detect_impl_not_found() -> None:
    """Returns not-found when neither branch name nor PR lookup succeeds."""
    result = _detect_plan_from_branch_impl(
        current_branch="feature-branch",
        pr_lookup=lambda: None,
    )
    assert result == {"found": False}


def test_detect_impl_detached_head() -> None:
    """Returns not-found when in detached HEAD state."""
    result = _detect_plan_from_branch_impl(
        current_branch=None,
        pr_lookup=lambda: None,
    )
    assert result == {"found": False}


def test_detect_impl_branch_name_takes_priority() -> None:
    """PR lookup is used when branch name doesn't resolve."""
    result = _detect_plan_from_branch_impl(
        current_branch="P100-feature",
        pr_lookup=lambda: 200,
    )
    assert result["plan_number"] == 200
    assert result["detection_method"] == "pr_lookup"


# --- CLI Command Tests ---


def test_cli_detects_from_branch_name(tmp_path: Path) -> None:
    """CLI outputs not-found for P-prefix branch."""
    git = FakeGit(current_branches={tmp_path: "P2521-fix-auth"})
    github = FakeLocalGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(detect_plan_from_branch, obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["found"] is False


def test_cli_not_found_exits_zero(tmp_path: Path) -> None:
    """CLI always exits 0, even when no plan is found."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    github = FakeLocalGitHub()
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, github=github, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(detect_plan_from_branch, obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["found"] is False
