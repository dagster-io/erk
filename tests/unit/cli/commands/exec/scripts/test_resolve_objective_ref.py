"""Tests for resolve-objective-ref exec command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.resolve_objective_ref import (
    _resolve_objective_ref_impl,
    resolve_objective_ref,
)
from erk_shared.context.context import ErkContext
from erk_shared.fakes.git import FakeGit

# --- Implementation Logic Tests ---


def test_resolves_plain_number() -> None:
    result = _resolve_objective_ref_impl(
        ref="3679",
        current_branch=None,
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": True, "objective_number": 3679, "source": "argument"}


def test_resolves_url() -> None:
    result = _resolve_objective_ref_impl(
        ref="https://github.com/owner/repo/issues/456",
        current_branch=None,
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": True, "objective_number": 456, "source": "argument"}


def test_resolves_from_branch_name() -> None:
    result = _resolve_objective_ref_impl(
        ref="",
        current_branch="plnd/O8762-some-slug-01-15-1430",
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": True, "objective_number": 8762, "source": "branch_name"}


def test_resolves_from_branch_name_lowercase_o() -> None:
    result = _resolve_objective_ref_impl(
        ref="",
        current_branch="plnd/o123-feature-01-15-1430",
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": True, "objective_number": 123, "source": "branch_name"}


def test_falls_back_to_plan_metadata() -> None:
    result = _resolve_objective_ref_impl(
        ref="",
        current_branch="plnd/fix-auth-bug-01-15-1430",
        get_objective_for_branch=lambda _: 999,
    )
    assert result == {"resolved": True, "objective_number": 999, "source": "plan_metadata"}


def test_not_resolved_detached_head() -> None:
    result = _resolve_objective_ref_impl(
        ref="",
        current_branch=None,
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": False}


def test_not_resolved_no_match() -> None:
    result = _resolve_objective_ref_impl(
        ref="",
        current_branch="feature-branch",
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": False}


def test_branch_name_takes_priority_over_plan_metadata() -> None:
    """Branch name objective wins over plan metadata lookup."""
    result = _resolve_objective_ref_impl(
        ref="",
        current_branch="plnd/O100-feature-01-15-1430",
        get_objective_for_branch=lambda _: 200,
    )
    assert result["objective_number"] == 100
    assert result["source"] == "branch_name"


def test_unparseable_ref_returns_not_resolved() -> None:
    result = _resolve_objective_ref_impl(
        ref="not-a-number-or-url",
        current_branch=None,
        get_objective_for_branch=lambda _: None,
    )
    assert result == {"resolved": False}


# --- CLI Command Tests ---


def test_cli_resolves_argument(tmp_path: Path) -> None:
    git = FakeGit(current_branches={tmp_path: "main"})
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(resolve_objective_ref, ["3679"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["resolved"] is True
    assert output["objective_number"] == 3679
    assert output["source"] == "argument"


def test_cli_resolves_from_branch(tmp_path: Path) -> None:
    git = FakeGit(current_branches={tmp_path: "plnd/O456-fix-auth-01-15-1430"})
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(resolve_objective_ref, obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["resolved"] is True
    assert output["objective_number"] == 456
    assert output["source"] == "branch_name"


def test_cli_not_resolved_exits_zero(tmp_path: Path) -> None:
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(resolve_objective_ref, obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["resolved"] is False
