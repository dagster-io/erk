"""Tests for the init command.

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
"""

import json
import os
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.init import perform_statusline_setup
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_creates_global_config_first_time() -> None:
    """Test that init creates global config on first run."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={env.cwd, env.git_dir},
        )
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, decline hooks (shell not detected so no prompt)
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Global config not found" in result.output
        assert "Created global config" in result.output
        # Verify config was saved to in-memory ops
        assert erk_installation.config_exists()
        loaded = erk_installation.load_config()
        assert loaded.erk_root == erk_root.resolve()


def test_init_prompts_for_erk_root() -> None:
    """Test that init prompts for erks root when creating config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "my-erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert ".erk folder" in result.output
        # Verify config was saved correctly to in-memory ops
        loaded_config = erk_installation.load_config()
        assert loaded_config.erk_root == erk_root.resolve()


def test_init_detects_graphite_installed() -> None:
    """Test that init detects when Graphite (gt) is installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={"gt": "/usr/local/bin/gt"})
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) detected" in result.output
        # Verify config was saved with graphite enabled
        loaded_config = erk_installation.load_config()
        assert loaded_config.use_graphite


def test_init_detects_graphite_not_installed() -> None:
    """Test that init detects when Graphite (gt) is NOT installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) not detected" in result.output
        # Verify config was saved with graphite disabled
        loaded_config = erk_installation.load_config()
        assert not loaded_config.use_graphite


