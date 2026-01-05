"""Tests for gitignore entry handling during init.

Mock Usage Policy:
------------------
This file uses minimal mocking for external boundaries:

1. os.environ HOME patches:
   - LEGITIMATE: Testing path resolution logic that depends on $HOME
   - The init command uses Path.home() to determine ~/.erk location
   - Patching HOME redirects to temp directory for test isolation
   - Cannot be replaced with fakes (environment variable is external boundary)

2. Global config operations:
   - Uses FakeErkInstallation for dependency injection
   - No mocking required - proper abstraction via ConfigStore interface
   - Tests inject FakeErkInstallation with desired initial state

NOTE: These tests use erk_isolated_fs_env because they verify actual
.gitignore file content on disk. Cannot migrate to pure mode without
abstracting file operations in production code.
"""

import os
from unittest import mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_adds_env_to_gitignore() -> None:
    """Test that init offers to add .env to .gitignore."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .gitignore
        gitignore = env.cwd / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept prompt for .env, decline .erk/scratch/, .impl/, hooks, and statusline
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\nn\nn\nn\nn\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".env" in gitignore_content


def test_init_skips_gitignore_entries_if_declined() -> None:
    """Test that init skips all gitignore entries if user declines."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .gitignore
        gitignore = env.cwd / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Decline all prompts (.env, .erk/scratch/, .impl/, hooks, statusline)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\nn\nn\nn\nn\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".env" not in gitignore_content
        assert ".erk/scratch/" not in gitignore_content
        assert ".impl/" not in gitignore_content


def test_init_adds_erk_scratch_and_impl_to_gitignore() -> None:
    """Test that init offers to add .erk/scratch/ and .impl/ to .gitignore."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .gitignore
        gitignore = env.cwd / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Decline .env, accept .erk/scratch/ and .impl/, decline hooks
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\ny\ny\nn\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".env" not in gitignore_content
        assert ".erk/scratch/" in gitignore_content
        assert ".impl/" in gitignore_content


def test_init_handles_missing_gitignore() -> None:
    """Test that init handles missing .gitignore gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # No .gitignore file

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should not crash or prompt about gitignore


def test_init_preserves_gitignore_formatting() -> None:
    """Test that init preserves existing gitignore formatting."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .gitignore with specific formatting
        gitignore = env.cwd / ".gitignore"
        original_content = "# Python\n*.pyc\n__pycache__/\n"
        gitignore.write_text(original_content, encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept .env, decline .erk/scratch/, .impl/, and hooks
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\nn\nn\nn\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        # Original content should be preserved
        assert "# Python" in gitignore_content
        assert "*.pyc" in gitignore_content
        # New entry should be added
        assert ".env" in gitignore_content
