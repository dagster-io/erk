"""Tests for erk project upgrade command.

This tests the upgrade command which updates repository to a new erk version
by updating the required version file and force-syncing artifacts.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_project_upgrade_fails_when_not_erk_ified() -> None:
    """Test that upgrade fails when repo is not erk-ified."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # No .erk directory
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "upgrade"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not erk-ified" in result.output.lower() or "project init" in result.output.lower()


def test_project_upgrade_updates_version_file() -> None:
    """Test that upgrade updates the required version file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create erk-ified repo with old version
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.1.0\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "upgrade"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Version file should be updated
        new_version = version_file.read_text(encoding="utf-8").strip()
        assert new_version != "0.1.0"  # Should be updated to current version


def test_project_upgrade_skips_when_version_matches() -> None:
    """Test that upgrade skips when versions already match."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        from erk.core.release_notes import get_current_version

        # Create erk-ified repo with current version
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        current_version = get_current_version()
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text(f"{current_version}\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "upgrade"], obj=test_ctx)

        assert result.exit_code == 0
        assert "already at version" in result.output.lower()


def test_project_upgrade_with_force_syncs_even_when_version_matches() -> None:
    """Test that --force syncs artifacts even when versions match."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        from erk.core.release_notes import get_current_version

        # Create erk-ified repo with current version
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        current_version = get_current_version()
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text(f"{current_version}\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "upgrade", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should have attempted artifact sync
        assert "upgrade complete" in result.output.lower()


def test_project_upgrade_shows_completion_message() -> None:
    """Test that upgrade shows completion message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create erk-ified repo with old version
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.1.0\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "upgrade"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "upgrade complete" in result.output.lower()


def test_project_upgrade_shows_next_steps() -> None:
    """Test that upgrade shows next steps for users."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create erk-ified repo with old version
        erk_dir = env.cwd / ".erk"
        erk_dir.mkdir()
        version_file = erk_dir / "required-erk-uv-tool-version"
        version_file.write_text("0.1.0\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["project", "upgrade"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "commit" in result.output.lower()  # Should mention committing changes
