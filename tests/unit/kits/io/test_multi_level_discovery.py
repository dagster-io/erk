"""Tests for multi-level artifact discovery."""

from pathlib import Path

from erk.kits.models.artifact import ArtifactLevel
from erk.kits.models.config import ProjectConfig
from erk.kits.repositories.filesystem_artifact_repository import FilesystemArtifactRepository


def test_discover_multi_level_with_both_levels(tmp_path: Path) -> None:
    """Test multi-level discovery with artifacts at both user and project levels."""
    # Create user-level .claude directory with a skill
    user_claude = tmp_path / "user" / ".claude"
    user_skill_dir = user_claude / "skills" / "user-skill"
    user_skill_dir.mkdir(parents=True)
    user_skill_file = user_skill_dir / "SKILL.md"
    user_skill_file.write_text("# User Skill", encoding="utf-8")

    # Create project-level .claude directory with a command
    project_claude = tmp_path / "project" / ".claude"
    project_commands_dir = project_claude / "commands"
    project_commands_dir.mkdir(parents=True)
    project_command_file = project_commands_dir / "project-cmd.md"
    project_command_file.write_text("# Project Command", encoding="utf-8")

    # Create empty project config
    config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_multi_level(user_claude, project_claude, config)

    # Verify both levels discovered
    assert len(artifacts) == 2

    # Verify user skill
    user_artifacts = [a for a in artifacts if a.level == ArtifactLevel.USER]
    assert len(user_artifacts) == 1
    assert user_artifacts[0].artifact_type == "skill"
    assert user_artifacts[0].artifact_name == "user-skill"

    # Verify project command
    project_artifacts = [a for a in artifacts if a.level == ArtifactLevel.PROJECT]
    assert len(project_artifacts) == 1
    assert project_artifacts[0].artifact_type == "command"
    assert project_artifacts[0].artifact_name == "project-cmd"


def test_discover_multi_level_with_missing_directories(tmp_path: Path) -> None:
    """Test multi-level discovery handles missing directories gracefully."""
    # Create only user directory, project doesn't exist
    user_claude = tmp_path / "user" / ".claude"
    user_skill_dir = user_claude / "skills" / "test-skill"
    user_skill_dir.mkdir(parents=True)
    user_skill_file = user_skill_dir / "SKILL.md"
    user_skill_file.write_text("# Test Skill", encoding="utf-8")

    project_claude = tmp_path / "nonexistent" / ".claude"

    config = ProjectConfig(version="1", kits={})

    # Should not raise exception
    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_multi_level(user_claude, project_claude, config)

    # Should only find user artifacts
    assert len(artifacts) == 1
    assert artifacts[0].level == ArtifactLevel.USER


def test_discover_multi_level_with_same_name_artifacts(tmp_path: Path) -> None:
    """Test that same-name artifacts at both levels are both discovered."""
    # Create user-level command
    user_claude = tmp_path / "user" / ".claude"
    user_commands_dir = user_claude / "commands"
    user_commands_dir.mkdir(parents=True)
    user_command_file = user_commands_dir / "same-name.md"
    user_command_file.write_text("# User Command", encoding="utf-8")

    # Create project-level command with same name
    project_claude = tmp_path / "project" / ".claude"
    project_commands_dir = project_claude / "commands"
    project_commands_dir.mkdir(parents=True)
    project_command_file = project_commands_dir / "same-name.md"
    project_command_file.write_text("# Project Command", encoding="utf-8")

    config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_multi_level(user_claude, project_claude, config)

    # Should find both
    assert len(artifacts) == 2

    user_artifacts = [a for a in artifacts if a.level == ArtifactLevel.USER]
    project_artifacts = [a for a in artifacts if a.level == ArtifactLevel.PROJECT]

    assert len(user_artifacts) == 1
    assert len(project_artifacts) == 1
    assert user_artifacts[0].artifact_name == "same-name"
    assert project_artifacts[0].artifact_name == "same-name"


def test_discover_multi_level_with_hooks_settings_source(tmp_path: Path) -> None:
    """Test that hook artifacts include settings source tracking."""
    # Create project-level .claude directory with settings
    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    # Create settings.json with a hook
    settings_json = project_claude / "settings.json"
    settings_content = """
    {
        "hooks": {
            "user-prompt-submit": [
                {
                    "matcher": "**",
                    "hooks": [
                        {
                            "command": "echo test"
                        }
                    ]
                }
            ]
        }
    }
    """
    settings_json.write_text(settings_content, encoding="utf-8")

    config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    user_claude = tmp_path / "user" / ".claude"  # Doesn't exist
    artifacts = repository.discover_multi_level(user_claude, project_claude, config)

    # Should find hook
    hooks = [a for a in artifacts if a.artifact_type == "hook"]
    assert len(hooks) == 1
    assert hooks[0].settings_source == "settings.json"


def test_discover_multi_level_empty_directories(tmp_path: Path) -> None:
    """Test multi-level discovery with empty directories returns empty list."""
    # Create empty directories
    user_claude = tmp_path / "user" / ".claude"
    user_claude.mkdir(parents=True)

    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_multi_level(user_claude, project_claude, config)

    # Should be empty
    assert len(artifacts) == 0


def test_discover_multi_level_with_all_artifact_types(tmp_path: Path) -> None:
    """Test multi-level discovery finds all artifact types."""
    # Create user-level artifacts
    user_claude = tmp_path / "user" / ".claude"

    # Skill
    user_skill_dir = user_claude / "skills" / "user-skill"
    user_skill_dir.mkdir(parents=True)
    (user_skill_dir / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    # Command
    user_commands_dir = user_claude / "commands"
    user_commands_dir.mkdir(parents=True)
    (user_commands_dir / "user-cmd.md").write_text("# User Command", encoding="utf-8")

    # Agent
    user_agents_dir = user_claude / "agents"
    user_agents_dir.mkdir(parents=True)
    (user_agents_dir / "user-agent.md").write_text("# User Agent", encoding="utf-8")

    # Hook in settings
    user_settings = user_claude / "settings.json"
    hooks_json = (
        '{"hooks": {"user-prompt-submit": [{"matcher": "**", '
        '"hooks": [{"command": "echo user"}]}]}}'
    )
    user_settings.write_text(hooks_json, encoding="utf-8")

    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_multi_level(user_claude, project_claude, config)

    # Should find all types
    assert len(artifacts) == 4

    types = {a.artifact_type for a in artifacts}
    assert types == {"skill", "command", "agent", "hook"}

    # All should be user level
    assert all(a.level == ArtifactLevel.USER for a in artifacts)
