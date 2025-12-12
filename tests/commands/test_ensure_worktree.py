"""Tests for ensure_worktree_for_branch function.

Test Environment Selection Guide
---------------------------------

This test file demonstrates the decision criteria for choosing between
`erk_inmem_env` and `erk_isolated_fs_env`:

**Use erk_inmem_env (PREFERRED) when:**
- Testing business logic without filesystem I/O
- Verifying return values and mutation tracking
- Testing error paths and validation logic
- Checking git_ops mutation tracking (added_worktrees, created_tracking_branches)
- No actual files or directories need to be created

**Use erk_isolated_fs_env when:**
- Testing .env file creation (path.write_text operations)
- Testing post-create command execution (subprocess that creates files)
- Testing unique name generation with actual directory collisions
- Any operation that needs to perform real filesystem I/O

**Examples from this file:**

In-memory tests (erk_inmem_env):
- test_ensure_worktree_returns_existing_worktree: Only checks return values
- test_ensure_worktree_creates_worktree_for_local_branch: Only verifies git_ops tracking
- test_ensure_worktree_creates_tracking_branch_from_remote: Checks mutation tracking
- test_ensure_worktree_fails_for_nonexistent_branch: Tests error path
- test_ensure_worktree_handles_tracking_branch_failure: Tests exception handling
- test_ensure_worktree_returns_was_created_flag: Checks return values

Isolated filesystem tests (erk_isolated_fs_env):
- test_ensure_worktree_creates_env_file_from_config: Writes and reads .env file
- test_ensure_worktree_skips_env_when_no_template: Checks .env file contents
- test_ensure_worktree_runs_post_create_commands: Runs subprocess that creates files
- test_ensure_worktree_works_without_local_config: Creates .env file
- test_ensure_worktree_generates_unique_name_on_collision: Creates actual directory

**Key Principle:**
Default to erk_inmem_env for speed and isolation. Only use erk_isolated_fs_env when
the code under test performs actual filesystem I/O that cannot be faked.
"""

from click.testing import CliRunner

from erk.cli.commands.wt.create_cmd import ensure_worktree_for_branch
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_ensure_worktree_returns_existing_worktree() -> None:
    """Test that ensure_worktree_for_branch returns existing worktree path."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name
        feature_path = repo_dir / "feature-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_path, branch="feature-1"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-1"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch for already-checked-out branch
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-1")

        # Should return existing path and False
        assert path == feature_path
        assert was_created is False
        # No new worktrees should be created
        assert len(git_ops.added_worktrees) == 0


def test_ensure_worktree_creates_worktree_for_local_branch() -> None:
    """Test that ensure_worktree_for_branch creates worktree for local branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # feature-2 exists locally but is not checked out
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-2"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch for local branch without worktree
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-2")

        # Should create worktree and return True
        assert was_created is True
        # Name should contain branch name and date suffix (e.g., "feature-2-25-11-17")
        assert "feature-2" in path.name
        # Verify worktree was added via git_ops
        assert any(branch == "feature-2" for _path, branch in git_ops.added_worktrees)


def test_ensure_worktree_creates_tracking_branch_from_remote() -> None:
    """Test that ensure_worktree_for_branch creates tracking branch from remote."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # feature-3 exists on remote but not locally
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main"]},  # feature-3 NOT in local
            remote_branches={env.cwd: ["origin/main", "origin/feature-3"]},  # BUT on remote
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch for remote-only branch
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-3")

        # Should create tracking branch, then worktree
        assert was_created is True
        # Name should contain branch name and date suffix (e.g., "feature-3-25-11-17")
        assert "feature-3" in path.name

        # Verify tracking branch was created
        assert any(
            branch == "feature-3" and remote == "origin/feature-3"
            for branch, remote in git_ops.created_tracking_branches
        )

        # Verify worktree was created
        assert any(branch == "feature-3" for _path, branch in git_ops.added_worktrees)


def test_ensure_worktree_fails_for_nonexistent_branch() -> None:
    """Test that ensure_worktree_for_branch fails when branch doesn't exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # nonexistent-branch doesn't exist locally or remotely
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch for nonexistent branch - should raise SystemExit
        try:
            ensure_worktree_for_branch(ctx, repo, "nonexistent-branch")
            raise AssertionError("Expected SystemExit to be raised")
        except SystemExit as e:
            assert e.code == 1

        # No worktrees should be created
        assert len(git_ops.added_worktrees) == 0
        # No tracking branches should be created
        assert len(git_ops.created_tracking_branches) == 0


