"""Tests for global config creation during init.

Mock Usage Policy:
------------------
This file uses minimal mocking for external boundaries:

1. os.environ HOME patches:
   - LEGITIMATE: Testing path resolution logic that depends on $HOME
   - The init command uses Path.home() to determine ~/.erk location
   - erk_isolated_fs_env(env_overrides={"HOME": ...}) redirects to temp directory for test isolation
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
from erk_shared.gateway.git.fake import FakeGit
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_init_creates_global_config_first_time() -> None:
    """Test that init creates global config on first run."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides={"HOME": "{root_worktree}"}) as env:
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
    with erk_isolated_fs_env(runner, env_overrides={"HOME": "{root_worktree}"}) as env:
        erk_root = env.cwd / "my-erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert ".erk folder" in result.output
        # Verify config was saved correctly to in-memory ops
        loaded_config = erk_installation.load_config()
        assert loaded_config.erk_root == erk_root.resolve()


def test_init_detects_graphite_installed() -> None:
    """Test that init detects when Graphite (gt) is installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides={"HOME": "{root_worktree}"}) as env:
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

        result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) detected" in result.output
        # Verify config was saved with graphite enabled
        loaded_config = erk_installation.load_config()
        assert loaded_config.use_graphite


def test_init_detects_graphite_not_installed() -> None:
    """Test that init detects when Graphite (gt) is NOT installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides={"HOME": "{root_worktree}"}) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

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
    with erk_isolated_fs_env(runner, env_overrides={"HOME": "{root_worktree}"}) as env:
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

        result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        # Key assertion: global config should be created even though repo was already erkified
        assert "Global config not found" in result.output
        assert "Created global config" in result.output
        assert erk_installation.config_exists()
        loaded = erk_installation.load_config()
        assert loaded.erk_root == erk_root.resolve()


def test_init_detects_both_backends_defaults_claude() -> None:
    """Both claude and codex installed, defaults to claude without prompting."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(
            installed_tools={"claude": "/usr/bin/claude", "codex": "/usr/bin/codex"}
        )
        erk_installation = FakeErkInstallation(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            erk_installation=erk_installation,
            global_config=None,
        )

        # Input: erk_root, decline hooks (no backend prompt)
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Detected: claude" in result.output
        assert "Detected: codex" in result.output
        loaded = erk_installation.load_config()
        assert loaded.interactive_agent.backend == "claude"


def test_init_detects_only_codex_defaults_claude() -> None:
    """Only codex installed, still defaults to claude."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={"codex": "/usr/bin/codex"})
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
        assert "Detected: codex" in result.output
        assert "Backend: claude" in result.output
        loaded = erk_installation.load_config()
        assert loaded.interactive_agent.backend == "claude"


def test_init_detects_only_claude_uses_it() -> None:
    """Only claude installed, defaults to claude."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={"claude": "/usr/bin/claude"})
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
        assert "Detected: claude" in result.output
        assert "Backend: claude" in result.output
        loaded = erk_installation.load_config()
        assert loaded.interactive_agent.backend == "claude"


def test_init_detects_no_backends_defaults_claude() -> None:
    """Neither backend installed, defaults to claude with warning."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={})
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
        assert "No agent backends detected" in result.output
        assert "Defaulting to claude" in result.output
        loaded = erk_installation.load_config()
        assert loaded.interactive_agent.backend == "claude"


def test_init_backend_persisted_in_config() -> None:
    """Verify backend is saved to config as claude regardless of detected backends."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={"codex": "/usr/bin/codex"})
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
        # Verify backend was persisted as claude (always default)
        assert len(erk_installation.saved_configs) == 1
        saved = erk_installation.saved_configs[0]
        assert saved.interactive_agent.backend == "claude"


def test_init_shows_config_switch_hint() -> None:
    """Verify init output contains hint about switching backend via config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={"claude": "/usr/bin/claude"})
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
        assert "erk config set interactive_claude.backend" in result.output
