"""Tests for output modes (JSON, script, --stay) in worktree creation."""

import json

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.git.fake import FakeGit
from tests.commands.workspace.create.conftest import get_current_date_suffix
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_create_with_json_output() -> None:
    """Test creating a worktree with JSON output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify JSON output
        output_data = json.loads(result.output)
        assert output_data["worktree_name"] == "test-feature"
        assert output_data["worktree_path"] == str(repo_dir / "worktrees" / "test-feature")
        assert output_data["branch_name"] == "test-feature"
        assert output_data["plan_file"] is None
        assert output_data["status"] == "created"

        # Verify worktree was actually created
        repo_dir / "test-feature"


def test_create_existing_worktree_with_json() -> None:
    """Test creating a worktree that already exists with JSON output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create existing worktree
        existing_wt = repo_dir / "worktrees" / "existing-feature"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={existing_wt: "existing-branch"},
        )

        # Tell context that existing_wt exists
        test_ctx = env.build_context(git=git_ops, existing_paths={existing_wt})

        result = runner.invoke(cli, ["wt", "create", "existing-feature", "--json"], obj=test_ctx)

        assert result.exit_code == 1, result.output

        # Verify JSON error output
        output_data = json.loads(result.output)
        assert output_data["worktree_name"] == "existing-feature"
        assert output_data["worktree_path"] == str(existing_wt)
        assert output_data["branch_name"] == "existing-branch"
        assert output_data["status"] == "exists"


def test_create_json_and_script_mutually_exclusive() -> None:
    """Test that --json and --script flags are mutually exclusive."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "test-feature", "--json", "--script"], obj=test_ctx
        )

        # Should fail with validation error
        assert result.exit_code == 1
        assert "Cannot use both --json and --script" in result.output


def test_create_with_json_and_plan_file() -> None:
    """Test creating a worktree with JSON output and plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        # Create a plan file - name will be derived from filename
        plan_file = env.cwd / "test-feature-plan.md"
        plan_content = (
            "---\nsteps:\n  - name: 'First step'\n---\n\n# Implementation Plan\n\nTest plan content"
        )
        plan_file.write_text(plan_content, encoding="utf-8")

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

        # Don't provide NAME - it's derived from plan filename
        result = runner.invoke(
            cli,
            ["wt", "create", "--json", "--from-plan-file", str(plan_file)],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output

        # Verify JSON output includes plan file
        output_data = json.loads(result.output)
        # Name is derived from "test-feature-plan.md" -> "test-feature" with date suffix
        date_suffix = get_current_date_suffix()
        expected_name = f"test-feature-{date_suffix}"
        assert output_data["worktree_name"] == expected_name
        wt_path = repo_dir / "worktrees" / expected_name
        expected_impl_folder = wt_path / ".impl"
        assert output_data["plan_file"] == str(expected_impl_folder)
        assert output_data["status"] == "created"

        # Verify impl folder was created
        assert (expected_impl_folder / "plan.md").exists()
        assert not plan_file.exists()  # Original should be moved, not copied


def test_create_with_json_no_plan() -> None:
    """Test that JSON output has null plan_file when no plan is provided."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify JSON output has null plan_file
        output_data = json.loads(result.output)
        assert output_data["plan_file"] is None
        assert output_data["status"] == "created"


def test_create_with_stay_prevents_script_generation() -> None:
    """Test that --stay flag prevents script generation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "test-feature", "--script", "--stay"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # When --stay is used, no script path should be output
        # The output should contain only the creation message (no navigation instructions)
        assert "Created worktree at" in result.output
        assert "Shell integration not detected" not in result.output
        # Should still create the worktree
        repo_dir / "test-feature"


def test_create_with_stay_and_json() -> None:
    """Test that --stay works with --json output mode."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "test-feature", "--json", "--stay"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output

        # Verify JSON output is still correct
        output_data = json.loads(result.output)
        assert output_data["worktree_name"] == "test-feature"
        assert output_data["status"] == "created"
        # Verify worktree was created
        repo_dir / "test-feature"


def test_create_with_stay_and_plan_file() -> None:
    """Test that --stay works with --from-plan-file flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "test-feature-plan.md"
        plan_file.write_text("# Test Feature Plan\n", encoding="utf-8")

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
            ["wt", "create", "--from-plan-file", str(plan_file), "--script", "--stay"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        # Verify worktree was created with date suffix
        date_suffix = get_current_date_suffix()
        wt_path = repo_dir / "worktrees" / f"test-feature-{date_suffix}"
        assert wt_path.exists()
        # Impl folder should be created
        assert (wt_path / ".impl" / "plan.md").exists()
        assert not plan_file.exists()
        # When --stay is used, only show creation message (no navigation)
        assert "Created worktree at" in result.output
        assert "Shell integration not detected" not in result.output


def test_create_default_behavior_generates_script() -> None:
    """Test that default behavior (without --stay) still generates script."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature", "--script"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should generate script path in output
        assert "/tmp/" in result.output or "erk-" in result.output
        # Verify worktree was created
        repo_dir / "test-feature"
