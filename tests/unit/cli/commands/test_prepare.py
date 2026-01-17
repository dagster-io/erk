"""Unit tests for prepare command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans, make_test_plan


def test_prepare_creates_branch_and_impl_folder() -> None:
    """Test that erk prepare creates branch, slot, and .impl/ folder."""
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
        plan = make_test_plan(
            123,
            title="Add feature",
            body="# Plan\nImplementation details",
            url="https://github.com/owner/repo/issues/123",
        )
        plan_store, _ = create_plan_store_with_plans({"123": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(cli, ["prepare", "123"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Branch name is derived from issue number and title
        assert "Created branch:" in result.output
        assert "P123" in result.output  # Branch should contain P123
        assert "Assigned" in result.output
        assert "erk-slot-01" in result.output
        assert "Created .impl/ folder from issue #123" in result.output
        assert "source" in result.output  # Activation script path

        # Verify .impl/ folder was created in the worktree
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        impl_folder = worktree_path / ".impl"
        assert impl_folder.exists()
        assert (impl_folder / "plan.md").exists()
        assert (impl_folder / "issue.json").exists()


def test_prepare_with_issue_url() -> None:
    """Test that erk prepare accepts GitHub issue URLs."""
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

        plan = make_test_plan(
            456,
            title="Fix bug",
            body="# Bug fix plan",
            url="https://github.com/owner/repo/issues/456",
        )
        plan_store, _ = create_plan_store_with_plans({"456": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(
            cli,
            ["prepare", "https://github.com/owner/repo/issues/456"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "P456" in result.output
        assert "Created .impl/ folder from issue #456" in result.output


def test_prepare_with_no_slot_flag() -> None:
    """Test that erk prepare --no-slot creates branch but not .impl folder."""
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

        plan = make_test_plan(
            100,
            title="No slot feature",
            body="# Plan",
            url="https://github.com/owner/repo/issues/100",
        )
        plan_store, _ = create_plan_store_with_plans({"100": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(
            cli,
            ["prepare", "--no-slot", "100"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Created branch:" in result.output
        assert "P100" in result.output
        # Should NOT have slot assignment or .impl folder messages
        assert "Assigned" not in result.output
        assert ".impl folder not created" in result.output or "Note:" in result.output


def test_prepare_with_force_flag() -> None:
    """Test that erk prepare --force reuses slot when pool is full."""
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
            local_branches={env.cwd: ["main", "old-branch"]},
        )

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

        plan = make_test_plan(
            200,
            title="Force feature",
            body="# Plan",
            url="https://github.com/owner/repo/issues/200",
        )
        plan_store, _ = create_plan_store_with_plans({"200": plan})

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            use_graphite=True,
            plan_store=plan_store,
            local_config=local_config,
        )

        # Create with --force (should reuse the slot)
        result = runner.invoke(
            cli, ["prepare", "--force", "200"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch:" in result.output
        assert "P200" in result.output
        assert "Unassigned" in result.output
        assert "old-branch" in result.output

        # Verify new state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_prepare_fails_without_erk_plan_label() -> None:
    """Test that erk prepare fails if issue doesn't have erk-plan label."""
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

        # Plan WITHOUT erk-plan label
        plan = make_test_plan(
            789,
            title="Missing label",
            body="# Plan content",
            url="https://github.com/owner/repo/issues/789",
            labels=["bug"],  # No erk-plan label
        )
        plan_store, _ = create_plan_store_with_plans({"789": plan})

        test_ctx = env.build_context(
            git=git_ops, repo=repo, use_graphite=True, plan_store=plan_store
        )

        result = runner.invoke(cli, ["prepare", "789"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "erk-plan" in result.output
        assert "must have" in result.output.lower() or "Error" in result.output


def test_prepare_behaves_same_as_br_create_for_plan() -> None:
    """Test that erk prepare X produces same result as erk br create --for-plan X."""
    runner = CliRunner()

    # Test with prepare command
    with erk_isolated_fs_env(runner) as env1:
        repo_dir1 = env1.setup_repo_structure()

        git_ops1 = FakeGit(
            worktrees=env1.build_worktrees("main"),
            current_branches={env1.cwd: "main"},
            git_common_dirs={env1.cwd: env1.git_dir},
            default_branches={env1.cwd: "main"},
        )

        repo1 = RepoContext(
            root=env1.cwd,
            repo_name=env1.cwd.name,
            repo_dir=repo_dir1,
            worktrees_dir=repo_dir1 / "worktrees",
            pool_json_path=repo_dir1 / "pool.json",
        )

        plan1 = make_test_plan(
            300,
            title="Test feature",
            body="# Plan",
            url="https://github.com/owner/repo/issues/300",
        )
        plan_store1, _ = create_plan_store_with_plans({"300": plan1})

        test_ctx1 = env1.build_context(
            git=git_ops1, repo=repo1, use_graphite=True, plan_store=plan_store1
        )

        result1 = runner.invoke(cli, ["prepare", "300"], obj=test_ctx1, catch_exceptions=False)

    # Test with br create --for-plan
    with erk_isolated_fs_env(runner) as env2:
        repo_dir2 = env2.setup_repo_structure()

        git_ops2 = FakeGit(
            worktrees=env2.build_worktrees("main"),
            current_branches={env2.cwd: "main"},
            git_common_dirs={env2.cwd: env2.git_dir},
            default_branches={env2.cwd: "main"},
        )

        repo2 = RepoContext(
            root=env2.cwd,
            repo_name=env2.cwd.name,
            repo_dir=repo_dir2,
            worktrees_dir=repo_dir2 / "worktrees",
            pool_json_path=repo_dir2 / "pool.json",
        )

        plan2 = make_test_plan(
            300,
            title="Test feature",
            body="# Plan",
            url="https://github.com/owner/repo/issues/300",
        )
        plan_store2, _ = create_plan_store_with_plans({"300": plan2})

        test_ctx2 = env2.build_context(
            git=git_ops2, repo=repo2, use_graphite=True, plan_store=plan_store2
        )

        result2 = runner.invoke(
            cli, ["br", "create", "--for-plan", "300"], obj=test_ctx2, catch_exceptions=False
        )

    # Both should succeed
    assert result1.exit_code == 0
    assert result2.exit_code == 0

    # Both should have the same key output messages
    assert "Created branch:" in result1.output
    assert "Created branch:" in result2.output
    assert "P300" in result1.output
    assert "P300" in result2.output
    assert "Created .impl/ folder from issue #300" in result1.output
    assert "Created .impl/ folder from issue #300" in result2.output
