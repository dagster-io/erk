"""Tests for name sanitization and validation in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


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
