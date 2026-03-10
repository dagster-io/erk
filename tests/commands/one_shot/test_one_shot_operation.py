"""Tests for one-shot core operation (run_one_shot)."""

import pytest
from click.testing import CliRunner

from erk.cli.commands.one_shot_operation import OneShotRequest, run_one_shot
from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchResult,
    OneShotDryRunResult,
)
from erk.cli.ensure import UserFacingCliError
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


def test_run_one_shot_dispatch() -> None:
    """run_one_shot returns OneShotDispatchResult on success."""
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

        request = OneShotRequest(prompt="fix the import in config.py")
        result = run_one_shot(request, ctx=ctx)

        assert isinstance(result, OneShotDispatchResult)
        assert result.pr_number == 1
        assert result.run_id == "run-1"


def test_run_one_shot_dry_run() -> None:
    """run_one_shot returns OneShotDryRunResult when dry_run=True."""
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

        request = OneShotRequest(prompt="add type hints", dry_run=True)
        result = run_one_shot(request, ctx=ctx)

        assert isinstance(result, OneShotDryRunResult)
        assert result.prompt == "add type hints"
        assert result.base_branch == "main"
        # Verify no mutations
        assert len(remote.created_refs) == 0
        assert len(remote.created_pull_requests) == 0


def test_run_one_shot_empty_prompt_raises() -> None:
    """run_one_shot raises UserFacingCliError for empty prompt."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        ctx = build_workspace_test_context(env, git=git, github=github)

        request = OneShotRequest(prompt="   ")
        with pytest.raises(UserFacingCliError) as exc_info:
            run_one_shot(request, ctx=ctx)

        assert exc_info.value.error_type == "invalid_input"


def test_run_one_shot_mutually_exclusive_flags() -> None:
    """run_one_shot raises for --repo + --ref-current."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        ctx = build_workspace_test_context(env, git=git, github=github)

        request = OneShotRequest(prompt="fix bug", target_repo="owner/repo", ref_current=True)
        with pytest.raises(UserFacingCliError) as exc_info:
            run_one_shot(request, ctx=ctx)

        assert "mutually exclusive" in str(exc_info.value).lower()