def test_init_auto_preset_detects_dagster() -> None:
    """Test that auto preset detects dagster repo and uses dagster preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create pyproject.toml with dagster as the project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "dagster"\n', encoding="utf-8")

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
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_auto_preset_uses_generic_fallback() -> None:
    """Test that auto preset falls back to generic for non-dagster repos."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create pyproject.toml with different project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myproject"\n', encoding="utf-8")

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
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_dagster() -> None:
    """Test that explicit --preset dagster uses dagster preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(
            cli, ["init", "--preset", "dagster", "--no-interactive"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_generic() -> None:
    """Test that explicit --preset generic uses generic preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(
            cli, ["init", "--preset", "generic", "--no-interactive"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Config should be created in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()


def test_init_list_presets_displays_available() -> None:
    """Test that --list-presets displays available presets."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--list-presets"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Available presets:" in result.output
        assert "dagster" in result.output
        assert "generic" in result.output


def test_init_invalid_preset_fails() -> None:
    """Test that invalid preset name fails with helpful error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--preset", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid preset 'nonexistent'" in result.output


def test_init_creates_config_at_erk_dir() -> None:
    """Test that init creates config.toml in .erk/ directory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
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
        # Config should be in .erk/ directory (consolidated location)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()
        # Not at repo root
        assert not (env.cwd / "config.toml").exists()
        # Not in erks_dir anymore (legacy location)
        legacy_path = erk_root / "repos" / env.cwd.name / "config.toml"
        assert not legacy_path.exists()


def test_init_force_overwrites_existing_config() -> None:
    """Test that --force overwrites existing config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create existing config in .erk/ directory
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir(parents=True)
        config_path = erk_dir / "config.toml"
        config_path.write_text("# Old config\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--force", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert config_path.exists()
        # Verify content was overwritten (shouldn't contain "Old config")
        content = config_path.read_text(encoding="utf-8")
        assert "# Old config" not in content


def test_init_skips_silently_when_already_erkified() -> None:
    """Test that init skips project setup when config exists (no error).

    NOTE: Behavior changed from failing to silently skipping project setup.
    The new stepped flow (Step 2) detects already-erk-ified repos and skips
    project configuration, proceeding directly to user setup (Step 3).
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create existing config in .erk/ directory
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir(parents=True)
        config_path = erk_dir / "config.toml"
        config_path.write_text("# Existing config\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        # Now succeeds and shows "already configured" message
        assert result.exit_code == 0, result.output
        assert "Repository already configured for erk" in result.output
        # Config should NOT be overwritten
        content = config_path.read_text(encoding="utf-8")
        assert "# Existing config" in content


def test_init_adds_env_to_gitignore() -> None:
    """Test that init offers to add .env to .gitignore.

    NOTE: Uses erk_isolated_fs_env because this test verifies actual
    .gitignore file content on disk. Cannot migrate to pure mode without
    abstracting file operations in production code.
    """
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
    """Test that init skips all gitignore entries if user declines.

    NOTE: Uses erk_isolated_fs_env because this test verifies actual
    .gitignore file content on disk. Cannot migrate to pure mode without
    abstracting file operations in production code.
    """
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
    """Test that init offers to add .erk/scratch/ and .impl/ to .gitignore.

    NOTE: Uses erk_isolated_fs_env because this test verifies actual
    .gitignore file content on disk. Cannot migrate to pure mode without
    abstracting file operations in production code.
    """
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
    """Test that init handles missing .gitignore gracefully.

    NOTE: Uses erk_isolated_fs_env because this test verifies behavior
    when .gitignore file doesn't exist on disk. Cannot migrate to pure mode
    without abstracting file operations in production code.
    """
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
    """Test that init preserves existing gitignore formatting.

    NOTE: Uses erk_isolated_fs_env because this test verifies actual
    .gitignore file formatting on disk. Cannot migrate to pure mode without
    abstracting file operations in production code.
    """
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


def test_init_first_time_offers_shell_setup() -> None:
    """Test that first-time init offers shell integration setup."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Provide input: erk_root, decline hooks, decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\nn\n")

        assert result.exit_code == 0, result.output
        # Should mention shell integration
        assert "shell integration" in result.output.lower()


def test_init_shell_flag_only_setup() -> None:
    """Test that --shell flag only performs shell setup."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0, result.output
        # Should mention shell but not create config
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
        assert not config_path.exists()


def test_init_detects_bash_shell() -> None:
    """Test that init correctly detects bash shell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "bash" in result.output.lower()


def test_init_detects_zsh_shell() -> None:
    """Test that init correctly detects zsh shell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        zshrc = Path.home() / ".zshrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("zsh", zshrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "zsh" in result.output.lower()


def test_init_detects_fish_shell() -> None:
    """Test that init correctly detects fish shell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        fish_config = Path.home() / ".config" / "fish" / "config.fish"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("fish", fish_config)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "fish" in result.output.lower()


def test_init_skips_unknown_shell() -> None:
    """Test that init skips shell setup for unknown shells."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, decline hooks (no shell prompt - unknown shell)
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Unable to detect shell" in result.output


def test_init_prints_completion_instructions() -> None:
    """Test that init prints completion instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, accept shell, accept config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\ny\ny\n",
            )

        assert result.exit_code == 0, result.output
        # Verify instructions are printed, not file written
        assert "Shell Integration Setup" in result.output
        assert "# Erk completion" in result.output
        assert "source <(erk completion bash)" in result.output


def test_init_prints_wrapper_instructions() -> None:
    """Test that init prints wrapper function instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, accept shell, accept config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\ny\ny\n",
            )

        assert result.exit_code == 0, result.output
        # Verify wrapper instructions are printed
        assert "Shell Integration Setup" in result.output
        assert "# Erk shell integration" in result.output
        assert "erk()" in result.output


def test_init_skips_shell_if_declined() -> None:
    """Test that init skips shell setup if user declines."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Input: erk_root, decline hooks, decline shell
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\nn\n",
            )

        assert result.exit_code == 0, result.output
        # Verify no instructions were printed when declined
        assert "Shell Integration Setup" not in result.output
        assert "Skipping shell integration" in result.output


