"""Tests for artifact CLI commands."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.artifact.check import check_cmd
from erk.cli.commands.artifact.list_cmd import list_cmd
from erk.cli.commands.artifact.show import show_cmd
from erk.cli.commands.artifact.sync_cmd import sync_cmd


class TestListCommand:
    """Tests for erk artifact list."""

    def test_list_no_claude_dir(self, tmp_path: Path) -> None:
        """Exits with error when .claude/ doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(list_cmd)

        assert result.exit_code == 1
        assert "No .claude/ directory found" in result.output

    def test_list_empty(self, tmp_path: Path) -> None:
        """Shows no artifacts found when directory is empty."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".claude").mkdir()
            result = runner.invoke(list_cmd)

        assert result.exit_code == 0
        assert "No artifacts found" in result.output

    def test_list_shows_artifacts(self, tmp_path: Path) -> None:
        """Lists discovered artifacts."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            skill_dir = Path(".claude/skills/test-skill")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

            result = runner.invoke(list_cmd)

        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_list_filters_by_type(self, tmp_path: Path) -> None:
        """Filters artifacts by type."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create skill
            skill_dir = Path(".claude/skills/test-skill")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Test", encoding="utf-8")

            # Create command
            cmd_dir = Path(".claude/commands/local")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "test-cmd.md").write_text("# Cmd", encoding="utf-8")

            result = runner.invoke(list_cmd, ["--type", "skill"])

        assert result.exit_code == 0
        assert "test-skill" in result.output
        assert "test-cmd" not in result.output


class TestShowCommand:
    """Tests for erk artifact show."""

    def test_show_no_claude_dir(self, tmp_path: Path) -> None:
        """Exits with error when .claude/ doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(show_cmd, ["nonexistent"])

        assert result.exit_code == 1
        assert "No .claude/ directory found" in result.output

    def test_show_artifact_not_found(self, tmp_path: Path) -> None:
        """Exits with error when artifact not found."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".claude").mkdir()
            result = runner.invoke(show_cmd, ["nonexistent"])

        assert result.exit_code == 1
        assert "Artifact not found" in result.output

    def test_show_displays_content(self, tmp_path: Path) -> None:
        """Displays artifact content."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            skill_dir = Path(".claude/skills/test-skill")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# My Test Skill Content", encoding="utf-8")

            result = runner.invoke(show_cmd, ["test-skill"])

        assert result.exit_code == 0
        assert "test-skill" in result.output
        assert "My Test Skill Content" in result.output


class TestCheckCommand:
    """Tests for erk artifact check."""

    def test_check_not_initialized(self, tmp_path: Path) -> None:
        """Shows not initialized when no state."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 1
        assert "not initialized" in result.output

    def test_check_version_mismatch(self, tmp_path: Path) -> None:
        """Shows mismatch when versions differ."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "0.9.0"\n', encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 1
        assert "out of sync" in result.output

    def test_check_up_to_date(self, tmp_path: Path) -> None:
        """Shows up to date when versions match."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "1.0.0"\n', encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_check_erk_repo(self, tmp_path: Path) -> None:
        """Shows development mode when in erk repo."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "Development mode" in result.output


class TestSyncCommand:
    """Tests for erk artifact sync."""

    def test_sync_in_erk_repo(self, tmp_path: Path) -> None:
        """Skips sync when in erk repo."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            result = runner.invoke(sync_cmd)

        assert result.exit_code == 0
        assert "Skipped" in result.output

    def test_sync_bundled_not_found(self, tmp_path: Path) -> None:
        """Fails when bundled .claude/ not found."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "erk.artifacts.sync.get_bundled_claude_dir",
                return_value=Path("/nonexistent"),
            ):
                result = runner.invoke(sync_cmd)

        assert result.exit_code == 1
        assert "not found" in result.output
