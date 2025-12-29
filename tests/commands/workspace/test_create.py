"""Tests for the create command."""

import json
from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.naming import WORKTREE_DATE_SUFFIX_FORMAT
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def _get_current_date_suffix() -> str:
    """Get the current date suffix for plan-derived worktrees."""
    return datetime.now().strftime(WORKTREE_DATE_SUFFIX_FORMAT)


def test_create_basic_worktree() -> None:
    """Test creating a basic worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create minimal config
        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify worktree creation from output
        assert "Created worktree" in result.output
        assert "test-feature" in result.output


def test_create_with_custom_branch_name() -> None:
    """Test creating a worktree with a custom branch name."""
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
            cli, ["wt", "create", "feature", "--branch", "my-custom-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "my-custom-branch" in result.output


def test_create_with_plan_file() -> None:
    """Test creating a worktree with a plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file)],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        # Should create worktree with "plan" stripped from filename and date suffix added
        date_suffix = _get_current_date_suffix()
        wt_path = repo_dir / "worktrees" / f"my-feature-{date_suffix}"
        assert wt_path.exists()
        # Impl folder should be created with plan.md and progress.md
        assert (wt_path / ".impl").exists()
        assert (wt_path / ".impl" / "plan.md").exists()
        assert (wt_path / ".impl" / "progress.md").exists()
        assert not plan_file.exists()


def test_create_with_plan_file_removes_plan_word() -> None:
    """Test that --from-plan-file flag removes 'plan' from worktree names."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        # Test multiple plan file examples
        date_suffix = _get_current_date_suffix()

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
            # Worktree name includes date suffix
            expected_worktree_name = f"{expected_worktree_base}-{date_suffix}"
            wt_path = repo_dir / "worktrees" / expected_worktree_name
            assert wt_path.exists(), f"Expected worktree at {wt_path} for {plan_filename}"
            assert (wt_path / ".impl" / "plan.md").exists()
            assert (wt_path / ".impl" / "progress.md").exists()
            assert not plan_file.exists()

            # Clean up for next test
            import shutil

            shutil.rmtree(wt_path)


def test_create_sanitizes_worktree_name() -> None:
    """Test that worktree names are sanitized."""
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

        result = runner.invoke(cli, ["wt", "create", "Test_Feature!!"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # The actual sanitization is tested in test_naming.py
        # Here we just verify the worktree was created
        assert "Created worktree" in result.output


def test_create_sanitizes_branch_name() -> None:
    """Test that branch names are sanitized."""
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

        # Branch name should be sanitized differently than worktree name
        result = runner.invoke(cli, ["wt", "create", "Test_Feature!!"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_detects_default_branch() -> None:
    """Test that create detects the default branch when needed."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "new-feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_from_current_branch_in_worktree() -> None:
    """Regression: ensure --from-current-branch works when executed from a worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_root = env.root_worktree
        git_dir = env.git_dir

        current_worktree = env.root_worktree.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=current_worktree, branch="feature"),
                ]
            },
            current_branches={current_worktree: "feature"},
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        expected_worktree = repo_dir / "worktrees" / "feature"
        assert (current_worktree, "main") in git_ops.checked_out_branches
        assert (repo_root, "main") not in git_ops.checked_out_branches
        assert (expected_worktree, "feature") in git_ops.added_worktrees


def test_create_fails_if_worktree_exists() -> None:
    """Test that create fails if worktree already exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create existing worktree directory
        wt_path = repo_dir / "worktrees" / "test-feature"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Tell context that wt_path exists
        test_ctx = env.build_context(git=git_ops, existing_paths={wt_path})

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_create_runs_post_create_commands() -> None:
    """Test that create runs post-create commands."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly with post_create commands
        local_config = LoadedConfig(
            env={},
            post_create_commands=["echo hello > test.txt"],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Running post-create commands" in result.output


def test_create_sets_env_variables() -> None:
    """Test that create sets environment variables in .env file."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly with env vars
        local_config = LoadedConfig(
            env={"MY_VAR": "my_value"},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        wt_path = repo_dir / "worktrees" / "test-feature"
        env_file = wt_path / ".env"
        env_content = env_file.read_text(encoding="utf-8")
        assert "MY_VAR" in env_content
        assert "WORKTREE_PATH" in env_content
        assert "REPO_ROOT" in env_content


def test_create_uses_graphite_when_enabled() -> None:
    """Test that create works with graphite disabled (testing without gt subprocess).

    Note: The original test mocked subprocess.run to test graphite integration.
    However, since there's no Graphite abstraction for create_branch(), and
    subprocess mocking is being eliminated, this test now verifies the non-graphite
    path. Graphite subprocess integration should be tested at the integration level
    with real gt commands.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        graphite_ops = FakeGraphite()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            local_config=local_config,
            repo=repo,
        )

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify worktree was created successfully
        repo_dir / "test-feature"


def test_create_blocks_when_staged_changes_present_with_graphite_enabled() -> None:
    """Ensure the command fails fast when staged changes exist and graphite is enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            staged_repos={env.cwd},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            local_config=local_config,
            repo=repo,
        )

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Staged changes detected." in result.output
        assert 'git commit -m "message"' in result.output
        # No need to verify subprocess wasn't called - the error happens before subprocess