def test_ensure_worktree_handles_tracking_branch_failure() -> None:
    """Test that ensure_worktree_for_branch handles tracking branch creation failure."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Configure git_ops to fail on create_tracking_branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-4"]},
            git_common_dirs={env.cwd: env.git_dir},
            tracking_branch_failures={"feature-4": "fatal: refusing to create branch"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch - should raise SystemExit
        try:
            ensure_worktree_for_branch(ctx, repo, "feature-4")
            raise AssertionError("Expected SystemExit to be raised")
        except SystemExit as e:
            assert e.code == 1

        # No worktrees should be created (tracking branch failed first)
        assert len(git_ops.added_worktrees) == 0


def test_ensure_worktree_creates_env_file_from_config() -> None:
    """Test that ensure_worktree_for_branch creates .env file from config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-5"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create config with env template
        local_config = LoadedConfig(
            env={"MY_VAR": "test_value_{name}"},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Call ensure_worktree_for_branch
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-5")

        # Should create worktree
        assert was_created is True

        # Verify .env file was created
        env_file = path / ".env"
        assert env_file.exists()
        env_content = env_file.read_text(encoding="utf-8")

        # Check that template variables were substituted
        assert "MY_VAR=" in env_content
        assert "test_value_feature-5" in env_content
        # Check default variables
        assert "WORKTREE_PATH=" in env_content
        assert "WORKTREE_NAME=" in env_content
        assert "REPO_ROOT=" in env_content


def test_ensure_worktree_skips_env_when_no_template() -> None:
    """Test that ensure_worktree_for_branch skips .env creation when no template."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-6"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create config WITHOUT env template
        local_config = LoadedConfig(
            env={},  # Empty env dict
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Call ensure_worktree_for_branch
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-6")

        # Should create worktree
        assert was_created is True

        # Verify .env file was still created with default variables only
        env_file = path / ".env"
        assert env_file.exists()
        env_content = env_file.read_text(encoding="utf-8")

        # Should only have default variables
        assert "WORKTREE_PATH=" in env_content
        assert "WORKTREE_NAME=" in env_content
        assert "REPO_ROOT=" in env_content


def test_ensure_worktree_runs_post_create_commands() -> None:
    """Test that ensure_worktree_for_branch runs post-create commands."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-7"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create config with post-create commands
        local_config = LoadedConfig(
            env={},
            post_create_commands=["echo 'Hello World'", "touch test.txt"],
            post_create_shell="bash",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Call ensure_worktree_for_branch
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-7")

        # Should create worktree
        assert was_created is True

        # Verify test.txt was created by post-create command
        test_file = path / "test.txt"
        assert test_file.exists()


def test_ensure_worktree_works_without_local_config() -> None:
    """Test that ensure_worktree_for_branch works when local_config is None."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-8"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        # Build context with local_config=None
        ctx = env.build_context(git=git_ops, repo=repo, local_config=None)

        # Call ensure_worktree_for_branch with no config
        path, was_created = ensure_worktree_for_branch(ctx, repo, "feature-8")

        # Should still create worktree successfully
        assert was_created is True

        # Should create .env with default variables only
        env_file = path / ".env"
        assert env_file.exists()
        env_content = env_file.read_text(encoding="utf-8")
        assert "WORKTREE_PATH=" in env_content


def test_ensure_worktree_generates_unique_name_on_collision() -> None:
    """Test that ensure_worktree_for_branch errors on name collision with different branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        # Create existing worktree with name "feature-name"
        existing_path = repo_dir / "feature-name"
        existing_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=existing_path, branch="other-branch"),
                ]
            },
            local_branches={env.cwd: ["main", "feature-name", "other-branch"]},
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={env.cwd, existing_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch for branch that would collide
        # Should error because name exists with different branch
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            ensure_worktree_for_branch(ctx, repo, "feature-name", is_plan_derived=False)

        # Should exit with error code
        assert exc_info.value.code == 1


def test_ensure_worktree_returns_was_created_flag() -> None:
    """Test that ensure_worktree_for_branch correctly returns was_created flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name
        feature_path = repo_dir / "existing-feature"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_path, branch="existing-feature"),
                ]
            },
            local_branches={env.cwd: ["main", "existing-feature", "new-feature"]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Test existing worktree - should return was_created=False
        _path1, was_created1 = ensure_worktree_for_branch(ctx, repo, "existing-feature")
        assert was_created1 is False

        # Test new worktree - should return was_created=True
        _path2, was_created2 = ensure_worktree_for_branch(ctx, repo, "new-feature")
        assert was_created2 is True


def test_ensure_worktree_detached_head_error_message() -> None:
    """Test that ensure_worktree_for_branch shows clear error for detached HEAD worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name
        detached_path = repo_dir / "feature-branch"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=detached_path, branch=None),  # Detached HEAD
                ]
            },
            local_branches={env.cwd: ["main", "feature-branch"]},
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={env.cwd, detached_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        ctx = env.build_context(git=git_ops, repo=repo)

        # Call ensure_worktree_for_branch for branch with same name as detached HEAD worktree
        # Should raise SystemExit with helpful error message
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            ensure_worktree_for_branch(ctx, repo, "feature-branch", is_plan_derived=False)

        # Should exit with error code
        assert exc_info.value.code == 1
        # No worktrees should be created
        assert len(git_ops.added_worktrees) == 0
