"""Tests for `erk json one-shot` and the human command split."""

from __future__ import annotations

import json

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.remote_github.fake import FakeRemoteGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_remote() -> FakeRemoteGitHub:
    return FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )


def test_machine_command_success() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()
        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)
        result = runner.invoke(
            cli,
            ["json", "one-shot"],
            obj=ctx,
            input=json.dumps({"prompt": "fix the import in config.py"}),
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["dry_run"] is False
    assert data["pr_number"] == 1
    assert "pr_url" in data
    assert "run_url" in data


def test_machine_command_dry_run() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()
        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)
        result = runner.invoke(
            cli,
            ["json", "one-shot"],
            obj=ctx,
            input=json.dumps({"prompt": "add type hints", "dry_run": True}),
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["dry_run"] is True
    assert data["prompt"] == "add type hints"
    assert remote.created_refs == []
    assert remote.created_pull_requests == []
    assert remote.dispatched_workflows == []


def test_machine_command_error_for_empty_prompt() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()
        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)
        result = runner.invoke(
            cli,
            ["json", "one-shot"],
            obj=ctx,
            input=json.dumps({"prompt": "   "}),
        )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is False
    assert data["error_type"] == "invalid_input"


def test_human_command_no_longer_accepts_json_flag() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()
        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)
        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "--json"],
            obj=ctx,
        )

    assert result.exit_code != 0
    assert "--json" in result.output
