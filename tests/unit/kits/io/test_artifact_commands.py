"""Tests for artifact CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.artifact.group import artifact_group


@pytest.fixture
def setup_test_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    """Set up test artifacts in user and project directories."""
    # Create user-level artifacts
    user_claude = tmp_path / "user" / ".claude"

    user_skill_dir = user_claude / "skills" / "user-skill"
    user_skill_dir.mkdir(parents=True)
    (user_skill_dir / "SKILL.md").write_text("# User Skill\n\nUser skill content", encoding="utf-8")

    user_commands_dir = user_claude / "commands"
    user_commands_dir.mkdir(parents=True)
    (user_commands_dir / "user-cmd.md").write_text("# User Command", encoding="utf-8")

    # Create project-level artifacts
    project_claude = tmp_path / "project" / ".claude"

    project_skill_dir = project_claude / "skills" / "project-skill"
    project_skill_dir.mkdir(parents=True)
    (project_skill_dir / "SKILL.md").write_text(
        "# Project Skill\n\nProject skill content", encoding="utf-8"
    )

    project_agents_dir = project_claude / "agents"
    project_agents_dir.mkdir(parents=True)
    (project_agents_dir / "project-agent.md").write_text("# Project Agent", encoding="utf-8")

    # Create project config
    project_dir = tmp_path / "project"
    erk_dir = project_dir / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_file = erk_dir / "kits.toml"
    config_file.write_text("[kits]\n# Empty config", encoding="utf-8")

    return user_claude, project_claude


def test_artifact_list_all(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact list command shows all artifacts."""
    user_claude, project_claude = setup_test_artifacts

    # Mock paths
    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list"])

    assert result.exit_code == 0
    # Should show artifacts from both levels
    assert "user-skill" in result.output
    assert "user-cmd" in result.output
    assert "project-skill" in result.output
    assert "project-agent" in result.output


def test_artifact_list_user_only(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact list with --user filter."""
    user_claude, project_claude = setup_test_artifacts

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list", "--user"])

    assert result.exit_code == 0
    # Should show only user artifacts
    assert "user-skill" in result.output
    assert "user-cmd" in result.output
    # Should NOT show project artifacts
    assert "project-skill" not in result.output
    assert "project-agent" not in result.output


def test_artifact_list_project_only(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact list with --project filter."""
    user_claude, project_claude = setup_test_artifacts

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list", "--project"])

    assert result.exit_code == 0
    # Should show only project artifacts
    assert "project-skill" in result.output
    assert "project-agent" in result.output
    # Should NOT show user artifacts
    assert "user-skill" not in result.output
    assert "user-cmd" not in result.output


def test_artifact_list_type_filter(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact list with --type filter."""
    user_claude, project_claude = setup_test_artifacts

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list", "--type", "skill"])

    assert result.exit_code == 0
    # Should show only skills
    assert "user-skill" in result.output
    assert "project-skill" in result.output
    # Should NOT show other types
    assert "user-cmd" not in result.output
    assert "project-agent" not in result.output


def test_artifact_list_managed_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test artifact list with --managed filter."""
    # Create user and project directories
    user_claude = tmp_path / "user" / ".claude"
    project_claude = tmp_path / "project" / ".claude"

    # Create managed artifact (from a kit)
    managed_skill_dir = project_claude / "skills" / "kit-skill"
    managed_skill_dir.mkdir(parents=True)
    (managed_skill_dir / "SKILL.md").write_text("# Kit Skill\n\nManaged skill", encoding="utf-8")

    # Create local artifact (not from a kit)
    local_skill_dir = project_claude / "skills" / "local-skill"
    local_skill_dir.mkdir(parents=True)
    (local_skill_dir / "SKILL.md").write_text("# Local Skill\n\nLocal skill", encoding="utf-8")

    # Create project config with managed artifact tracked
    project_dir = tmp_path / "project"
    erk_dir = project_dir / ".erk"
    erk_dir.mkdir(exist_ok=True)
    config_file = erk_dir / "kits.toml"
    config_file.write_text(
        """
[kits.test-kit]
kit_id = "test-kit"
source_type = "bundled"
version = "1.0.0"
artifacts = ["skills/kit-skill/SKILL.md"]
""",
        encoding="utf-8",
    )

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list", "--managed"])

    assert result.exit_code == 0
    # Should show only managed artifacts
    assert "kit-skill" in result.output
    # Should NOT show local artifacts
    assert "local-skill" not in result.output


def test_artifact_list_verbose(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact list with --verbose flag."""
    user_claude, project_claude = setup_test_artifacts

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list", "-v"])

    assert result.exit_code == 0
    # Verbose should include metadata
    assert "user-skill" in result.output
    # New format uses type groupings and Path: labels
    assert "Skills:" in result.output or "Path:" in result.output


def test_artifact_list_no_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test artifact list with no artifacts found."""
    # Create empty directories
    user_claude = tmp_path / "user" / ".claude"
    user_claude.mkdir(parents=True)

    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    project_dir = tmp_path / "project"
    config_file = project_dir / "dot-agent.toml"
    config_file.write_text("[kits]\n# Empty config", encoding="utf-8")

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["list"])

    assert result.exit_code == 1
    assert "No artifacts found" in result.output


def test_artifact_show_single_match(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact show with single matching artifact."""
    user_claude, project_claude = setup_test_artifacts

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["show", "user-skill"])

    assert result.exit_code == 0
    # Should show artifact metadata
    assert "user-skill" in result.output
    assert "skill" in result.output
    # Should show file content
    assert "User skill content" in result.output
    # Should show absolute path
    expected_path = (user_claude / "skills" / "user-skill" / "SKILL.md").resolve()
    assert str(expected_path) in result.output


def test_artifact_show_multiple_matches(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact show with multiple matching artifacts."""
    user_claude, project_claude = setup_test_artifacts

    # Create same-named artifact at both levels
    user_commands_dir = user_claude / "commands"
    (user_commands_dir / "same-name.md").write_text("# User Same Name", encoding="utf-8")

    project_commands_dir = project_claude / "commands"
    project_commands_dir.mkdir(parents=True)
    (project_commands_dir / "same-name.md").write_text("# Project Same Name", encoding="utf-8")

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["show", "same-name"])

    assert result.exit_code == 0
    # Should show both artifacts
    assert "User Same Name" in result.output
    assert "Project Same Name" in result.output
    # Should show absolute paths for both
    user_path = (user_commands_dir / "same-name.md").resolve()
    project_path = (project_commands_dir / "same-name.md").resolve()
    assert str(user_path) in result.output
    assert str(project_path) in result.output


def test_artifact_show_not_found(
    setup_test_artifacts: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test artifact show with no matching artifacts."""
    user_claude, project_claude = setup_test_artifacts

    monkeypatch.setattr("pathlib.Path.home", lambda: user_claude.parent)
    monkeypatch.setattr("pathlib.Path.cwd", lambda: project_claude.parent)

    runner = CliRunner()
    result = runner.invoke(artifact_group, ["show", "nonexistent"])

    assert result.exit_code == 1
    assert "No artifact found" in result.output