def test_init_not_in_git_repo_fails() -> None:
    """Test that init fails when not in a git repository."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Remove .git directory to simulate non-git directory
        import shutil

        shutil.rmtree(env.git_dir)

        # Empty git_ops with cwd existing but no .git (simulating non-git directory)
        git_ops = FakeGit(existing_paths={env.cwd})
        global_config = GlobalConfig.test(
            env.cwd / "fake-erks", use_graphite=False, shell_setup_complete=False
        )

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{env.cwd}/erks\n")

        # The command should fail at repo discovery
        assert result.exit_code != 0


def test_shell_setup_confirmation_declined_with_shell_flag() -> None:
    """Test user declining confirmation for global config write (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "n" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\nn\n")

        assert result.exit_code == 0, result.output
        assert "Shell integration instructions shown above" in result.output
        assert "Run 'erk init --shell' to save this preference" in result.output
        # Config should NOT have been updated
        loaded = erk_installation.load_config()
        assert loaded.shell_setup_complete is False


def test_shell_setup_confirmation_accepted_with_shell_flag() -> None:
    """Test user accepting confirmation for global config write (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "y" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 0, result.output
        assert "✓ Global config updated" in result.output
        # Config should have been updated
        loaded = erk_installation.load_config()
        assert loaded.shell_setup_complete is True


def test_shell_setup_confirmation_declined_first_init() -> None:
    """Test user declining confirmation during first-time init."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Input: erk_root, decline hooks, accept shell, decline config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\ny\nn\n")

        assert result.exit_code == 0, result.output
        assert "Shell integration instructions shown above" in result.output
        # Config should exist (created by first-time init)
        assert erk_installation.config_exists()
        # But shell_setup_complete should be False (user declined)
        loaded = erk_installation.load_config()
        assert loaded.shell_setup_complete is False


