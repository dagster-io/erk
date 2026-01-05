"""Tests for project setup (config location, force, stepped flow, git repo).

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
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


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
