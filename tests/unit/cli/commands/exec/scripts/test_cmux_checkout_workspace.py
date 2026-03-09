"""Tests for cmux-open-pr exec script."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.cmux_checkout_workspace import cmux_open_pr
from erk_shared.context.context import ErkContext
from erk_shared.fakes.cmux import FakeCmux
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails


def _make_pr_details(*, pr_number: int, head_ref_name: str) -> PRDetails:
    """Create minimal PRDetails for testing."""
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title=f"PR #{pr_number}",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
    )


def test_cmux_open_pr_success_with_branch() -> None:
    """cmux-open-pr succeeds when branch is provided."""
    fake_cmux = FakeCmux(workspace_ref="workspace-12345")
    ctx = ErkContext.for_test(cmux=fake_cmux)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152", "--branch", "my-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 8152
    assert output["branch"] == "my-branch"
    assert output["workspace_name"] == "workspace-12345"

    assert len(fake_cmux.create_calls) == 1
    assert "erk pr checkout" in fake_cmux.create_calls[0].command
    assert len(fake_cmux.rename_calls) == 1
    assert fake_cmux.rename_calls[0].workspace_ref == "workspace-12345"
    assert fake_cmux.rename_calls[0].new_name == "my-branch"


def test_cmux_open_pr_success_auto_detect_branch() -> None:
    """cmux-open-pr auto-detects branch when not provided."""
    pr_details = _make_pr_details(pr_number=8152, head_ref_name="feature-branch")
    fake_github = FakeLocalGitHub(pr_details={8152: pr_details})
    fake_cmux = FakeCmux(workspace_ref="workspace-99999")
    ctx = ErkContext.for_test(github=fake_github, cmux=fake_cmux)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 8152
    assert output["branch"] == "feature-branch"


def test_cmux_open_pr_fails_auto_detect() -> None:
    """cmux-open-pr fails gracefully when branch auto-detection fails."""
    fake_github = FakeLocalGitHub()  # empty pr_details -> PRNotFound
    ctx = ErkContext.for_test(github=fake_github)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to detect head branch" in output["error"]


def test_cmux_open_pr_fails_cmux_command() -> None:
    """cmux-open-pr fails when cmux create_workspace raises RuntimeError."""
    fake_cmux = FakeCmux(
        workspace_ref="unused",
        create_error="cmux error: workspace already exists",
    )
    ctx = ErkContext.for_test(cmux=fake_cmux)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152", "--branch", "my-branch"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to create cmux workspace" in output["error"]


def test_cmux_open_pr_teleport_mode() -> None:
    """cmux-open-pr --mode teleport uses teleport command."""
    fake_cmux = FakeCmux(workspace_ref="workspace-12345")
    ctx = ErkContext.for_test(cmux=fake_cmux)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152", "--branch", "my-branch", "--mode", "teleport"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert len(fake_cmux.create_calls) == 1
    assert "erk pr teleport" in fake_cmux.create_calls[0].command
    assert "--new-slot --script --sync" in fake_cmux.create_calls[0].command


def test_cmux_open_pr_default_mode_uses_checkout() -> None:
    """cmux-open-pr default mode uses checkout command."""
    fake_cmux = FakeCmux(workspace_ref="workspace-12345")
    ctx = ErkContext.for_test(cmux=fake_cmux)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152", "--branch", "my-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert len(fake_cmux.create_calls) == 1
    assert "erk pr checkout" in fake_cmux.create_calls[0].command
    assert "--script" in fake_cmux.create_calls[0].command
    assert "teleport" not in fake_cmux.create_calls[0].command


def test_cmux_open_pr_extracts_workspace_name() -> None:
    """cmux-open-pr correctly extracts workspace name from output."""
    fake_cmux = FakeCmux(workspace_ref="Created workspace: my-workspace")
    ctx = ErkContext.for_test(cmux=fake_cmux)

    runner = CliRunner()
    result = runner.invoke(
        cmux_open_pr,
        ["--pr", "8152", "--branch", "my-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["workspace_name"] == "my-workspace"
