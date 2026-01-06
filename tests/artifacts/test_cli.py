"""Tests for artifact CLI commands."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.artifacts.artifact_health import is_erk_managed
from erk.artifacts.models import InstalledArtifact
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

    def test_list_shows_erk_indicator_for_erk_command(self, tmp_path: Path) -> None:
        """Shows [erk] badge for erk: prefixed commands."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            cmd_dir = Path(".claude/commands/erk/system")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "impl-execute.md").write_text("# Cmd", encoding="utf-8")

            result = runner.invoke(list_cmd, color=True)

        assert result.exit_code == 0
        assert "erk:system:impl-execute" in result.output
        assert "[erk]" in result.output

    def test_list_shows_erk_indicator_for_bundled_skill(self, tmp_path: Path) -> None:
        """Shows [erk] badge for bundled skills."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            skill_dir = Path(".claude/skills/learned-docs")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            result = runner.invoke(list_cmd, color=True)

        assert result.exit_code == 0
        assert "learned-docs" in result.output
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

    def test_list_shows_unmanaged_badge_for_local_artifacts(self, tmp_path: Path) -> None:
        """Shows [unmanaged] badge for local/user-defined artifacts."""
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
        # Both should show [unmanaged] badge, not [erk]
        assert "[unmanaged]" in result.output
        assert result.output.count("[unmanaged]") == 2  # Both artifacts


class TestIsErkManaged:
    """Tests for is_erk_managed helper function."""

    def test_erk_command_is_managed(self) -> None:
        """Commands with erk: prefix are erk-managed."""
        artifact = InstalledArtifact(
            name="erk:system:impl-execute",
            artifact_type="command",
            path=Path(".claude/commands/erk/plan-implement.md"),
            content_hash=None,
        )
        assert is_erk_managed(artifact) is True

    def test_local_command_not_managed(self) -> None:
        """Commands with local: prefix are not erk-managed."""
        artifact = InstalledArtifact(
            name="local:my-cmd",
            artifact_type="command",
            path=Path(".claude/commands/local/my-cmd.md"),
            content_hash=None,
        )
        assert is_erk_managed(artifact) is False

    def test_bundled_skill_is_managed(self) -> None:
        """Skills in BUNDLED_SKILLS are erk-managed."""
        artifact = InstalledArtifact(
            name="learned-docs",
            artifact_type="skill",
            path=Path(".claude/skills/learned-docs"),
            content_hash=None,
        )
        assert is_erk_managed(artifact) is True

    def test_custom_skill_not_managed(self) -> None:
        """Skills not in BUNDLED_SKILLS are not erk-managed."""
        artifact = InstalledArtifact(
            name="my-custom-skill",
            artifact_type="skill",
            path=Path(".claude/skills/my-custom-skill"),
            content_hash=None,
        )
        assert is_erk_managed(artifact) is False

    def test_bundled_agent_is_managed(self) -> None:
        """Agents in BUNDLED_AGENTS are erk-managed."""
        artifact = InstalledArtifact(
            name="devrun",
            artifact_type="agent",
            path=Path(".claude/agents/devrun"),
            content_hash=None,
        )
        assert is_erk_managed(artifact) is True

    def test_custom_agent_not_managed(self) -> None:
        """Agents not in BUNDLED_AGENTS are not erk-managed."""
        artifact = InstalledArtifact(
            name="my-agent",
            artifact_type="agent",
            path=Path(".claude/agents/my-agent"),
            content_hash=None,
        )
        assert is_erk_managed(artifact) is False


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
            state_file.write_text(
                '[artifacts]\nversion = "0.9.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

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
            state_file.write_text(
                '[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.artifact_health.get_bundled_claude_dir",
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

    def test_check_erk_repo_shows_installed_artifacts(self, tmp_path: Path) -> None:
        """Shows installed artifacts list in development mode."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            # Create actual .claude directory with installed artifacts
            agent_dir = Path(".claude/agents/devrun")
            agent_dir.mkdir(parents=True)
            (agent_dir / "devrun.md").write_text("# Agent", encoding="utf-8")

            skill_dir = Path(".claude/skills/learned-docs")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            cmd_dir = Path(".claude/commands/erk")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "plan-implement.md").write_text("# Command", encoding="utf-8")
            (cmd_dir / "pr-submit.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "Development mode" in result.output
        # Verify installed artifacts are shown
        assert "agents/devrun" in result.output
        assert "skills/learned-docs" in result.output
        assert "commands/erk/plan-implement.md" in result.output
        assert "commands/erk/pr-submit.md" in result.output

    def test_check_up_to_date_shows_installed_artifacts(self, tmp_path: Path) -> None:
        """Shows installed artifacts list when artifacts are up to date."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                '[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

            # Create actual .claude directory with installed artifacts
            agent_dir = Path(".claude/agents/devrun")
            agent_dir.mkdir(parents=True)
            (agent_dir / "devrun.md").write_text("# Agent", encoding="utf-8")

            skill_dir = Path(".claude/skills/learned-docs")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            cmd_dir = Path(".claude/commands/erk")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "auto-restack.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.artifact_health.get_bundled_claude_dir",
                    return_value=Path("/nonexistent"),
                ):
                    result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "up to date" in result.output
        # Verify installed artifacts are shown
        assert "agents/devrun" in result.output
        assert "skills/learned-docs" in result.output
        assert "commands/erk/auto-restack.md" in result.output

    def test_check_version_mismatch_does_not_show_artifacts(self, tmp_path: Path) -> None:
        """Does NOT show artifacts when version is mismatched."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version mismatch
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                '[artifacts]\nversion = "0.9.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

            # Create actual .claude directory with installed artifacts
            agent_dir = Path(".claude/agents/devrun")
            agent_dir.mkdir(parents=True)
            (agent_dir / "devrun.md").write_text("# Agent", encoding="utf-8")

            cmd_dir = Path(".claude/commands/erk/system")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "impl-execute.md").write_text("# Command", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 1
        assert "out of sync" in result.output
        # Should NOT show artifacts when version is mismatched
        assert "agents/devrun" not in result.output
        assert "commands/erk/system/impl-execute.md" not in result.output

    def test_check_with_orphans(self, tmp_path: Path) -> None:
        """Shows orphaned artifacts and fails when orphans found."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                '[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

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
                    "erk.artifacts.artifact_health.get_bundled_claude_dir",
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
        import json

        from erk.core.claude_settings import add_erk_hooks

        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                '[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

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

            # Add settings.json with hooks to avoid missing hooks
            settings = add_erk_hooks({})
            (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

            # Create bundled github dir (empty, no workflows)
            bundled_github = tmp_path / "bundled" / ".github"
            bundled_github.mkdir(parents=True)

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.artifact_health.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    with patch(
                        "erk.artifacts.artifact_health.get_bundled_github_dir",
                        return_value=bundled_github,
                    ):
                        result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "up to date" in result.output
        assert "No orphaned artifacts" in result.output


class TestSyncCommand:
    """Tests for erk artifact sync."""

    def test_sync_in_erk_repo(self, tmp_path: Path) -> None:
        """Updates state when in erk repo (development mode)."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            result = runner.invoke(sync_cmd)

        assert result.exit_code == 0
        assert "Development mode" in result.output

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


class TestCheckCommandShowsActualArtifacts:
    """Tests for ensuring check shows only actually-installed artifacts."""

    def test_check_shows_only_existing_artifacts(self, tmp_path: Path) -> None:
        """Check should only show artifacts that actually exist in project .claude/.

        Bug: _display_bundled_artifacts() lists artifacts from BUNDLED_AGENTS/SKILLS
        constants without verifying they exist in the target .claude/ directory.
        This causes false positives where it claims agents/devrun exists when it
        doesn't.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name (triggers dev mode)
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            # Create .claude with ONLY a skill, no agents
            skill_dir = Path(".claude/skills/learned-docs")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Dignified Python", encoding="utf-8")

            # No agents directory at all
            # The old bug would still list "agents/devrun" from BUNDLED_AGENTS

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd)

        assert result.exit_code == 0
        assert "Development mode" in result.output
        # Should show the skill that exists
        assert "skills/learned-docs" in result.output
        # Should NOT show agents/devrun - it doesn't exist in .claude/
        assert "agents/devrun" not in result.output


class TestCheckVerboseShowsBothArtifactTypes:
    """Tests for verbose mode showing both erk-managed and project artifacts."""

    def test_verbose_shows_erk_managed_and_project_artifacts(self, tmp_path: Path) -> None:
        """Verbose mode shows both erk-managed artifacts with status and project artifacts.

        Note: Exit code may be non-zero due to missing bundled artifacts (skills, hooks).
        This test verifies the output format, not sync status.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                '[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

            # Create bundled directory with one command
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

            # Create .claude/ with both erk-managed and project artifacts
            project_claude = Path(".claude")
            project_commands_erk = project_claude / "commands" / "erk"
            project_commands_erk.mkdir(parents=True)
            (project_commands_erk / "plan-implement.md").write_text("# Command", encoding="utf-8")

            # Project-specific artifacts (local commands)
            project_commands_local = project_claude / "commands" / "local"
            project_commands_local.mkdir(parents=True)
            (project_commands_local / "my-command.md").write_text("# Local", encoding="utf-8")

            # Project-specific skill
            skill_dir = project_claude / "skills" / "my-custom-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Custom", encoding="utf-8")

            # Create bundled github dir (empty, no workflows)
            bundled_github = tmp_path / "bundled" / ".github"
            bundled_github.mkdir(parents=True)

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.artifact_health.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    with patch(
                        "erk.artifacts.artifact_health.get_bundled_github_dir",
                        return_value=bundled_github,
                    ):
                        result = runner.invoke(check_cmd, ["-v"])

        # Verify verbose output has both sections
        assert "Erk-managed artifacts:" in result.output
        assert "Project artifacts (unmanaged):" in result.output
        # Should show project artifacts
        assert "commands/local/my-command.md" in result.output
        assert "skills/my-custom-skill" in result.output

    def test_verbose_without_project_artifacts_omits_section(self, tmp_path: Path) -> None:
        """Verbose mode omits Project artifacts section when none exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Set up version as up-to-date
            state_file = Path(".erk/state.toml")
            state_file.parent.mkdir(parents=True)
            state_file.write_text(
                '[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8"
            )

            # Create bundled directory with one command
            bundled_dir = tmp_path / "bundled" / ".claude"
            bundled_commands = bundled_dir / "commands" / "erk"
            bundled_commands.mkdir(parents=True)
            (bundled_commands / "plan-implement.md").write_text("# Command", encoding="utf-8")

            # Only erk-managed artifacts, no project-specific ones
            project_claude = Path(".claude")
            project_commands_erk = project_claude / "commands" / "erk"
            project_commands_erk.mkdir(parents=True)
            (project_commands_erk / "plan-implement.md").write_text("# Command", encoding="utf-8")

            # Create bundled github dir (empty, no workflows)
            bundled_github = tmp_path / "bundled" / ".github"
            bundled_github.mkdir(parents=True)

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                with patch(
                    "erk.artifacts.artifact_health.get_bundled_claude_dir",
                    return_value=bundled_dir,
                ):
                    with patch(
                        "erk.artifacts.artifact_health.get_bundled_github_dir",
                        return_value=bundled_github,
                    ):
                        result = runner.invoke(check_cmd, ["-v"])

        assert "Erk-managed artifacts:" in result.output
        # Project artifacts section should be omitted when no project artifacts exist
        assert "Project artifacts (unmanaged):" not in result.output

    def test_verbose_dev_mode_shows_both_sections(self, tmp_path: Path) -> None:
        """Verbose mode in dev repo shows both erk-managed and project artifacts."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create pyproject.toml with erk name (triggers dev mode)
            Path("pyproject.toml").write_text('[project]\nname = "erk"\n', encoding="utf-8")

            # Create .claude/ with bundled skill
            skill_dir = Path(".claude/skills/learned-docs")
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

            # Project-specific command
            cmd_dir = Path(".claude/commands/local")
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "my-local-cmd.md").write_text("# Local", encoding="utf-8")

            with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
                result = runner.invoke(check_cmd, ["-v"])

        # Dev mode always succeeds
        assert result.exit_code == 0
        assert "Development mode" in result.output
        assert "Erk-managed artifacts:" in result.output
        assert "Project artifacts (unmanaged):" in result.output
        assert "commands/local/my-local-cmd.md" in result.output
