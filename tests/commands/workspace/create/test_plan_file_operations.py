"""Tests for plan file handling in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.git.fake import FakeGit
from tests.commands.workspace.create.conftest import get_current_date_suffix
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_create_with_plan_file() -> None:
    """Test creating a worktree with a plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file)],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        # Should create worktree with "plan" stripped from filename and date suffix added
        date_suffix = get_current_date_suffix()
        wt_path = repo_dir / "worktrees" / f"my-feature-{date_suffix}"
        assert wt_path.exists()
        # Impl folder should be created with plan.md
        assert (wt_path / ".impl").exists()
        assert (wt_path / ".impl" / "plan.md").exists()
        assert not plan_file.exists()


def test_create_with_plan_file_removes_plan_word() -> None:
    """Test that --from-plan-file flag removes 'plan' from worktree names."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        test_cases = [
            ("devclikit-extraction-plan.md", "devclikit-extraction"),
            ("auth-plan.md", "auth"),
            ("plan-for-api.md", "for-api"),
            ("plan.md", "plan"),  # Edge case: only "plan" should be preserved
        ]

        for plan_filename, expected_worktree_base in test_cases:
            # Create plan file
            plan_file = env.cwd / plan_filename
            plan_file.write_text(f"# {plan_filename}\n", encoding="utf-8")

            result = runner.invoke(
                cli, ["wt", "create", "--from-plan-file", str(plan_file)], obj=test_ctx
            )

            assert result.exit_code == 0, f"Failed for {plan_filename}: {result.output}"

            # Compute date suffix after invoke to avoid timing issues at minute boundaries
            date_suffix = get_current_date_suffix()
            expected_worktree_name = f"{expected_worktree_base}-{date_suffix}"
            wt_path = repo_dir / "worktrees" / expected_worktree_name
            assert wt_path.exists(), f"Expected worktree at {wt_path} for {plan_filename}"
            assert (wt_path / ".impl" / "plan.md").exists()
            assert not plan_file.exists()

            # Clean up for next test
            import shutil

            shutil.rmtree(wt_path)


def test_create_plan_file_not_found() -> None:
    """Test that create fails when plan file doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", "nonexistent.md"],
            obj=test_ctx,
        )

        # Click should fail validation before reaching our code
        assert result.exit_code != 0


