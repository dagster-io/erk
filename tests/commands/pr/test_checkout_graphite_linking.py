"""Tests for Graphite tracking at PR checkout.

These tests verify that pr checkout properly tracks and submits branches
with Graphite when checking out PRs into new worktrees.
"""

import os
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails
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


def test_pr_checkout_tracks_and_submits_with_graphite() -> None:
    """Test pr checkout tracks branch and submits to link with Graphite.

    When Graphite is enabled and checking out a PR into a new worktree,
    checkout should:
    1. Track the branch with Graphite (gt track)
    2. Submit to establish remote stack metadata (gt submit)
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=100,
            head_ref_name="feature-graphite",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={100: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-graphite"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-graphite"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "100"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Created worktree for PR #100" in result.output
        # Check for Graphite linking messages
        assert "Tracking branch with Graphite" in result.output
        assert "Submitting to link with Graphite" in result.output
        assert "Branch linked with Graphite" in result.output


def test_pr_checkout_skips_graphite_for_existing_worktree() -> None:
    """Test pr checkout skips Graphite linking for already-existing worktrees.

    When a worktree already exists for the branch (already_existed=True),
    the Graphite linking should be skipped as the branch may already be tracked.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=101,
            head_ref_name="existing-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={101: pr_details})
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


def test_pr_checkout_skips_graphite_for_already_tracked() -> None:
    """Test pr checkout skips Graphite linking when branch is already tracked.

    When a branch already has a parent in Graphite's metadata (get_parent_branch
    returns non-None), the Graphite linking should be skipped for idempotence.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=102,
            head_ref_name="tracked-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={102: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "tracked-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/tracked-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # Use FakeGraphite with pre-configured parent branch (branch is already tracked)
        from erk_shared.gateway.graphite.fake import FakeGraphite
        from erk_shared.gateway.graphite.types import BranchMetadata

        graphite = FakeGraphite(
            branches={
                "tracked-branch": BranchMetadata(
                    name="tracked-branch",
                    parent="main",  # Already has a parent = already tracked
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
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
        # Should NOT have Graphite linking messages (already tracked)
        assert "Tracking branch with Graphite" not in result.output


def test_pr_checkout_skips_graphite_for_fork_prs() -> None:
    """Test pr checkout skips Graphite linking for cross-repository (fork) PRs.

    Fork PRs use pr/<number> branch naming and cannot be tracked with Graphite
    because the source branch is in a different repository.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        # Cross-repository PR (is_cross_repository=True)
        pr_details = _make_pr_details(
            number=103,
            head_ref_name="contributor-branch",
            is_cross_repository=True,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={103: pr_details})
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


def test_pr_checkout_skips_graphite_when_disabled() -> None:
    """Test pr checkout skips Graphite linking when Graphite is disabled.

    When Graphite is disabled (use_graphite=False, the default), the checkout
    command should not attempt any Graphite operations.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=104,
            head_ref_name="no-graphite-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={104: pr_details})
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
