"""Unit tests for branch create command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_branch_create_creates_new_branch_and_assignment(tmp_path) -> None:
    """Test that branch create creates a new branch and assignment."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # use_graphite=True because branch create calls graphite.track_branch
        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        result = runner.invoke(
            cli, ["branch", "create", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch: feature-test" in result.output
        assert "Assigned feature-test to erk-managed-wt-01" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"
        assert state.assignments[0].slot_name == "erk-managed-wt-01"


def test_branch_create_with_br_alias(tmp_path) -> None:
    """Test that 'erk br create' alias works."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # use_graphite=True because branch create calls graphite.track_branch
        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        result = runner.invoke(
            cli, ["br", "create", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch: feature-test" in result.output
        assert "Assigned feature-test to erk-managed-wt-01" in result.output


def test_branch_create_no_slot_only_creates_branch() -> None:
    """Test that --no-slot creates branch without slot assignment."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )
        graphite_ops = FakeGraphite()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, repo=repo)

        result = runner.invoke(
            cli, ["br", "create", "--no-slot", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch: feature-test" in result.output
        # Should NOT have slot assignment message
        assert "Assigned" not in result.output

        # Verify NO pool state was created
        state = load_pool_state(repo.pool_json_path)
        assert state is None

        # Verify branch was created
        assert (env.cwd, "feature-test", "main") in git_ops.created_branches

        # Verify Graphite tracking was called
        assert len(graphite_ops.track_branch_calls) == 1


def test_branch_create_second_slot() -> None:
    """Test that branch create uses next available slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # use_graphite=True because branch create calls graphite.track_branch
        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        # First create
        result1 = runner.invoke(
            cli, ["br", "create", "feature-a"], obj=test_ctx, catch_exceptions=False
        )
        assert result1.exit_code == 0

        # Second create
        result2 = runner.invoke(
            cli, ["br", "create", "feature-b"], obj=test_ctx, catch_exceptions=False
        )
        assert result2.exit_code == 0
        assert "Assigned feature-b to erk-managed-wt-02" in result2.output

        # Verify state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2


def test_branch_create_fails_if_branch_already_exists() -> None:
    """Test that branch create fails if branch already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a FakeGit that reports the branch already exists
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Try to create a branch that already exists
        result = runner.invoke(
            cli, ["br", "create", "existing-branch"], obj=test_ctx, catch_exceptions=False
        )
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "erk br assign" in result.output


def test_branch_create_tracks_branch_with_graphite() -> None:
    """Test that branch create registers the branch with Graphite."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )
        graphite_ops = FakeGraphite()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, repo=repo)

        result = runner.invoke(
            cli, ["br", "create", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Verify Graphite tracking was called
        assert len(graphite_ops.track_branch_calls) == 1
        cwd, branch, parent = graphite_ops.track_branch_calls[0]
        assert branch == "feature-test"
        assert parent == "main"


def test_branch_create_force_reuses_unassigned_slot_with_checkout() -> None:
    """Test that --force reuses an unassigned slot with checkout_branch, not add_worktree.

    Regression test for issue #4173: When pool is full and --force is used,
    the unassigned slot's worktree already exists. We must use checkout_branch
    (not add_worktree) to avoid 'fatal: already exists' error from git.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pre-create worktree directory so we can configure FakeGit with it
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees including the pool slot worktree
        worktrees = env.build_worktrees("main")
        # Add the pool slot worktree to the configuration
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            # old-branch exists, new-branch will be created
            local_branches={env.cwd: ["main", "old-branch"]},
        )
        graphite_ops = FakeGraphite()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a full pool with 1 slot
        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, local_config=local_config
        )

        # Create a new branch with --force (should reuse the slot)
        result = runner.invoke(
            cli, ["br", "create", "--force", "new-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch: new-branch" in result.output
        assert "Unassigned" in result.output
        assert "old-branch" in result.output
        assert "Assigned new-branch" in result.output

        # Verify: checkout_branch was called (reusing existing worktree)
        assert len(git_ops.checked_out_branches) == 1
        checkout_path, checkout_branch = git_ops.checked_out_branches[0]
        assert checkout_path == worktree_path
        assert checkout_branch == "new-branch"

        # Verify: add_worktree was NOT called for the slot reuse
        # (add_worktree was only called if creating a fresh slot)
        assert len(git_ops.added_worktrees) == 0

        # Verify new state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "new-branch"
        assert state.assignments[0].slot_name == "erk-managed-wt-01"
