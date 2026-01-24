"""Unit tests for branch create command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans

# Fixed timestamp for test Plan objects - deterministic test data
TEST_PLAN_TIMESTAMP = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)


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
        assert "Assigned feature-test to erk-slot-01" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"
        assert state.assignments[0].slot_name == "erk-slot-01"


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
        assert "Assigned feature-test to erk-slot-01" in result.output


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

        # Verify branch was created (tuple is cwd, branch_name, start_point, force)
        assert (env.cwd, "feature-test", "main", False) in git_ops.created_branches

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
        assert "Assigned feature-b to erk-slot-02" in result2.output

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
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
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
                    slot_name="erk-slot-01",
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

        # Verify: checkout_branch was called in the slot worktree (reusing existing worktree)
        # Note: There may be additional checkouts from create_branch (for Graphite tracking),
        # but the key assertion is that the SLOT worktree received a checkout, not add_worktree
        slot_checkouts = [
            (path, branch) for path, branch in git_ops.checked_out_branches if path == worktree_path
        ]
        assert len(slot_checkouts) == 1
        checkout_path, checkout_branch = slot_checkouts[0]
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
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_branch_create_for_plan_creates_branch_and_impl_folder(tmp_path) -> None:
    """Test that --for-plan creates branch, slot, and .impl/ folder."""
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

        # Create a plan with erk-plan label
        now = TEST_PLAN_TIMESTAMP
        plan = Plan(
            plan_identifier="123",
            title="Add feature",
            body="# Plan\nImplementation details",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/123",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"123": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(
            cli, ["br", "create", "--for-plan", "123"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Branch name is derived from issue number and title
        assert "Created branch:" in result.output
        assert "P123" in result.output  # Branch should contain P123
        assert "Assigned" in result.output
        assert "erk-slot-01" in result.output
        assert "Created .impl/ folder from issue #123" in result.output
        assert "source" in result.output  # Activation script path
        # Default mode is "implement", so we expect the implement instructions
        assert "To activate and start implementation:" in result.output
        assert "erk implement" in result.output

        # Verify .impl/ folder was created in the worktree
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        impl_folder = worktree_path / ".impl"
        assert impl_folder.exists()
        assert (impl_folder / "plan.md").exists()
        assert (impl_folder / "issue.json").exists()

        # Verify activation script was created
        activate_script = worktree_path / ".erk" / "bin" / "activate.sh"
        assert activate_script.exists()
        assert str(activate_script) in result.output


def test_branch_create_for_plan_with_issue_url(tmp_path) -> None:
    """Test that --for-plan accepts GitHub issue URLs."""
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

        now = TEST_PLAN_TIMESTAMP
        plan = Plan(
            plan_identifier="456",
            title="Fix bug",
            body="# Bug fix plan",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/456",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"456": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(
            cli,
            ["br", "create", "--for-plan", "https://github.com/owner/repo/issues/456"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "P456" in result.output
        assert "Created .impl/ folder from issue #456" in result.output


def test_branch_create_for_plan_fails_without_erk_plan_label() -> None:
    """Test that --for-plan fails if issue doesn't have erk-plan label."""
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

        now = TEST_PLAN_TIMESTAMP
        # Plan WITHOUT erk-plan label
        plan = Plan(
            plan_identifier="789",
            title="Missing label",
            body="# Plan content",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/789",
            labels=["bug"],  # No erk-plan label
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"789": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(
            cli, ["br", "create", "--for-plan", "789"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "erk-plan" in result.output
        assert "must have" in result.output.lower() or "Error" in result.output


def test_branch_create_for_plan_with_no_slot_skips_impl() -> None:
    """Test that --for-plan with --no-slot creates branch but not .impl folder."""
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

        now = TEST_PLAN_TIMESTAMP
        plan = Plan(
            plan_identifier="100",
            title="No slot feature",
            body="# Plan",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/100",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"100": plan})

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, plan_store=plan_store
        )

        result = runner.invoke(
            cli,
            ["br", "create", "--for-plan", "100", "--no-slot"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Created branch:" in result.output
        assert "P100" in result.output
        # Should NOT have slot assignment or .impl folder messages
        assert "Assigned" not in result.output
        assert ".impl folder not created" in result.output or "Note:" in result.output


def test_branch_create_fails_with_both_branch_and_for_plan() -> None:
    """Test that specifying both BRANCH and --for-plan fails."""
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

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        result = runner.invoke(
            cli,
            ["br", "create", "my-branch", "--for-plan", "123"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "Cannot specify both BRANCH and --for-plan" in result.output


def test_branch_create_fails_without_branch_or_for_plan() -> None:
    """Test that omitting both BRANCH and --for-plan fails."""
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

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        result = runner.invoke(cli, ["br", "create"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Must provide BRANCH argument or --for-plan option" in result.output


def test_branch_create_stacks_on_current_branch() -> None:
    """Test that branch create stacks on current branch when not on trunk."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Current branch is feature-parent, not trunk
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "feature-parent"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-parent"]},
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
            cli, ["br", "create", "feature-child"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch: feature-child" in result.output

        # Verify branch was created from feature-parent, not main
        # (tuple is cwd, branch_name, start_point, force)
        assert (env.cwd, "feature-child", "feature-parent", False) in git_ops.created_branches

        # Verify Graphite tracking was called with feature-parent as parent
        assert len(graphite_ops.track_branch_calls) == 1
        cwd, branch, parent = graphite_ops.track_branch_calls[0]
        assert branch == "feature-child"
        assert parent == "feature-parent"


def test_branch_create_for_plan_stacks_on_current_branch() -> None:
    """Test that --for-plan stacks on current branch when not on trunk."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Current branch is feature-parent, not trunk
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "feature-parent"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-parent"]},
        )
        graphite_ops = FakeGraphite()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        now = TEST_PLAN_TIMESTAMP
        plan = Plan(
            plan_identifier="200",
            title="Stacked feature",
            body="# Plan\nStacked implementation",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/200",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
            objective_id=None,
        )
        plan_store, _ = create_plan_store_with_plans({"200": plan})

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, plan_store=plan_store
        )

        result = runner.invoke(
            cli, ["br", "create", "--for-plan", "200"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "P200" in result.output

        # Verify Graphite tracking was called with feature-parent as parent
        assert len(graphite_ops.track_branch_calls) == 1
        cwd, branch, parent = graphite_ops.track_branch_calls[0]
        assert "P200" in branch
        assert parent == "feature-parent"


def test_branch_create_uses_trunk_when_on_trunk() -> None:
    """Test that branch create uses trunk when current branch is trunk."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Current branch is main (trunk)
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
            cli, ["br", "create", "new-feature"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify branch was created from main (trunk)
        # (tuple is cwd, branch_name, start_point, force)
        assert (env.cwd, "new-feature", "main", False) in git_ops.created_branches

        # Verify Graphite tracking was called with main as parent
        assert len(graphite_ops.track_branch_calls) == 1
        cwd, branch, parent = graphite_ops.track_branch_calls[0]
        assert branch == "new-feature"
        assert parent == "main"