def test_create_with_keep_plan_file_flag() -> None:
    """Test that --keep-plan-file copies instead of moves the plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file), "--keep-plan-file"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        # Should create worktree with "plan" stripped from filename and date suffix added
        date_suffix = get_current_date_suffix()
        wt_path = repo_dir / "worktrees" / f"my-feature-{date_suffix}"
        assert wt_path.exists()
        # Impl folder should be created with plan.md
        assert (wt_path / ".impl" / "plan.md").exists()
        # Original plan file should still exist (copied, not moved)
        assert plan_file.exists()
        assert "Copied plan to" in result.output


def test_create_keep_plan_file_without_plan_file_fails() -> None:
    """Test that --keep-plan-file without --from-plan-file fails with error message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["wt", "create", "test-feature", "--keep-plan-file"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "--keep-plan-file requires --from-plan-file" in result.output


def test_create_with_plan_file_ensures_uniqueness() -> None:
    """Test that --from-plan-file ensures uniqueness with date suffix and versioning."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        # Create first worktree from plan
        result1 = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file)],
            obj=test_ctx,
        )
        assert result1.exit_code == 0, result1.output

        # Check that first worktree has date suffix
        # Compute date suffix after invoke to avoid timing issues at minute boundaries
        date_suffix1 = get_current_date_suffix()
        expected_name1 = f"my-feature-{date_suffix1}"
        wt_path1 = repo_dir / "worktrees" / expected_name1
        assert wt_path1.exists(), f"Expected first worktree at {wt_path1}"
        assert (wt_path1 / ".impl" / "plan.md").exists()

        # Recreate plan file for second worktree
        plan_file.write_text("# My Feature Plan - Round 2\n", encoding="utf-8")

        # Create second worktree from same plan (same day)
        result2 = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file)],
            obj=test_ctx,
        )
        assert result2.exit_code == 0, result2.output

        # Check that second worktree has -2 after date suffix (if same minute)
        # or just date suffix (if minute boundary crossed)
        date_suffix2 = get_current_date_suffix()
        if date_suffix1 == date_suffix2:
            # Same minute: uniqueness versioning adds -2
            expected_name2 = f"my-feature-{date_suffix2}-2"
        else:
            # Minute boundary crossed: different timestamp, no -2 needed
            expected_name2 = f"my-feature-{date_suffix2}"
        wt_path2 = repo_dir / "worktrees" / expected_name2
        assert wt_path2.exists(), f"Expected second worktree at {wt_path2}"
        assert (wt_path2 / ".impl" / "plan.md").exists()

        # Verify both worktrees exist
        assert wt_path1.exists()
        assert wt_path2.exists()


def test_create_with_long_plan_name_matches_branch_and_worktree() -> None:
    """Test that long plan names produce matching branch/worktree names.

    This test verifies the behavior with consistent 30-char truncation:
    - Worktree base name is truncated to 30 chars by sanitize_worktree_name()
    - Date suffix (-YY-MM-DD, 9 chars) is added to worktree name → 39 chars total
    - Branch name is truncated to 30 chars by sanitize_branch_component()
    - Branch name does NOT get date suffix → 30 chars max
    - Result: branch name matches the BASE of the worktree name (before date)
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file with very long name
        # The base will be truncated to 30 chars for both branch and worktree base
        # Branch: "fix-branch-worktree-name-misma" (30 chars, no date)
        # Worktree: "fix-branch-worktree-name-misma-YY-MM-DD" (39 chars with date)
        long_plan_name = "fix-branch-worktree-name-mismatch-in-erk-plan-workflow-plan.md"
        plan_file = env.cwd / long_plan_name
        plan_file.write_text("# Fix Branch Worktree Name Mismatch\n", encoding="utf-8")

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        # Create worktree from long plan filename
        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file)],
            obj=test_ctx,
        )
        assert result.exit_code == 0, result.output

        # Get the created worktree (should be only directory in worktrees_dir)
        worktrees_dir = repo_dir / "worktrees"
        worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir()]
        assert len(worktrees) == 1, f"Expected exactly 1 worktree, found {len(worktrees)}"

        actual_worktree_path = worktrees[0]
        actual_worktree_name = actual_worktree_path.name

        # Get the branch that was created for this worktree
        # The git_ops fake tracks added worktrees as (path, branch)
        assert len(git_ops.added_worktrees) == 1, (
            f"Expected exactly 1 worktree added, found {len(git_ops.added_worktrees)}"
        )
        added_worktree_path, actual_branch_name = git_ops.added_worktrees[0]
        assert actual_branch_name is not None, "Branch name should not be None"

        # Branch name should be 31 chars (truncated, no date suffix)
        assert len(actual_branch_name) == 31, (
            f"Branch name: expected exactly 31 chars, got {len(actual_branch_name)}"
        )

        # Worktree name should be >31 chars (31 char base + 9 char date suffix)
        assert len(actual_worktree_name) > 31, (
            f"Worktree name: expected >31 chars, got {len(actual_worktree_name)}"
        )

        # Worktree name should end with date suffix (-YY-MM-DD-HHMM)
        date_suffix = get_current_date_suffix()
        assert actual_worktree_name.endswith(date_suffix), (
            f"Worktree name should end with '{date_suffix}', got: {actual_worktree_name}"
        )

        # Branch name should match worktree base (worktree name without date suffix)
        worktree_base = actual_worktree_name.removesuffix(f"-{date_suffix}")
        assert actual_branch_name == worktree_base, (
            f"Branch '{actual_branch_name}' should match worktree base '{worktree_base}'"
        )

        # Both branch and worktree base should be exactly 31 chars
        assert len(actual_branch_name) == 31
        assert len(worktree_base) == 31
