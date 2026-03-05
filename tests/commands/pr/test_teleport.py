"""Tests for erk pr teleport command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    number: int,
    head_ref_name: str,
    *,
    is_cross_repository: bool = False,
    state: str = "OPEN",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}",
        body="",
        state=state,
        is_draft=False,
        base_ref_name="main",
        head_ref_name=head_ref_name,
        is_cross_repository=is_cross_repository,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_teleport_pr_not_found() -> None:
    """Teleport errors when PR doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        github = FakeGitHub(pr_details={})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "999"], obj=ctx)
        assert result.exit_code == 1
        assert "Could not find PR #999" in result.output


def test_teleport_cross_repo_errors() -> None:
    """Teleport rejects cross-repository (fork) PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature", is_cross_repository=True)
        github = FakeGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 1
        assert "cross-repository" in result.output


def test_teleport_wrong_branch_errors() -> None:
    """Teleport errors when current branch doesn't match PR branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 1
        assert "feature-branch" in result.output
        assert "--new-slot" in result.output


def test_teleport_in_place_with_force() -> None:
    """Teleport force-resets current branch to match remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (1, 2)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Teleported" in result.output
        assert "feature-branch" in result.output


def test_teleport_already_in_sync_exits_cleanly() -> None:
    """Teleport exits with 0 when branch is already in sync."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (0, 0)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 0
        assert "already in sync" in result.output
