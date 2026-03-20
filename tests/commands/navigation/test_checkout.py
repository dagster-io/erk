"""Tests for erk slot checkout command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.graphite import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_checkout_to_branch_in_single_worktree() -> None:
    """Test switching to a branch that is checked out in exactly one worktree.

    This test uses erk_inmem_env() for in-memory testing without filesystem I/O.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        # Use sentinel paths (no mkdir() needed in pure mode)
        feature_wt = work_dir / "feature-wt"
        other_wt = work_dir / "other-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=other_wt, branch="other-feature"),
                    # feature-2 is checked out here
                    WorktreeInfo(path=feature_wt, branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "other-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create RepoContext to avoid filesystem checks in discover_repo_context
        repo = RepoContext(
            root=env.cwd,
            repo_name="repo",
            repo_dir=env.erk_root / "repo",
            worktrees_dir=env.erk_root / "repo" / "worktrees",
            pool_json_path=env.erk_root / "repo" / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-2", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should not checkout (already on the branch)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_wt) in script_content


def test_checkout_to_branch_not_found() -> None:
    """Test switching to a branch that doesn't exist in git."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "feature-1-wt", branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            # nonexistent-branch is NOT in this list
            local_branches={env.cwd: ["main", "feature-1"]},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout a branch that doesn't exist
        result = runner.invoke(
            cli, ["slot", "checkout", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "does not exist" in result.stderr
        assert "erk wt create --branch nonexistent-branch" in result.stderr


def test_checkout_allocates_slot_for_unchecked_branch() -> None:
    """Test that checkout allocates a slot when branch exists but is not checked out.

    Unified slot checkout allocates a new pool slot instead of checking out
    in the current worktree.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        work_dir = env.erk_root / env.cwd.name

        # Branch 'existing-branch' exists in git but is not checked out
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "existing-branch"]},  # exists in git
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout branch that exists but is not checked out
        result = runner.invoke(
            cli,
            ["slot", "checkout", "existing-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should succeed - allocates a slot
        assert result.exit_code == 0


def test_checkout_to_branch_in_stack_but_not_checked_out() -> None:
    """Test that checkout allocates a slot when branch exists but is not checked out."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        work_dir = env.erk_root / env.cwd.name
        wt1 = work_dir / "feature-1-wt"

        # feature-1 is checked out, but feature-base is not
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-1", "feature-base"]},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-base which exists in repo but is not checked out
        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-base", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should succeed - allocates a slot
        assert result.exit_code == 0


def test_checkout_works_without_graphite() -> None:
    """Test that checkout works without Graphite enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-1-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        # Graphite is NOT enabled - checkout should still work
        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-1", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should succeed - checkout does not require Graphite
        assert result.exit_code == 0
        script_path = Path(result.stdout.strip())
        # Verify script was written to in-memory store
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_checkout_already_on_target_branch() -> None:
    """Test checking out when already in the target worktree on the target branch.

    This test validates the TRUE 'already there' case where ctx.cwd matches the target worktree.
    Should show 'Already in worktree' message, NOT 'Switched to worktree'.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-1-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        # CRITICAL: Set cwd to feature_wt to simulate already being in target location
        test_ctx = env.build_context(git=git_ops, repo=repo, cwd=feature_wt)

        # Checkout feature-1 while already in feature_wt
        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-1", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed without checking out (already on the branch)
        assert result.exit_code == 0
        # Should not have checked out (it's already checked out)
        assert len(git_ops.checked_out_branches) == 0

        # Verify activation script was generated
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None

        # CRITICAL: Message should say "Already on branch" since we're already in target location
        assert "Already on branch" in script_content
        assert "feature-1" in script_content
        assert "feature-1-wt" in script_content
        # Should NOT say "Switched" since we didn't switch locations
        assert "Switched" not in script_content


def test_checkout_succeeds_when_branch_exactly_checked_out() -> None:
    """Test that checkout succeeds when branch is exactly checked out in a worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"
        other_wt = work_dir / "other-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=other_wt, branch="other-feature"),
                    WorktreeInfo(path=feature_wt, branch="feature-2"),  # feature-2 is checked out
                ]
            },
            current_branches={env.cwd: "other-feature"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-2", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Should not checkout (already on feature-2)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_checkout_with_multiple_worktrees_same_branch() -> None:
    """Test error when multiple worktrees have the same branch checked out."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        wt1 = work_dir / "wt1"
        wt2 = work_dir / "wt2"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=wt1, branch="feature-2"),
                    WorktreeInfo(path=wt2, branch="feature-2"),  # Same branch
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-2", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "exists in multiple worktrees" in result.stderr


def test_checkout_allocates_slot_for_remote_only_branch() -> None:
    """Test checkout allocates a slot when branch exists only on origin."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        work_dir = env.erk_root / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-remote"]},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-remote", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Expected success, got: {result.stderr}"
        assert "exists on origin, creating local tracking branch" in result.stderr

        # Verify fetch and tracking branch creation
        assert ("origin", "feature-remote") in git_ops.fetched_branches
        assert ("feature-remote", "origin/feature-remote") in git_ops.created_tracking_branches


def test_checkout_fails_when_branch_not_on_origin() -> None:
    """Test checkout shows error when branch doesn't exist locally or on origin."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "nonexistent-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "does not exist" in result.stderr
        assert "erk wt create --branch nonexistent-branch" in result.stderr


def test_checkout_message_when_switching_worktrees() -> None:
    """Test that checkout shows 'Switched to worktree' when switching from different location."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir.parent,
            worktrees_dir=work_dir,
            pool_json_path=work_dir.parent / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None

        assert "Switched to worktree" in script_content
        assert "feature-wt" in script_content
        assert str(feature_wt) in script_content
        assert "Already" not in script_content
        assert len(git_ops.checked_out_branches) == 0


def test_checkout_tracks_untracked_branch_with_graphite() -> None:
    """Test that checkout tracks untracked branches with Graphite after confirmation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-untracked-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-untracked"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            repo=repo,
            use_graphite=True,
            confirm_responses=[True],
        )

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-untracked"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert len(graphite.track_branch_calls) == 1
        cwd, branch_name, parent_branch = graphite.track_branch_calls[0]
        assert cwd == env.cwd
        assert branch_name == "feature-untracked"
        assert parent_branch == "main"


def test_checkout_skips_tracking_when_user_declines() -> None:
    """Test that checkout skips tracking when user declines the confirmation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-untracked-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-untracked"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            repo=repo,
            use_graphite=True,
            confirm_responses=[False],
        )

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-untracked"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert len(graphite.track_branch_calls) == 0


def test_checkout_skips_tracking_in_script_mode() -> None:
    """Test that checkout skips tracking prompt in script mode."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-untracked-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-untracked"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo, use_graphite=True)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-untracked", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert len(graphite.track_branch_calls) == 0


def test_checkout_does_not_track_already_tracked_branch() -> None:
    """Test that checkout does not call track_branch for already tracked branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-tracked-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-tracked"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        graphite = FakeGraphite(
            branches={
                "feature-tracked": BranchMetadata(
                    name="feature-tracked",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                )
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "feature-tracked", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert len(graphite.track_branch_calls) == 0


def test_checkout_does_not_track_trunk_branch() -> None:
    """Test that checkout does not track the trunk branch with Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
            pool_json_path=work_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo, cwd=feature_wt)

        result = runner.invoke(
            cli, ["slot", "checkout", "main", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert len(graphite.track_branch_calls) == 0
