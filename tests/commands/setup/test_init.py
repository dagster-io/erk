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
   - Uses FakeConfigStore for dependency injection
   - No mocking required - proper abstraction via ConfigStore interface
   - Tests inject FakeConfigStore with desired initial state
"""

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.cli.cli import cli
from erk.core.config_store import FakeConfigStore, GlobalConfig
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Global config not found" in result.output
        assert "Created global config" in result.output
        # Verify config was saved to in-memory ops
        assert global_config_ops.exists()
        loaded = global_config_ops.load()
        assert loaded.erk_root == erk_root.resolve()


def test_init_prompts_for_erk_root() -> None:
    """Test that init prompts for erks root when creating config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "my-erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Worktrees root directory" in result.output
        # Verify config was saved correctly to in-memory ops
        loaded_config = global_config_ops.load()
        assert loaded_config.erk_root == erk_root.resolve()


def test_init_detects_graphite_installed() -> None:
    """Test that init detects when Graphite (gt) is installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        shell_ops = FakeShell(installed_tools={"gt": "/usr/local/bin/gt"})
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            shell=shell_ops,
            config_store=global_config_ops,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) detected" in result.output
        # Verify config was saved with graphite enabled
        loaded_config = global_config_ops.load()
        assert loaded_config.use_graphite


def test_init_detects_graphite_not_installed() -> None:
    """Test that init detects when Graphite (gt) is NOT installed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) not detected" in result.output
        # Verify config was saved with graphite disabled
        loaded_config = global_config_ops.load()
        assert not loaded_config.use_graphite


def test_init_skips_global_with_repo_flag() -> None:
    """Test that --repo flag skips global config creation."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--repo"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Global config not found" not in result.output
        assert (env.cwd / "config.toml").exists()


def test_init_fails_repo_flag_without_global_config() -> None:
    """Test that --repo flag fails when global config doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist - this is the error case being tested
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--repo"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Global config not found" in result.output
        assert "Run 'erk init' without --repo" in result.output


def test_init_auto_preset_detects_dagster() -> None:
    """Test that auto preset detects dagster repo and uses dagster preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create pyproject.toml with dagster as the project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "dagster"\n', encoding="utf-8")

        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be created in erks_dir
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_dagster() -> None:
    """Test that explicit --preset dagster uses dagster preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--preset", "dagster"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_generic() -> None:
    """Test that explicit --preset generic uses generic preset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--preset", "generic"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
        assert config_path.exists()


def test_init_list_presets_displays_available() -> None:
    """Test that --list-presets displays available presets."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=env.cwd / "fake-erks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--preset", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid preset 'nonexistent'" in result.output


def test_init_creates_config_at_erks_dir() -> None:
    """Test that init creates config.toml in erks_dir by default."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be in erks_dir, not repo root
        repo_dir = erk_root / "repos" / env.cwd.name
        config_path = repo_dir / "config.toml"
        assert config_path.exists()
        assert not (env.cwd / "config.toml").exists()


def test_init_repo_flag_creates_config_at_root() -> None:
    """Test that --repo creates config.toml at repo root."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--repo"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be at repo root
        config_path = env.cwd / "config.toml"
        assert config_path.exists()


