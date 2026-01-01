"""Tests for erk project init command (repo initialization).

This tests the repository initialization command which erk-ifies a repository
by creating .erk/ directory, config files, and syncing artifacts.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_project_init_creates_erk_directory() -> None:
    """Test that project init creates .erk directory and config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert (env.cwd / ".erk").is_dir()
        assert (env.cwd / ".erk" / "config.toml").exists()


def test_project_init_sets_required_version() -> None:
    """Test that project init creates required version file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        version_file = env.cwd / ".erk" / "required-erk-uv-tool-version"
        assert version_file.exists()
        version = version_file.read_text(encoding="utf-8").strip()
        assert version  # Should have a version string


def test_project_init_refuses_overwrite_without_force() -> None:
    """Test that project init refuses to overwrite existing config without --force."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create existing .erk/config.toml
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        (erk_dir / "config.toml").write_text("existing = true\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output.lower()


def test_project_init_with_force_overwrites_config() -> None:
    """Test that project init with --force overwrites existing config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create existing .erk/config.toml
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        (erk_dir / "config.toml").write_text("existing = true\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["project", "init", "--force", "--no-interactive"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Config should be overwritten
        content = (erk_dir / "config.toml").read_text(encoding="utf-8")
        assert "existing" not in content


def test_project_init_list_presets() -> None:
    """Test that --list-presets shows available presets."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "init", "--list-presets"], obj=test_ctx)

        assert result.exit_code == 0
        assert "presets" in result.output.lower()


def test_project_init_creates_prompt_hooks_directory() -> None:
    """Test that project init creates .erk/prompt-hooks/ directory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        prompt_hooks_dir = env.cwd / ".erk" / "prompt-hooks"
        assert prompt_hooks_dir.is_dir()


def test_project_init_shows_next_steps() -> None:
    """Test that project init shows next steps for users."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "init", "--no-interactive"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository initialized" in result.output
        assert "erk init" in result.output  # Should mention local setup
