"""Tests for erk checkout command."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
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
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["checkout", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
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
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout a branch that doesn't exist
        result = runner.invoke(
            cli, ["checkout", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "does not exist" in result.stderr
        assert "erk wt create --branch nonexistent-branch" in result.stderr


def test_checkout_creates_worktree_for_unchecked_branch() -> None:
    """Test that checkout auto-creates worktree when branch exists but is not checked out."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
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
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout branch that exists but is not checked out
        result = runner.invoke(
            cli, ["checkout", "existing-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed and create worktree
        assert result.exit_code == 0
        assert "creating worktree" in result.stderr
        assert "✓ Created worktree" in result.stderr

        # Verify worktree was created
        assert len(git_ops.added_worktrees) == 1
        added_wt_path, added_wt_branch = git_ops.added_worktrees[0]
        assert added_wt_branch == "existing-branch"

        # Should generate activation script (output path to stdout)
        assert result.stdout.strip() != ""
        script_path = Path(result.stdout.strip())
        assert script_path.exists()

        # Verify "Switched to new worktree" message in activation script
        script_content = script_path.read_text(encoding="utf-8")
        assert "Switched to new worktree" in script_content
        assert "existing-branch" in script_content


def test_checkout_to_branch_in_stack_but_not_checked_out() -> None:
    """Test that checkout auto-creates worktree when branch exists in repo but is not checked out.

    With auto-creation behavior, branches that exist in Graphite stacks but are not
    directly checked out will have a worktree created automatically.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        wt1 = work_dir / "feature-1-wt"

        # feature-1 is checked out, but feature-base is not
        # (even though it exists in git)
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-1", "feature-base"]},  # feature-base exists
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-base which exists in repo but is not checked out
        result = runner.invoke(
            cli, ["checkout", "feature-base", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed and create worktree
        assert result.exit_code == 0
        assert "creating worktree" in result.stderr

        # Verify worktree was created
        assert len(git_ops.added_worktrees) == 1


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
        )

        # Graphite is NOT enabled - checkout should still work
        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["checkout", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
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
        )

        # CRITICAL: Set cwd to feature_wt to simulate already being in target location
        test_ctx = env.build_context(git=git_ops, repo=repo, cwd=feature_wt)

        # Checkout feature-1 while already in feature_wt
        result = runner.invoke(
            cli, ["checkout", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
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
        # Message format: "Already on branch {branch} in worktree {name}"
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
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["checkout", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should not checkout (already on feature-2)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_checkout_with_multiple_worktrees_same_branch() -> None:
    """Test error when multiple worktrees have the same branch checked out.

    This is an edge case that shouldn't happen in normal use (git prevents it),
    but our code should handle it gracefully.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        wt1 = work_dir / "wt1"
        wt2 = work_dir / "wt2"

        # Edge case: same branch checked out in multiple worktrees
        # (shouldn't happen in real git, but test our handling)
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

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-2 which is checked out in multiple worktrees
        result = runner.invoke(
            cli, ["checkout", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should show error about multiple worktrees
        assert result.exit_code == 1
        assert "exists in multiple worktrees" in result.stderr


def test_checkout_creates_worktree_for_remote_only_branch() -> None:
    """Test checkout auto-creates worktree when branch exists only on origin."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        # Branch exists on origin but not locally
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},  # feature-remote NOT here
            remote_branches={env.cwd: ["origin/main", "origin/feature-remote"]},  # But here
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout remote branch
        result = runner.invoke(
            cli, ["checkout", "feature-remote", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed with worktree creation
        assert result.exit_code == 0, f"Expected success, got: {result.stderr}"
        assert "exists on origin, creating local tracking branch" in result.stderr
        assert "creating worktree" in result.stderr
        assert "✓ Created worktree" in result.stderr

        # Verify worktree was created
        assert len(git_ops.added_worktrees) == 1
        added_wt_path, added_wt_branch = git_ops.added_worktrees[0]
        assert added_wt_branch == "feature-remote"

        # Should generate activation script (output path to stdout)
        assert result.stdout.strip() != ""
        script_path = Path(result.stdout.strip())
        assert script_path.exists()

        # Verify "Switched to new worktree" message in activation script
        script_content = script_path.read_text(encoding="utf-8")
        assert "Switched to new worktree" in script_content
        assert "feature-remote" in script_content


def test_checkout_fails_when_branch_not_on_origin() -> None:
    """Test checkout shows error when branch doesn't exist locally or on origin."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        # Branch doesn't exist locally or remotely
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},  # nonexistent-branch NOT here
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout nonexistent branch
        result = runner.invoke(
            cli,
            ["checkout", "nonexistent-branch", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Should fail with error message
        assert result.exit_code == 1
        assert "does not exist" in result.stderr
        assert "erk wt create --branch nonexistent-branch" in result.stderr


def test_checkout_message_when_switching_worktrees() -> None:
    """Test that checkout shows 'Switched to worktree' when switching from different location.

    This validates that message logic checks location change, not whether git checkout is needed.
    Regression test for bug where 'Already on branch X' was shown when switching worktrees even
    when the branch was already checked out in the target worktree.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        # Set up two worktrees: root on main, secondary on feature-branch
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    # Branch already checked out in target worktree
                    WorktreeInfo(path=feature_wt, branch="feature-branch"),
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
            repo_dir=work_dir.parent,
            worktrees_dir=work_dir,
        )

        # Build context with cwd=env.cwd (root worktree)
        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Checkout feature-branch from root worktree
        result = runner.invoke(
            cli, ["checkout", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        assert result.exit_code == 0

        # Verify activation script was generated
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None

        # CRITICAL: Message should say "Switched to worktree"
        # NOT "Already on branch" or "Already in worktree"
        # Because user is switching from env.cwd to feature_wt
        # Message format: "Switched to worktree {name}" (when name matches branch)
        assert "Switched to worktree" in script_content
        assert "feature-wt" in script_content
        assert str(feature_wt) in script_content

        # Should NOT contain "Already" since we're switching locations
        assert "Already" not in script_content

        # Should not checkout (branch already checked out in target worktree)
        assert len(git_ops.checked_out_branches) == 0


def test_checkout_trunk_with_dirty_root_errors() -> None:
    """Test that checkout prevents creating worktree for trunk branch when root is dirty.

    When the root worktree is dirty, try_switch_root_worktree() fails and the command
    falls through to ensure_worktree_for_branch(). This test verifies that the trunk
    validation in ensure_worktree_for_branch() catches this and errors appropriately.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name

        # Setup: root worktree is on a feature branch, not trunk
        # This way when user tries to checkout trunk, it won't already be checked out
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-1"]},
            default_branches={env.cwd: "main"},
            # Simulate dirty root - uncommitted changes present
            file_statuses={env.cwd: ([], ["modified_file.txt"], [])},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Try to checkout trunk branch (main) - should error
        result = runner.invoke(cli, ["checkout", "main"], obj=test_ctx, catch_exceptions=False)

        # Should fail with error
        assert result.exit_code == 1

        # Error message should indicate trunk branch cannot have worktree
        assert "Cannot create worktree for trunk branch" in result.stderr
        assert "main" in result.stderr
        assert "erk checkout root" in result.stderr
        assert "root worktree" in result.stderr


def test_checkout_tracks_untracked_branch_with_graphite() -> None:
    """Test that checkout tracks untracked branches with Graphite after confirmation.

    When checking out a branch that is not tracked by Graphite, checkout
    prompts the user. If confirmed, it calls track_branch() with trunk as parent.
    """
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

        # Graphite has no branches tracked (empty dict)
        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo)

        # Checkout the untracked branch (non-script mode, confirm with 'y')
        result = runner.invoke(
            cli,
            ["checkout", "feature-untracked"],
            obj=test_ctx,
            input="y\n",
            catch_exceptions=False,
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        assert result.exit_code == 0

        # Verify track_branch was called with trunk as parent
        assert len(graphite.track_branch_calls) == 1
        cwd, branch_name, parent_branch = graphite.track_branch_calls[0]
        assert cwd == feature_wt
        assert branch_name == "feature-untracked"
        assert parent_branch == "main"


def test_checkout_skips_tracking_when_user_declines() -> None:
    """Test that checkout skips tracking when user declines the confirmation.

    When the user responds 'n' to the tracking confirmation, track_branch()
    should not be called.
    """
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

        # Graphite has no branches tracked (empty dict)
        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo)

        # Checkout the untracked branch (non-script mode, decline with 'n')
        result = runner.invoke(
            cli,
            ["checkout", "feature-untracked"],
            obj=test_ctx,
            input="n\n",
            catch_exceptions=False,
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        assert result.exit_code == 0

        # Verify track_branch was NOT called (user declined)
        assert len(graphite.track_branch_calls) == 0


def test_checkout_skips_tracking_in_script_mode() -> None:
    """Test that checkout skips tracking prompt in script mode.

    Script mode cannot prompt interactively, so tracking should be skipped
    entirely when --script is used.
    """
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

        # Graphite has no branches tracked (empty dict)
        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo)

        # Checkout with --script flag (no interactive prompt)
        result = runner.invoke(
            cli, ["checkout", "feature-untracked", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        assert result.exit_code == 0

        # Verify track_branch was NOT called (script mode skips tracking)
        assert len(graphite.track_branch_calls) == 0


def test_checkout_does_not_track_already_tracked_branch() -> None:
    """Test that checkout does not call track_branch for already tracked branches.

    When a branch is already tracked by Graphite, checkout should not
    call track_branch() again (idempotent behavior).
    """
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

        # Graphite already has the branch tracked
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
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo)

        # Checkout the already tracked branch
        result = runner.invoke(
            cli, ["checkout", "feature-tracked", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        assert result.exit_code == 0

        # Verify track_branch was NOT called (already tracked)
        assert len(graphite.track_branch_calls) == 0


def test_checkout_does_not_track_trunk_branch() -> None:
    """Test that checkout does not track the trunk branch with Graphite.

    Trunk branches (main/master) are always implicitly tracked by Graphite,
    so checkout should never call track_branch() for them.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        # Setup: We're on feature branch, checking out main
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

        # Graphite has no branches tracked (empty dict)
        graphite = FakeGraphite(branches={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )

        # Set cwd to feature_wt to simulate being in that worktree
        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo, cwd=feature_wt)

        # Checkout trunk (main) from feature worktree
        result = runner.invoke(
            cli, ["checkout", "main", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        assert result.exit_code == 0

        # Verify track_branch was NOT called for trunk branch
        assert len(graphite.track_branch_calls) == 0