def test_init_force_overwrites_existing_config() -> None:
    """Test that --force overwrites existing config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        repo_dir = erk_root / "repos" / env.cwd.name
        repo_dir.mkdir(parents=True)

        # Create existing config
        config_path = repo_dir / "config.toml"
        config_path.write_text("# Old config\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert config_path.exists()
        # Verify content was overwritten (shouldn't contain "Old config")
        content = config_path.read_text(encoding="utf-8")
        assert "# Old config" not in content


def test_init_fails_without_force_when_exists() -> None:
    """Test that init fails when config exists without --force."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        repo_dir = erk_root / "repos" / env.cwd.name
        repo_dir.mkdir(parents=True)

        # Create existing config
        config_path = repo_dir / "config.toml"
        config_path.write_text("# Existing config\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Config already exists" in result.output
        assert "Use --force to overwrite" in result.output


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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        # Accept prompt for .env

        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".env" in gitignore_content


def test_init_skips_gitignore_entries_if_declined() -> None:
    """Test that init skips .env gitignore entry if user declines.

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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        # Decline prompt
        result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".env" not in gitignore_content


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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx)

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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
        )

        # Accept prompt for .env

        result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\n")

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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Provide input: erk_root, decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\nn\n")

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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\n",
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("zsh", zshrc)),
            dry_run=False,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\n",
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("fish", fish_config)),
            dry_run=False,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\n",
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\n")

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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Accept shell setup to see instructions
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\ny\ny\n",
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Accept shell setup to see instructions
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\ny\ny\n",
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
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(detected_shell=("bash", bashrc)),
            dry_run=False,
        )

        # Decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{erk_root}\nn\n",
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
        global_config = GlobalConfig(
            erk_root=env.cwd / "fake-erks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
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
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "n" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\nn\n")

        assert result.exit_code == 0, result.output
        assert "Shell integration instructions were displayed above" in result.output
        assert "Run 'erk init --shell' again to save this preference" in result.output
        # Config should NOT have been updated
        loaded = global_config_ops.load()
        assert loaded.shell_setup_complete is False


def test_shell_setup_confirmation_accepted_with_shell_flag() -> None:
    """Test user accepting confirmation for global config write (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        global_config_ops = FakeConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "y" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 0, result.output
        assert "✓ Global config updated" in result.output
        # Config should have been updated
        loaded = global_config_ops.load()
        assert loaded.shell_setup_complete is True


def test_shell_setup_confirmation_declined_first_init() -> None:
    """Test user declining confirmation during first-time init."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Config doesn't exist yet (first-time init)
        global_config_ops = FakeConfigStore(config=None)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Provide erk_root, decline shell setup instructions, answer confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            # Input: erk_root path, "y" for shell setup, "n" for config confirmation
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\ny\nn\n")

        assert result.exit_code == 0, result.output
        assert "Shell integration instructions were displayed above" in result.output
        # Config should exist (created by first-time init)
        assert global_config_ops.exists()
        # But shell_setup_complete should be False (user declined)
        loaded = global_config_ops.load()
        assert loaded.shell_setup_complete is False


def test_shell_setup_permission_error_with_shell_flag() -> None:
    """Test permission error handling when saving global config (--shell flag)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            erk_root=erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        # Create a ConfigStore that raises PermissionError on save
        class PermissionErrorConfigStore(FakeConfigStore):
            def save(self, config: GlobalConfig) -> None:
                raise PermissionError(
                    f"Cannot write to file: {self.path()}\n"
                    "The file exists but is not writable.\n\n"
                    "To fix this manually:\n"
                    "  1. Make it writable: chmod 644 {self.path()}\n"
                    "  2. Run erk init --shell again"
                )

        global_config_ops = PermissionErrorConfigStore(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=global_config,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Answer "y" to shell setup, then "y" to config write confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 1, result.output
        assert "❌ Error: Could not save global config" in result.output
        assert "Cannot write to file" in result.output
        assert "Shell integration instructions were displayed above" in result.output
        assert "You can use them now - erk just couldn't save this preference" in result.output


def test_shell_setup_permission_error_first_init() -> None:
    """Test permission error handling during first-time init (doesn't exit)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        # Create a ConfigStore that allows first save but fails on second
        class ConditionalPermissionErrorOps(FakeConfigStore):
            def __init__(self) -> None:
                super().__init__(config=None)
                self.save_count = 0

            def save(self, config: GlobalConfig) -> None:
                self.save_count += 1
                if self.save_count == 1:
                    # First save (creating global config) succeeds
                    super().save(config)
                else:
                    # Second save (shell setup update) fails
                    raise PermissionError(
                        f"Cannot write to file: {self.path()}\n"
                        "Permission denied during write operation."
                    )

        global_config_ops = ConditionalPermissionErrorOps()

        test_ctx = env.build_context(
            git=git_ops,
            config_store=global_config_ops,
            global_config=None,
            shell=FakeShell(detected_shell=("bash", bashrc)),
        )

        # Input: erk_root path, "y" for shell setup, "y" for config confirmation
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\ny\ny\n")

        # Should NOT exit with error code (first-time init continues)
        assert result.exit_code == 0, result.output
        assert "❌ Error: Could not save global config" in result.output
        assert "Cannot write to file" in result.output
        assert "Shell integration instructions were displayed above" in result.output
        # First save succeeded, second failed
        assert global_config_ops.save_count == 2
