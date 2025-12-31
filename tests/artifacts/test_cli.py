"""Tests for artifact CLI commands."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.artifacts.models import InstalledArtifact
from erk.cli.commands.artifact.check import check_cmd
from erk.cli.commands.artifact.list_cmd import _is_erk_managed, list_cmd
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

    def test_list_shows_erk_indicator_for_erk_command(self, tmp_path: Path) -> None:
        """Shows [erk] badge for erk: prefixed commands."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            cmd_dir = Path(".claude/commands/erk")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "plan-implement.md").write_text("# Cmd", encoding="utf-8")

            result = runner.invoke(list_cmd, color=True)

        assert result.exit_code == 0
        assert "erk:plan-implement" in result.output
        assert "[erk]" in result.output

    def test_list_shows_erk_indicator_for_bundled_skill(self, tmp_path: Path) -> None:
        """Shows [erk] badge for bundled skills."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            skill_dir = Path(".claude/skills/dignified-python")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            result = runner.invoke(list_cmd, color=True)

        assert result.exit_code == 0
        assert "dignified-python" in result.output
        assert "[erk]" in result.output

    def test_list_shows_erk_indicator_for_bundled_agent(self, tmp_path: Path) -> None:
        """Shows [erk] badge for bundled agents."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            agent_dir = Path(".claude/agents/devrun")
            agent_dir.mkdir(parents=True)
            # Agent discovery expects <agent-name>/<agent-name>.md pattern
            (agent_dir / "devrun.md").write_text("# Agent", encoding="utf-8")

            result = runner.invoke(list_cmd, color=True)

        assert result.exit_code == 0
        assert "devrun" in result.output
        assert "[erk]" in result.output

    def test_list_shows_local_badge_for_local_artifacts(self, tmp_path: Path) -> None:
        """Shows [local] badge for local/user-defined artifacts."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Local command
            cmd_dir = Path(".claude/commands/local")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "my-cmd.md").write_text("# Cmd", encoding="utf-8")

            # Custom skill (not in BUNDLED_SKILLS)
            skill_dir = Path(".claude/skills/my-skill")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            result = runner.invoke(list_cmd, color=True)

        assert result.exit_code == 0
        assert "local:my-cmd" in result.output
        assert "my-skill" in result.output
        # Both should show [local] badge, not [erk]
        assert "[local]" in result.output
        assert result.output.count("[local]") == 2  # Both artifacts


class TestIsErkManaged:
    """Tests for _is_erk_managed helper function."""

    def test_erk_command_is_managed(self) -> None:
        """Commands with erk: prefix are erk-managed."""
        artifact = InstalledArtifact(
            name="erk:plan-implement",
            artifact_type="command",
            path=Path(".claude/commands/erk/plan-implement.md"),
            content_hash=None,
        )
        assert _is_erk_managed(artifact) is True

    def test_local_command_not_managed(self) -> None:
        """Commands with local: prefix are not erk-managed."""
        artifact = InstalledArtifact(
            name="local:my-cmd",
            artifact_type="command",
            path=Path(".claude/commands/local/my-cmd.md"),
            content_hash=None,
        )
        assert _is_erk_managed(artifact) is False

    def test_bundled_skill_is_managed(self) -> None:
        """Skills in BUNDLED_SKILLS are erk-managed."""
        artifact = InstalledArtifact(
            name="dignified-python",
            artifact_type="skill",
            path=Path(".claude/skills/dignified-python"),
            content_hash=None,
        )
        assert _is_erk_managed(artifact) is True

    def test_custom_skill_not_managed(self) -> None:
        """Skills not in BUNDLED_SKILLS are not erk-managed."""
        artifact = InstalledArtifact(
            name="my-custom-skill",
            artifact_type="skill",
            path=Path(".claude/skills/my-custom-skill"),
            content_hash=None,
        )
        assert _is_erk_managed(artifact) is False

    def test_bundled_agent_is_managed(self) -> None:
        """Agents in BUNDLED_AGENTS are erk-managed."""
        artifact = InstalledArtifact(
            name="devrun",
            artifact_type="agent",
            path=Path(".claude/agents/devrun"),
            content_hash=None,
        )
        assert _is_erk_managed(artifact) is True

    def test_custom_agent_not_managed(self) -> None:
        """Agents not in BUNDLED_AGENTS are not erk-managed."""
        artifact = InstalledArtifact(
            name="my-agent",
            artifact_type="agent",
            path=Path(".claude/agents/my-agent"),
            content_hash=None,
        )
        assert _is_erk_managed(artifact) is False


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
        """Shows up to date when versions match and no orphans."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "1.0.0"\n', encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.orphans.get_bundled_claude_dir",
                    return_value=Path("/nonexistent"),
                ):
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

    def test_check_erk_repo_shows_bundled_artifacts(self, tmp_path: Path) -> None:
        """Shows bundled artifacts list in development mode."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            # Create bundled directory with commands
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")
            (bundled_commands / "pr-submit.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.cli.commands.artifact.check.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "Development mode" in result.output
        # Verify bundled agents are shown (from BUNDLED_AGENTS constant)
        assert "agents/devrun" in result.output
        # Verify bundled skills are shown (from BUNDLED_SKILLS constant)
        assert "skills/dignified-python" in result.output
        assert "skills/learned-docs" in result.output
        # Verify bundled commands are shown (from mocked directory)
        assert "commands/erk/plan-implement.md" in result.output
        assert "commands/erk/pr-submit.md" in result.output

    def test_check_up_to_date_shows_bundled_artifacts(self, tmp_path: Path) -> None:
        """Shows bundled artifacts list when artifacts are up to date."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "1.0.0"\n', encoding="utf-8")

            # Create bundled directory with commands
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "auto-restack.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.orphans.get_bundled_claude_dir",
                    return_value=Path("/nonexistent"),
                ):
                    with patch(
                        "erk.cli.commands.artifact.check.get_bundled_claude_dir",
                        return_value=bundled_dir,
                    ):
                        result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "up to date" in result.output
        # Verify bundled agents are shown
        assert "agents/devrun" in result.output
        # Verify bundled skills are shown
        assert "skills/dignified-python" in result.output
        # Verify bundled commands are shown
        assert "commands/erk/auto-restack.md" in result.output

    def test_check_version_mismatch_does_not_show_artifacts(self, tmp_path: Path) -> None:
        """Does NOT show bundled artifacts when version is mismatched."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version mismatch
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "0.9.0"\n', encoding="utf-8")

            # Create bundled directory with commands
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.cli.commands.artifact.check.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    result = runner.invoke(check_cmd)

        assert result.exit_code == 1
        assert "out of sync" in result.output
        # Should NOT show bundled artifacts when version is mismatched
        assert "agents/devrun" not in result.output
        assert "commands/erk/plan-implement.md" not in result.output

    def test_check_with_orphans(self, tmp_path: Path) -> None:
        """Shows orphaned artifacts and fails when orphans found."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "1.0.0"\n', encoding="utf-8")

            # Create bundled directory with one command
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

            # Create .claude/ with orphaned command
            project_claude = Path(".claude")
            project_commands = project_claude / "commands" / "erk"
            project_commands.mkdir(parents=True)
            (project_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")
            (project_commands / "orphaned.md").write_text("# Orphan", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.orphans.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    result = runner.invoke(check_cmd)

        assert result.exit_code == 1
        assert "up to date" in result.output
        assert "orphaned artifact" in result.output
        assert "orphaned.md" in result.output
        assert "rm .claude/commands/erk/orphaned.md" in result.output

    def test_check_no_orphans(self, tmp_path: Path) -> None:
        """Shows no orphaned artifacts when none found."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text('[artifacts]\nversion = "1.0.0"\n', encoding="utf-8")

            # Create bundled directory
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

            # Create .claude/ with same files (no orphans)
            project_claude = Path(".claude")
            project_commands = project_claude / "commands" / "erk"
            project_commands.mkdir(parents=True)
            (project_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.orphans.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "up to date" in result.output
        assert "No orphaned artifacts" in result.output


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
