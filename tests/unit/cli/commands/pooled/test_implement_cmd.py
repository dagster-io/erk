"""Unit tests for pooled implement command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def _make_plan(number: int, title: str, body: str) -> Plan:
    """Create a Plan for testing."""
    now = datetime.now(UTC)
    return Plan(
        plan_identifier=str(number),
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={"number": number},
    )


def test_pooled_implement_rejects_file_path() -> None:
    """Test that pooled implement rejects file paths (issue-only)."""
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

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "implement", "./plan.md"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "only supports GitHub issues" in result.output


def test_pooled_implement_dry_run_shows_plan(tmp_path: Path) -> None:
    """Test that pooled implement --dry-run shows plan without executing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create plan store with test plan
        plan = _make_plan(
            number=123,
            title="P4008-test-feature",
            body="# Test Plan\n\nImplement test feature.",
        )
        plan_store, _ = create_plan_store_with_plans({"123": plan})

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

        test_ctx = env.build_context(git=git_ops, repo=repo, plan_store=plan_store)

        result = runner.invoke(
            cli,
            ["pooled", "implement", "123", "--dry-run"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would assign branch" in result.output
        assert "P4008-test-feature" in result.output


def test_pooled_implement_assigns_to_available_slot() -> None:
    """Test that pooled implement assigns issue branch to available slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create plan store with test plan
        plan = _make_plan(
            number=456,
            title="P1234-add-feature",
            body="# Add Feature\n\nStep 1: Do something.",
        )
        plan_store, _ = create_plan_store_with_plans({"456": plan})

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

        # Pre-create the worktree directory since git.add_worktree would create it
        slot_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        slot_path.mkdir(parents=True)

        test_ctx = env.build_context(git=git_ops, repo=repo, plan_store=plan_store)

        result = runner.invoke(
            cli,
            ["pooled", "implement", "456", "--dry-run"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "P1234-add-feature" in result.output


def test_pooled_implement_dry_run_shows_branch_assignment() -> None:
    """Test that pooled implement --dry-run shows branch to be assigned."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create plan store with test plan
        plan = _make_plan(
            number=789,
            title="P9999-new-feature",
            body="# New Feature\n\nNew plan.",
        )
        plan_store, _ = create_plan_store_with_plans({"789": plan})

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

        test_ctx = env.build_context(git=git_ops, repo=repo, plan_store=plan_store)

        result = runner.invoke(
            cli,
            ["pooled", "implement", "789", "--dry-run"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Should show branch would be assigned
        assert "Would assign branch" in result.output
        assert "P9999-new-feature" in result.output


def test_pooled_implement_force_unassigns_oldest_in_script_mode() -> None:
    """Test that --force auto-unassigns oldest branch when pool is full (script mode)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create plan store with test plan
        plan = _make_plan(
            number=100,
            title="P0100-new-feature",
            body="# New Feature\n\nNew plan.",
        )
        plan_store, _ = create_plan_store_with_plans({"100": plan})

        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees including the pool slot worktree
        worktrees = env.build_worktrees("main")
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
        full_state = PoolState(
            version="1.0",
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
            git=git_ops, repo=repo, plan_store=plan_store, local_config=local_config
        )

        # Use --script mode to avoid actual Claude execution
        # --script outputs shell commands and completes successfully
        result = runner.invoke(
            cli,
            ["pooled", "implement", "100", "--force", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Should show unassignment message
        assert "Unassigned" in result.output
        assert "old-branch" in result.output

        # Verify pool state was updated
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        # Branch name is derived from plan title with transformations
        assert "p0100-new-feature" in state.assignments[0].branch_name.lower()


def test_pooled_implement_pool_full_non_tty_fails() -> None:
    """Test that pool-full without --force fails in non-TTY mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create plan store with test plan
        plan = _make_plan(
            number=200,
            title="P0200-another-feature",
            body="# Another Feature\n\nAnother plan.",
        )
        plan_store, _ = create_plan_store_with_plans({"200": plan})

        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="blocking-branch"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "blocking-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "blocking-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a full pool with 1 slot
        full_state = PoolState(
            version="1.0",
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="blocking-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(
            git=git_ops, repo=repo, plan_store=plan_store, local_config=local_config
        )

        # No --force, no --dry-run, pool is full
        # CliRunner simulates non-TTY mode
        result = runner.invoke(
            cli,
            ["pooled", "implement", "200"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "Pool is full" in result.output
        assert "--force" in result.output


def test_pooled_implement_validates_submit_requires_no_interactive() -> None:
    """Test that --submit requires --no-interactive."""
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

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["pooled", "implement", "123", "--submit"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "--submit requires --no-interactive" in result.output


def test_pooled_implement_yolo_enables_flags() -> None:
    """Test that --yolo enables dangerous, submit, and no-interactive."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create plan store with test plan
        plan = _make_plan(
            number=999,
            title="P0999-yolo-feature",
            body="# YOLO Feature\n\nGo fast.",
        )
        plan_store, _ = create_plan_store_with_plans({"999": plan})

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

        test_ctx = env.build_context(git=git_ops, repo=repo, plan_store=plan_store)

        # --yolo with --dry-run should work (yolo sets submit + no-interactive)
        result = runner.invoke(
            cli,
            ["pooled", "implement", "999", "--yolo", "--dry-run"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Should show command sequence including CI and submit
        assert "/erk:plan-implement" in result.output
        assert "/fast-ci" in result.output
        assert "/gt:pr-submit" in result.output
