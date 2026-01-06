"""Unit tests for admin upgrade-repo command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_upgrade_repo_writes_version_file() -> None:
    """Test that upgrade-repo writes the version file correctly."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory where version file will be written
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)

        ctx = env.build_context()

        result = runner.invoke(cli, ["admin", "upgrade-repo"], obj=ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Version file should exist and contain a version string
        version_file = erk_dir / "required-erk-uv-tool-version"
        assert version_file.exists(), "Version file should be created"

        version_content = version_file.read_text(encoding="utf-8").strip()
        # Version should match expected format (e.g., "0.4.0")
        assert version_content, "Version file should not be empty"
        # Basic format check: should contain at least one dot (e.g., "0.4.0")
        assert "." in version_content, f"Version should contain dot: {version_content}"


def test_upgrade_repo_outputs_next_steps() -> None:
    """Test that upgrade-repo outputs next steps instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)

        ctx = env.build_context()

        result = runner.invoke(cli, ["admin", "upgrade-repo"], obj=ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Output should contain next steps
        assert "Next steps" in result.output
        assert "erk artifact sync" in result.output
        assert "erk doctor" in result.output


def test_upgrade_repo_outputs_updated_version_message() -> None:
    """Test that upgrade-repo outputs a message about the updated version."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create .erk directory
        erk_dir = env.root_worktree / ".erk"
        erk_dir.mkdir(parents=True)

        ctx = env.build_context()

        result = runner.invoke(cli, ["admin", "upgrade-repo"], obj=ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Output should contain update confirmation
        assert "Updated required version to" in result.output


def test_upgrade_repo_fails_without_erk_directory() -> None:
    """Test that upgrade-repo fails with clear error when .erk directory is missing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Intentionally do NOT create .erk directory

        ctx = env.build_context()

        result = runner.invoke(cli, ["admin", "upgrade-repo"], obj=ctx)

        # Should fail with exit code 1
        assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"

        # Output should contain the error message
        assert "Not an erk-managed repository" in result.output