def test_shell_setup_permission_error_with_shell_flag() -> None:
    """Test permission error handling when saving global config (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)

        # Create an ErkInstallation that raises PermissionError on save
        class PermissionErrorErkInstallation(FakeErkInstallation):
            def save_config(self, config: GlobalConfig) -> None:
                raise PermissionError(
                    f"Cannot write to file: {self.config_path()}\n"
                    "The file exists but is not writable.\n\n"
                    "To fix this manually:\n"
                    f"  1. Make it writable: chmod 644 {self.config_path()}\n"
                    "  2. Run erk init --shell again"
                )

        erk_installation = PermissionErrorErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "y" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 1, result.output
        assert "❌ Error: Could not save global config" in result.output
        assert "Cannot write to file" in result.output
        assert "Shell integration instructions shown above" in result.output
        assert "You can use them now - erk just couldn't save" in result.output


def test_shell_setup_permission_error_first_init() -> None:
    """Test permission error handling during first-time init (doesn't exit)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        # Create an ErkInstallation that allows first save but fails on second
        class ConditionalPermissionErrorErkInstallation(FakeErkInstallation):
            def __init__(self) -> None:
                super().__init__(config=None)
                self.save_count = 0

            def save_config(self, config: GlobalConfig) -> None:
                self.save_count += 1
                if self.save_count == 1:
                    # First save (creating global config) succeeds
                    super().save_config(config)
                else:
                    # Second save (shell setup update) fails
                    raise PermissionError(
                        f"Cannot write to file: {self.config_path()}\n"
                        "Permission denied during write operation."
                    )

        erk_installation = ConditionalPermissionErrorErkInstallation()

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Input: erk_root, decline hooks, accept shell, accept config save
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\ny\ny\n")

        # Should NOT exit with error code (first-time init continues)
        assert result.exit_code == 0, result.output
        assert "❌ Error: Could not save global config" in result.output
        assert "Cannot write to file" in result.output
        assert "Shell integration instructions shown above" in result.output
        # First save succeeded, second failed
        assert erk_installation.save_count == 2


def test_init_offers_claude_permission_when_missing() -> None:
    """Test that init offers to add erk permission when Claude settings exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings in repo without erk permission
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text(
            json.dumps({"permissions": {"allow": ["Bash(git:*)"]}}),
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept permission (y), confirm write (y), decline hooks (n), delete backup (y)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\ny\nn\ny\n")

        assert result.exit_code == 0, result.output
        assert "Claude settings found" in result.output
        assert "Bash(erk:*)" in result.output
        assert "Proceed with writing changes?" in result.output
        # Verify permission was added
        updated_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "Bash(erk:*)" in updated_settings["permissions"]["allow"]


def test_init_skips_claude_permission_when_already_configured() -> None:
    """Test that init skips prompt when erk permission already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings WITH erk permission already present
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text(
            json.dumps({"permissions": {"allow": ["Bash(erk:*)", "Bash(git:*)"]}}),
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should NOT prompt about Claude permission
        assert "Claude settings found" not in result.output


def test_init_skips_claude_permission_when_no_settings() -> None:
    """Test that init skips Claude permission setup when no settings.json exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # No .claude/settings.json file in repo

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should NOT prompt about Claude permission
        assert "Claude settings found" not in result.output


def test_init_handles_declined_claude_permission() -> None:
    """Test that init handles user declining Claude permission gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings in repo without erk permission
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        original_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
        claude_settings_path.write_text(json.dumps(original_settings), encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Decline permission (n), decline hooks (n)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\nn\n")

        assert result.exit_code == 0, result.output
        assert "Skipped" in result.output
        # Verify permission was NOT added
        unchanged_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "Bash(erk:*)" not in unchanged_settings["permissions"]["allow"]


def test_init_handles_declined_write_confirmation() -> None:
    """Test that init handles user declining write confirmation gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings in repo without erk permission
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        original_settings = {"permissions": {"allow": ["Bash(git:*)"]}}
        claude_settings_path.write_text(json.dumps(original_settings), encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept permission (y), decline write (n), decline hooks (n)
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\nn\nn\n")

        assert result.exit_code == 0, result.output
        assert "Proceed with writing changes?" in result.output
        assert "No changes made to settings.json" in result.output
        # Verify permission was NOT added
        unchanged_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "Bash(erk:*)" not in unchanged_settings["permissions"]["allow"]


# --- Tests for --hooks flag ---


def test_init_hooks_flag_adds_hooks_to_empty_settings() -> None:
    """Test that --hooks flag adds erk hooks to settings.json."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create empty Claude settings
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text("{}", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept hook addition
        result = runner.invoke(cli, ["init", "--hooks"], obj=test_ctx, input="y\n")

        assert result.exit_code == 0, result.output
        assert "Erk uses Claude Code hooks" in result.output
        assert "Added erk hooks" in result.output

        # Verify hooks were added
        updated_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "hooks" in updated_settings
        assert "UserPromptSubmit" in updated_settings["hooks"]
        assert "PreToolUse" in updated_settings["hooks"]


def test_init_hooks_flag_skips_when_already_configured() -> None:
    """Test that --hooks flag skips when hooks already exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings WITH erk hooks already present
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        existing_settings = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook"
                                ),
                            }
                        ],
                    }
                ],
                "PreToolUse": [
                    {
                        "matcher": "ExitPlanMode",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"
                                ),
                            }
                        ],
                    }
                ],
            }
        }
        claude_settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # No input needed - should skip silently
        result = runner.invoke(cli, ["init", "--hooks"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Hooks already configured" in result.output


def test_init_hooks_flag_handles_declined() -> None:
    """Test that --hooks flag handles user declining gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create empty Claude settings
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text("{}", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Decline hook addition
        result = runner.invoke(cli, ["init", "--hooks"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0, result.output
        assert "Skipped" in result.output
        assert "erk init --hooks" in result.output

        # Verify hooks were NOT added
        unchanged_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "hooks" not in unchanged_settings


def test_init_hooks_flag_creates_settings_if_missing() -> None:
    """Test that --hooks flag creates settings.json if it doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # No .claude/settings.json file
        claude_settings_path = env.cwd / ".claude" / "settings.json"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept hook addition
        result = runner.invoke(cli, ["init", "--hooks"], obj=test_ctx, input="y\n")

        assert result.exit_code == 0, result.output
        assert "Added erk hooks" in result.output

        # Verify file was created with hooks
        assert claude_settings_path.exists()
        created_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "hooks" in created_settings


def test_init_hooks_flag_only_does_hook_setup() -> None:
    """Test that --hooks flag skips all other init steps."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Accept hook addition
        result = runner.invoke(cli, ["init", "--hooks"], obj=test_ctx, input="y\n")

        assert result.exit_code == 0, result.output

        # Verify no config.toml was created (other init steps skipped)
        config_path = env.cwd / ".erk" / "config.toml"
        assert not config_path.exists()


def test_init_main_flow_syncs_hooks_automatically() -> None:
    """Test that main init flow syncs hooks automatically via artifact sync.

    Hooks are now part of artifact sync (since they're bundled artifacts),
    so they're added automatically before the interactive hook prompt runs.
    This test verifies that behavior.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create Claude settings without erk permission or hooks
        claude_settings_path = env.cwd / ".claude" / "settings.json"
        claude_settings_path.parent.mkdir(parents=True)
        claude_settings_path.write_text(
            json.dumps({"permissions": {"allow": []}}),
            encoding="utf-8",
        )

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)

        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Decline permission (n) - hooks should already be synced via artifact sync
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0, result.output
        # Permission prompt should appear
        assert "Bash(erk:*)" in result.output
        # Hooks are synced as part of artifact sync, so the interactive prompt
        # shows "Hooks already configured" instead of asking
        assert "Hooks already configured" in result.output

        # Verify hooks were added (by artifact sync)
        updated_settings = json.loads(claude_settings_path.read_text(encoding="utf-8"))
        assert "hooks" in updated_settings


def test_init_syncs_artifacts_successfully() -> None:
    """Test that init calls sync_artifacts and shows success message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Mock sync_artifacts to return success
        from erk.artifacts.sync import SyncResult

        with mock.patch("erk.cli.commands.init.sync_artifacts") as mock_sync:
            mock_sync.return_value = SyncResult(
                success=True, artifacts_installed=5, message="Synced 5 artifact files"
            )

            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

            assert result.exit_code == 0, result.output
            # Verify sync_artifacts was called with correct arguments
            mock_sync.assert_called_once_with(env.cwd, force=False)
            # Verify success message appears in output
            assert "✓" in result.output
            assert "Synced 5 artifact files" in result.output


def test_init_shows_warning_on_artifact_sync_failure() -> None:
    """Test that init shows warning but continues when artifact sync fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Mock sync_artifacts to return failure
        from erk.artifacts.sync import SyncResult

        with mock.patch("erk.cli.commands.init.sync_artifacts") as mock_sync:
            mock_sync.return_value = SyncResult(
                success=False, artifacts_installed=0, message="Bundled .claude/ not found"
            )

            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

            # Init should continue despite sync failure (non-fatal)
            assert result.exit_code == 0, result.output
            # Verify sync_artifacts was called
            mock_sync.assert_called_once_with(env.cwd, force=False)
            # Verify warning appears in output
            assert "⚠" in result.output
            assert "Artifact sync failed" in result.output
            assert "Bundled .claude/ not found" in result.output
            assert "Run 'erk artifact sync' to retry" in result.output


# --- Tests for --statusline flag ---
#
# These tests use perform_statusline_setup() directly with path injection
# to avoid mocking HOME environment variable.


def test_statusline_setup_configures_empty_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup configures statusline in empty settings.json."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # Create settings.json
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")

    # Mock user_confirm to return True (confirm write)
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=True):
        perform_statusline_setup(settings_path=settings_path)

    # Verify settings were written
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "statusLine" in updated_settings
    assert updated_settings["statusLine"]["type"] == "command"
    assert "erk-statusline" in updated_settings["statusLine"]["command"]


def test_statusline_setup_creates_settings_if_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup creates settings.json if it doesn't exist."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # No settings.json file
    settings_path = tmp_path / ".claude" / "settings.json"

    # Mock user_confirm to return True (confirm write)
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=True):
        perform_statusline_setup(settings_path=settings_path)

    # Verify file was created
    assert settings_path.exists()
    created_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "erk-statusline" in created_settings["statusLine"]["command"]


def test_statusline_setup_skips_when_already_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup skips when erk-statusline is already configured."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # Create settings.json with erk-statusline already configured
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    existing_settings = {
        "statusLine": {
            "type": "command",
            "command": "uvx erk-statusline",
        }
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    # Run setup with injected path (no confirm needed - skips without prompting)
    perform_statusline_setup(settings_path=settings_path)

    # File should not have been modified - content should be same
    unchanged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert unchanged_settings == existing_settings


def test_statusline_setup_prompts_for_different_command(tmp_path: Path) -> None:
    """Test perform_statusline_setup prompts when different statusline is configured."""
    # Create settings.json with different statusline
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    existing_settings = {
        "statusLine": {
            "type": "command",
            "command": "other-statusline",
        }
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    # Mock user_confirm to return False (decline replacement)
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=False):
        perform_statusline_setup(settings_path=settings_path)

    # Verify settings were NOT changed
    unchanged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert unchanged_settings["statusLine"]["command"] == "other-statusline"


def test_statusline_setup_replaces_when_confirmed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup replaces existing statusline when user confirms."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # Create settings.json with different statusline
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    existing_settings = {
        "statusLine": {
            "type": "command",
            "command": "other-statusline",
        }
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    # Mock user_confirm to return True for both prompts
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=True):
        perform_statusline_setup(settings_path=settings_path)

    # Verify settings were updated
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "erk-statusline" in updated_settings["statusLine"]["command"]


def test_init_statusline_flag_recognized() -> None:
    """Test that --statusline flag is recognized and invokes statusline setup.

    This is a minimal CLI integration test - detailed behavior is tested
    via perform_statusline_setup() unit tests above.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Mock the function to avoid HOME dependency in CLI test
        with mock.patch("erk.cli.commands.init.perform_statusline_setup") as mock_setup:
            result = runner.invoke(cli, ["init", "--statusline"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify the function was called with settings_path=None (uses default)
        mock_setup.assert_called_once_with(settings_path=None)

        # Verify no config.toml was created (other init steps skipped)
        config_path = env.cwd / ".erk" / "config.toml"
        assert not config_path.exists()


# --- Tests for stepped flow and re-init behavior ---


def test_init_stepped_flow_shows_three_steps() -> None:
    """Test that init shows the three-step flow in output."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify three steps are shown
        assert "Step 1: Checking repository..." in result.output
        assert "Step 2: Project configuration..." in result.output
        assert "Step 3: User configuration..." in result.output
        assert "Initialization complete!" in result.output


def test_init_skips_project_setup_when_already_erkified() -> None:
    """Test that init skips project setup when repo is already erk-ified."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create existing erk config to simulate already erk-ified repo
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir(parents=True)
        config_path = erk_dir / "config.toml"
        config_path.write_text("# Existing config\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify it shows "already configured" message
        assert "Repository already configured for erk" in result.output
        # Verify config was NOT overwritten
        content = config_path.read_text(encoding="utf-8")
        assert "# Existing config" in content


def test_init_force_overwrites_when_already_erkified() -> None:
    """Test that init --force overwrites config even when already erk-ified."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create existing erk config
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir(parents=True)
        config_path = erk_dir / "config.toml"
        config_path.write_text("# Old config\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--force", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify config was overwritten
        content = config_path.read_text(encoding="utf-8")
        assert "# Old config" not in content


def test_init_step1_shows_repo_name() -> None:
    """Test that step 1 shows the detected repository name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify step 1 shows the repo name (the directory name)
        assert "Git repository detected:" in result.output
