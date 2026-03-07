"""Tests for Graphite tracking at PR checkout.

These tests verify that pr checkout properly tracks and submits branches
with Graphite when checking out PRs into new worktrees.
"""

import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    number: int,
    head_ref_name: str,
    is_cross_repository: bool,
    state: str,
    base_ref_name: str = "main",
) -> PRDetails:
    """Create a PRDetails for testing."""
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


def test_pr_checkout_tracks_untracked_branch_with_graphite() -> None:
    """Test pr checkout tracks untracked branch with Graphite.

    When Graphite is enabled and checking out a PR into a new worktree,
    checkout should track the branch with Graphite (gt track) but NOT
    submit (force-push is unnecessary at checkout time).

    The track_branch call must use the repo root as cwd (not the worktree path),
    because Graphite resolves branch refs via .git/ which differs in worktrees.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=100,
            head_ref_name="feature-graphite",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={100: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-graphite"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-graphite"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "100"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Created worktree for PR #100" in result.output
        # Should track but NOT submit
        assert "Tracking branch with Graphite" in result.output
        assert "Submitting to link with Graphite" not in result.output
        # track_branch must be called with repo root, not worktree path
        assert len(graphite.track_branch_calls) == 1
        track_cwd, track_branch, track_parent = graphite.track_branch_calls[0]
        assert track_cwd == env.cwd, (
            f"track_branch cwd should be repo root ({env.cwd}), not worktree path ({track_cwd})"
        )
        assert track_branch == "feature-graphite"
        assert track_parent == "main"


def test_pr_checkout_skips_graphite_for_existing_worktree() -> None:
    """Test pr checkout skips Graphite linking for already-existing worktrees.

    When a worktree already exists for the branch (already_existed=True),
    the Graphite linking should be skipped as the branch may already be tracked.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=101,
            head_ref_name="existing-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={101: pr_details})
        existing_wt_path = env.repo.worktrees_dir / "existing-branch"
        existing_wt_path.mkdir(parents=True, exist_ok=True)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=existing_wt_path, branch="existing-branch"),
                ]
            },
            local_branches={env.cwd: ["main", "existing-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, existing_wt_path},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "101"], obj=ctx)

        assert result.exit_code == 0
        assert "already checked out" in result.output
        # Should NOT have Graphite linking messages (worktree already exists)
        assert "Tracking branch with Graphite" not in result.output


def test_pr_checkout_skips_graphite_for_already_tracked_not_diverged() -> None:
    """Test pr checkout skips Graphite when branch is tracked and not diverged.

    When a branch already has a parent in Graphite's metadata (get_parent_branch
    returns non-None) and the SHA matches Graphite's cache, no retracking is needed.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=102,
            head_ref_name="tracked-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={102: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "tracked-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/tracked-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Use FakeGraphite with pre-configured parent branch (branch is already tracked)
        # tracked_revision matches commit_sha = not diverged
        from erk_shared.gateway.graphite.types import BranchMetadata

        graphite = FakeGraphite(
            branches={
                "tracked-branch": BranchMetadata(
                    name="tracked-branch",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                    tracked_revision="abc123",
                ),
            }
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "102"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Created worktree for PR #102" in result.output
        # Should NOT have any Graphite messages (already tracked and not diverged)
        assert "Tracking branch with Graphite" not in result.output
        assert "Retracking diverged branch" not in result.output


def test_pr_checkout_skips_graphite_for_fork_prs() -> None:
    """Test pr checkout skips Graphite linking for cross-repository (fork) PRs.

    Fork PRs use pr/<number> branch naming and cannot be tracked with Graphite
    because the source branch is in a different repository.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        # Cross-repository PR (is_cross_repository=True)
        pr_details = _make_pr_details(
            number=103,
            head_ref_name="contributor-branch",
            is_cross_repository=True,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={103: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "103"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Created worktree for PR #103" in result.output
        # Should NOT have Graphite linking messages (fork PRs not supported)
        assert "Tracking branch with Graphite" not in result.output


def test_pr_checkout_retracks_diverged_graphite_branch() -> None:
    """Test pr checkout retracks after worktree creation and rebase.

    When a branch is already tracked by Graphite and the local branch
    is force-updated to match remote, the retrack happens after rebase
    so Graphite's cached SHA matches the post-rebase commit.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=105,
            head_ref_name="diverged-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={105: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "diverged-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/diverged-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Branch is tracked but SHA diverged (tracked_revision != commit_sha)
        from erk_shared.gateway.graphite.types import BranchMetadata

        graphite = FakeGraphite(
            branches={
                "diverged-branch": BranchMetadata(
                    name="diverged-branch",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="new-sha-after-dispatch",
                    tracked_revision="old-sha-before-dispatch",
                ),
            }
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "105"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Created worktree for PR #105" in result.output
        # Should NOT track fresh — branch is already tracked
        assert "Tracking branch with Graphite" not in result.output
        # retrack_branch must be called with repo root, not worktree path
        assert len(graphite.retrack_branch_calls) == 1
        retrack_cwd, retrack_branch = graphite.retrack_branch_calls[0]
        assert retrack_cwd == env.cwd, (
            f"retrack_branch cwd should be repo root ({env.cwd}), not worktree path ({retrack_cwd})"
        )
        assert retrack_branch == "diverged-branch"


def test_pr_checkout_script_mode_no_gt_submit_for_new_worktree() -> None:
    """Test pr checkout in script mode never includes gt submit.

    Checkout no longer supports --sync. The gt submit behavior is now
    exclusively on teleport. Checkout script mode should never include
    gt submit in the activation script.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=110,
            head_ref_name="feature-submit",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={110: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-submit"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-submit"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        result = runner.invoke(pr_group, ["checkout", "110", "--script"], obj=ctx)

        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert "gt submit --no-interactive" not in script_content


def test_pr_checkout_script_mode_no_gt_submit_for_existing_worktree() -> None:
    """Test pr checkout in script mode omits gt submit for existing worktrees."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="existing-submit-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={111: pr_details})
        existing_wt_path = env.repo.worktrees_dir / "existing-submit-branch"
        existing_wt_path.mkdir(parents=True, exist_ok=True)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=existing_wt_path, branch="existing-submit-branch"),
                ]
            },
            local_branches={env.cwd: ["main", "existing-submit-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, existing_wt_path},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        result = runner.invoke(pr_group, ["checkout", "111", "--script"], obj=ctx)

        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert "gt submit --no-interactive" not in script_content


def test_pr_checkout_script_mode_no_gt_submit_for_fork_prs() -> None:
    """Test pr checkout in script mode omits gt submit for fork PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=112,
            head_ref_name="fork-branch",
            is_cross_repository=True,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={112: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        result = runner.invoke(pr_group, ["checkout", "112", "--script"], obj=ctx)

        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert "gt submit --no-interactive" not in script_content


def test_pr_checkout_skips_graphite_when_disabled() -> None:
    """Test pr checkout skips Graphite linking when Graphite is disabled.

    When Graphite is disabled (use_graphite=False, the default), the checkout
    command should not attempt any Graphite operations.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=104,
            head_ref_name="no-graphite-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeLocalGitHub(pr_details={104: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "no-graphite-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/no-graphite-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        # Note: use_graphite=False is the default
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=False)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "104"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Created worktree for PR #104" in result.output
        # Should NOT have Graphite linking messages
        assert "Tracking branch with Graphite" not in result.output
        assert "Submitting to link with Graphite" not in result.output


def test_pr_checkout_stacked_pr_rebases_then_tracks() -> None:
    """Test stacked PR checkout rebases onto base branch before Graphite tracking.

    For stacked PRs (base is not trunk), the checkout must:
    1. Create the worktree
    2. Rebase onto the base branch
    3. Track/retrack with Graphite AFTER rebase

    This ordering prevents Graphite divergence where the cached SHA
    becomes stale after rebase changes the branch's commit.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        # Stacked PR: base is "parent-branch", not "main"
        pr_details = _make_pr_details(
            number=120,
            head_ref_name="stacked-feature",
            is_cross_repository=False,
            state="OPEN",
            base_ref_name="parent-branch",
        )
        github = FakeLocalGitHub(pr_details={120: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "stacked-feature", "parent-branch"]},
            remote_branches={
                env.cwd: [
                    "origin/main",
                    "origin/stacked-feature",
                    "origin/parent-branch",
                ]
            },
            branch_heads={
                "parent-branch": "local-parent-sha",
                "origin/parent-branch": "remote-parent-sha",
            },
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "120"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Rebasing onto base branch" in result.output
        # Graphite tracking should happen (untracked branch)
        assert "Tracking branch with Graphite" in result.output
        assert len(graphite.track_branch_calls) == 1
        track_cwd, track_branch, track_parent = graphite.track_branch_calls[0]
        assert track_cwd == env.cwd
        assert track_branch == "stacked-feature"
        assert track_parent == "parent-branch"
        # Rebase should have happened before tracking
        assert len(git.rebase_onto_calls) == 1
        # Parent branch should have been updated via update_local_ref
        assert len(git.updated_refs) == 1
        ref_root, ref_branch, ref_sha = git.updated_refs[0]
        assert ref_branch == "parent-branch"
        assert ref_sha == "remote-parent-sha"
