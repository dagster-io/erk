"""Tests for global config creation during init.

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

import os
from unittest import mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
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
        # Note: FakeShell only affects context.shell, not DirenvCapability which
        # uses RealShell via registry. If direnv is installed on the real system,
        # DirenvCapability will create .gitignore triggering prompts.
        shell_ops = FakeShell(installed_tools={})

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, then decline all gitignore prompts that may appear
        # (DirenvCapability may create .gitignore if direnv is on the real system)
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\nn\nn\nn\n")

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
        shell_ops = FakeShell(installed_tools={})

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, then decline all gitignore prompts that may appear
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\nn\nn\nn\n")

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
        # gt installed (FakeShell affects context.shell for graphite detection)
        shell_ops = FakeShell(installed_tools={"gt": "/usr/local/bin/gt"})
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, then decline all gitignore prompts that may appear
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\nn\nn\nn\n")

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
        shell_ops = FakeShell(installed_tools={})

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, then decline all gitignore prompts that may appear
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\nn\nn\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) not detected" in result.output
        # Verify config was saved with graphite disabled
        loaded_config = erk_installation.load_config()
        assert not loaded_config.use_graphite


def test_init_creates_global_config_even_when_repo_already_erkified() -> None:
    """Regression test: global config created even if repo has .erk/config.toml.

    Before the fix (issue #4898), when running `erk init` in a repo that already
    had a local `.erk/config.toml` but no global `~/.erk/config.toml`, the global
    config was never created. This was because global config creation was inside
    the else block that only ran when `not already_erkified`.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        # Create a repo that's already erkified (has .erk/config.toml)
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text("# existing local config", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={env.cwd, env.git_dir, erk_dir},
        )
        # No global config exists yet
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        # Key assertion: global config should be created even though repo was already erkified
        assert "Global config not found" in result.output
        assert "Created global config" in result.output
        assert erk_installation.config_exists()
        loaded = erk_installation.load_config()
        assert loaded.erk_root == erk_root.resolve()