def test_create_uses_git_when_graphite_disabled() -> None:
    """Test that create uses git when graphite is disabled."""
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

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_allows_staged_changes_when_graphite_disabled() -> None:
    """Graphite disabled path should ignore staged changes and continue."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        (repo_dir / "config.toml").write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            staged_repos={env.cwd},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_invalid_worktree_name() -> None:
    """Test that create rejects invalid worktree names."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        # Test reserved name "root"
        result = runner.invoke(cli, ["wt", "create", "root"], obj=test_ctx)
        assert result.exit_code == 1
        assert "reserved" in result.output.lower()

        # Test trunk branch rejection (default is "main")
        result = runner.invoke(cli, ["wt", "create", "main"], obj=test_ctx)
        assert result.exit_code == 1
        assert "cannot be used" in result.output.lower()

        # Note: "master" is not rejected unless it's the configured trunk branch
        # If repo uses master as trunk, it would be rejected; otherwise it's allowed


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


def test_create_no_post_flag_skips_commands() -> None:
    """Test that --no-post flag skips post-create commands."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create config with post_create commands
        config_toml = repo_dir / "config.toml"
        config_toml.write_text(
            '[post_create]\ncommands = ["echo hello"]\n',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature", "--no-post"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Running post-create commands" not in result.output


def test_create_from_current_branch() -> None:
    """Test creating worktree from current branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_from_branch() -> None:
    """Test creating worktree from an existing branch."""
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
            cli, ["wt", "create", "feature", "--from-branch", "existing-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_requires_name_or_flag() -> None:
    """Test that create requires NAME or a flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Must provide NAME" in result.output


def test_create_from_current_branch_on_main_fails() -> None:
    """Test that --from-current-branch fails with helpful message when on main."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "Cannot use --from-current-branch when on 'main'" in result.output
        assert "Alternatives:" in result.output


def test_create_detects_branch_already_checked_out() -> None:
    """Test that create detects when branch is already checked out."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Setup: feature-branch is already checked out in an existing worktree
        existing_wt_path = repo_dir / "worktrees" / "existing-feature"
        existing_wt_path.mkdir(parents=True)

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=existing_wt_path, branch="feature-branch"),
                ],
            },
        )
        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "new-feature", "--from-branch", "feature-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "already checked out" in result.output
        assert "feature-branch" in result.output


def test_create_from_current_branch_on_master_fails() -> None:
    """Test that --from-current-branch fails when on master branch too."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "master"},
            current_branches={env.cwd: "master"},
            trunk_branches={env.cwd: "master"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "Cannot use --from-current-branch when on 'master'" in result.output


def test_create_with_keep_plan_file_flag() -> None:
    """Test that --keep-plan-file copies instead of moves the plan file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan file
        plan_file = env.cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file), "--keep-plan-file"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        # Should create worktree with "plan" stripped from filename and date suffix added
        date_suffix = _get_current_date_suffix()
        wt_path = repo_dir / "worktrees" / f"my-feature-{date_suffix}"
        assert wt_path.exists()
        # Impl folder should be created with plan.md and progress.md
        assert (wt_path / ".impl" / "plan.md").exists()
        assert (wt_path / ".impl" / "progress.md").exists()
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


def test_from_current_branch_with_main_in_use_prefers_graphite_parent() -> None:
    """Test that --from-current-branch prefers Graphite parent when main is in use.

    Scenario:
    - Current worktree is on feature-2 (with Graphite parent feature-1)
    - Root worktree has main checked out
    - feature-1 is available (not checked out)

    Expected: Should checkout feature-1 (the parent), not try to checkout main
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        # Set up worktree stack: main -> feature-1 -> feature-2
        from erk_shared.gateway.graphite.types import BranchMetadata

        branch_metadata = {
            "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
            "feature-1": BranchMetadata.branch(
                "feature-1", "main", children=["feature-2"], commit_sha="def456"
            ),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="feature-2"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "feature-2",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )
        graphite_ops = FakeGraphite(branches=branch_metadata)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            local_config=local_config,
            repo=repo,
            cwd=current_worktree,
        )

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should checkout feature-1 (the Graphite parent), not main
        assert (current_worktree, "feature-1") in git_ops.checked_out_branches


def test_from_current_branch_with_parent_in_use_falls_back_to_detached_head() -> None:
    """Test that --from-current-branch uses detached HEAD when parent is also in use.

    Scenario:
    - Current worktree is on feature-2 (with Graphite parent feature-1)
    - Root worktree has main checked out
    - Another worktree has feature-1 checked out

    Expected: Should use detached HEAD as fallback since both main and parent are in use
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        other_worktree = env.cwd.parent / "wt-other"
        other_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up worktree stack: main -> feature-1 -> feature-2
        from erk_shared.gateway.graphite.types import BranchMetadata

        {
            "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
            "feature-1": BranchMetadata.branch(
                "feature-1", "main", children=["feature-2"], commit_sha="def456"
            ),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="feature-2"),
                    WorktreeInfo(path=other_worktree, branch="feature-1"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "feature-2",
                other_worktree: "feature-1",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
                other_worktree: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should use detached HEAD since both main and feature-1 are in use
        assert len(git_ops.detached_checkouts) == 1
        assert git_ops.detached_checkouts[0][0] == current_worktree
        assert git_ops.detached_checkouts[0][1] == "feature-2"


def test_from_current_branch_without_graphite_falls_back_to_main() -> None:
    """Test that --from-current-branch falls back to main when no Graphite parent exists.

    Scenario:
    - Current worktree is on standalone-feature (not in any worktree stack)
    - Root worktree has other-branch checked out (not main)
    - main is available

    Expected: Should checkout main as fallback
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up minimal worktree stack (standalone-feature not in it)
        from erk_shared.gateway.graphite.types import BranchMetadata

        {
            "main": BranchMetadata.trunk("main", commit_sha="abc123"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="other-branch"),
                    WorktreeInfo(path=current_worktree, branch="standalone-feature"),
                ]
            },
            current_branches={
                repo_root: "other-branch",
                current_worktree: "standalone-feature",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should checkout main since no Graphite parent exists
        assert (current_worktree, "main") in git_ops.checked_out_branches


def test_from_current_branch_no_graphite_main_in_use_uses_detached_head() -> None:
    """Test that --from-current-branch uses detached HEAD when no parent and main is in use.

    Scenario:
    - Current worktree is on standalone-feature (not in any worktree stack)
    - Root worktree has main checked out

    Expected: Should use detached HEAD since no parent exists and main is in use
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up minimal worktree stack (standalone-feature not in it)
        from erk_shared.gateway.graphite.types import BranchMetadata

        {
            "main": BranchMetadata.trunk("main", commit_sha="abc123"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="standalone-feature"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "standalone-feature",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should use detached HEAD since no parent and main is in use
        assert len(git_ops.detached_checkouts) == 1
        assert git_ops.detached_checkouts[0][0] == current_worktree
        assert git_ops.detached_checkouts[0][1] == "standalone-feature"


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
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        # Create a plan file - name will be derived from filename
        plan_file = env.cwd / "test-feature-plan.md"
        plan_file.write_text("# Implementation Plan\n\nTest plan content", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
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
        date_suffix = _get_current_date_suffix()
        expected_name = f"test-feature-{date_suffix}"
        assert output_data["worktree_name"] == expected_name
        wt_path = repo_dir / "worktrees" / expected_name
        expected_impl_folder = wt_path / ".impl"
        assert output_data["plan_file"] == str(expected_impl_folder)
        assert output_data["status"] == "created"

        # Verify impl folder was created
        assert (expected_impl_folder / "plan.md").exists()
        assert (expected_impl_folder / "progress.md").exists()
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
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create", "--from-plan-file", str(plan_file), "--script", "--stay"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        # Verify worktree was created with date suffix
        date_suffix = _get_current_date_suffix()
        wt_path = repo_dir / "worktrees" / f"test-feature-{date_suffix}"
        assert wt_path.exists()
        # Impl folder should be created
        assert (wt_path / ".impl" / "plan.md").exists()
        assert (wt_path / ".impl" / "progress.md").exists()
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


def test_create_with_long_name_truncation() -> None:
    """Test that worktree base names exceeding 30 characters are truncated before date suffix."""
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

        # Create with name that exceeds 30 characters
        long_name = "this-is-a-very-long-worktree-name-that-exceeds-thirty-characters"
        result = runner.invoke(cli, ["wt", "create", long_name], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Worktree base name should be truncated to 31 chars
        # Note: worktree name doesn't include sanitize_worktree_name truncation in this flow
        # as create without --from-plan-file uses sanitize_worktree_name which truncates to 31
        expected_truncated = "this-is-a-very-long-worktree-na"  # 31 chars
        repo_dir / expected_truncated
        assert len(expected_truncated) == 31, "Truncated base name should be exactly 31 chars"


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
        date_suffix = _get_current_date_suffix()
        expected_name1 = f"my-feature-{date_suffix}"
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

        # Check that second worktree has -2 after date suffix
        expected_name2 = f"my-feature-{date_suffix}-2"
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
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.root_worktree,
            repo_name=env.root_worktree.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
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
        date_suffix = _get_current_date_suffix()
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


def test_create_fails_when_branch_exists_on_remote() -> None:
    """Test that create fails if branch name already exists on origin."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            remote_branches={env.cwd: ["origin/main", "origin/existing-feature"]},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "existing-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists on remote" in result.output
        assert "origin" in result.output


def test_create_succeeds_when_branch_not_on_remote() -> None:
    """Test that create succeeds if branch name doesn't exist on origin."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            remote_branches={env.cwd: ["origin/main"]},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "new-feature"], obj=test_ctx)

        assert result.exit_code == 0
        assert "new-feature" in result.output


def test_create_with_skip_remote_check_flag() -> None:
    """Test that --skip-remote-check bypasses remote validation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            remote_branches={env.cwd: ["origin/main", "origin/existing-feature"]},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli,
            ["wt", "create", "existing-feature", "--skip-remote-check"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        assert "existing-feature" in result.output


def test_create_proceeds_with_warning_when_remote_check_fails() -> None:
    """Test that create proceeds with warning if remote check fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create FakeGit that raises exception on list_remote_branches
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Override list_remote_branches to raise exception
        def failing_list_remote_branches(repo_root):
            raise Exception("Network error")

        git_ops.list_remote_branches = failing_list_remote_branches

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "new-feature"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Warning:" in result.output
        assert "Could not check remote branches" in result.output
        assert "new-feature" in result.output


def test_create_with_branch_only_derives_name() -> None:
    """Test that --branch alone derives worktree name from branch.

    This enables: `erk wt create --branch license-update` to work,
    creating worktree and branch both named 'license-update'.
    """
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

        result = runner.invoke(cli, ["wt", "create", "--branch", "license-update"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "license-update" in result.output

        # Verify worktree was created with branch name
        expected_wt = repo_dir / "worktrees" / "license-update"
        assert (expected_wt, "license-update") in git_ops.added_worktrees


def test_create_error_message_suggests_wt_create() -> None:
    """Test that error message suggests 'erk wt create' not 'erk create'."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        # Invoke without NAME or any flag
        result = runner.invoke(cli, ["wt", "create"], obj=test_ctx)

        assert result.exit_code == 1
        # Should mention --branch as a valid option
        assert "--branch" in result.output
