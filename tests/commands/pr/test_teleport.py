"""Tests for erk pr teleport command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    number: int,
    head_ref_name: str,
    *,
    is_cross_repository: bool = False,
    state: str = "OPEN",
    base_ref_name: str = "main",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}",
        body="",
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
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
        github = FakeLocalGitHub(pr_details={})
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
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 1
        assert "cross-repository" in result.output


def test_teleport_wrong_branch_switches_and_teleports() -> None:
    """Teleport automatically switches branch when it's not yet checked out."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # feature-branch doesn't exist yet
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Teleported" in result.output
        assert "feature-branch" in result.output


def test_teleport_wrong_branch_exists_in_other_worktree() -> None:
    """Teleport prints activation instructions when branch is already checked out elsewhere."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        other_worktree_path = env.repo.worktrees_dir / "other"
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=other_worktree_path, branch="feature-branch", is_root=False),
                ]
            },
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 0
        assert "feature-branch" in result.output
        assert str(other_worktree_path) in result.output


def test_teleport_in_place_with_force() -> None:
    """Teleport force-resets current branch to match remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
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
        github = FakeLocalGitHub(pr_details={123: pr})
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


def test_teleport_stacked_pr_fetches_base_with_graphite() -> None:
    """Teleport fetches base branch and tracks with Graphite for stacked PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Stacked PR: base is not main
        pr = _make_pr_details(
            123,
            "plnd/add-print-statement",
            base_ref_name="plnd/rename-sync-teleport",
        )
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # Base branch not yet local
            remote_branches={
                env.cwd: [
                    "origin/main",
                    "origin/plnd/rename-sync-teleport",
                    "origin/plnd/add-print-statement",
                ]
            },
        )
        graphite = FakeGraphite(
            branches={
                "plnd/rename-sync-teleport": BranchMetadata(
                    name="plnd/rename-sync-teleport",
                    parent="main",
                    children=["plnd/add-print-statement"],
                    is_trunk=False,
                    commit_sha=None,
                ),
            }
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Fetching base branch" in result.output
        assert "Tracking branch with Graphite" in result.output
        # Verify base branch was fetched
        assert ("origin", "plnd/rename-sync-teleport") in git.fetched_branches
        # Verify tracking branch was created for base
        assert (
            "plnd/rename-sync-teleport",
            "origin/plnd/rename-sync-teleport",
        ) in git.created_tracking_branches


def test_teleport_trunk_parent_tracks_without_base_fetch() -> None:
    """Teleport skips base fetch but still tracks with Graphite for non-stacked PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # PR with base = main (trunk) — not stacked, but still needs Graphite tracking
        pr = _make_pr_details(123, "feature-branch", base_ref_name="main")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
        )
        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Fetching base branch" not in result.output
        assert "Tracking branch with Graphite" in result.output
        # No base branch fetching (trunk is already local)
        assert len(git.created_tracking_branches) == 0


def test_teleport_already_tracked_retracks() -> None:
    """Teleport retracks already-tracked branches after force-reset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Stacked PR
        pr = _make_pr_details(
            123,
            "plnd/add-print-statement",
            base_ref_name="plnd/rename-sync-teleport",
        )
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={
                env.cwd: [
                    "main",
                    "plnd/rename-sync-teleport",
                    "plnd/add-print-statement",
                ]
            },
            remote_branches={
                env.cwd: [
                    "origin/main",
                    "origin/plnd/rename-sync-teleport",
                    "origin/plnd/add-print-statement",
                ]
            },
            ahead_behind={(env.cwd, "plnd/add-print-statement"): (2, 0)},
        )
        # Configure branch as already tracked by Graphite
        graphite = FakeGraphite(
            branches={
                "plnd/rename-sync-teleport": BranchMetadata(
                    name="plnd/rename-sync-teleport",
                    parent="main",
                    children=["plnd/add-print-statement"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "plnd/add-print-statement": BranchMetadata(
                    name="plnd/add-print-statement",
                    parent="plnd/rename-sync-teleport",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
            }
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Tracking branch with Graphite" not in result.output  # Already tracked
        # Verify retrack was called - check git's tracked branches
        # (should be empty since graphite_branch_ops.retrack was called)
        # The retrack happens via graphite_branch_ops, so we just verify no fresh track happened
        assert len(git.created_tracking_branches) == 0  # Fresh tracking not called
