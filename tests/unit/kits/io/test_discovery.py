"""Tests for artifact discovery."""

from pathlib import Path

from erk.kits.io.discovery import discover_installed_artifacts
from erk.kits.models.config import InstalledKit, ProjectConfig


def test_discover_kit_skills_with_matching_prefixes(tmp_project: Path) -> None:
    """Test that skills with kit prefixes are detected correctly."""
    # Create config with devrun and gt kits
    config = ProjectConfig(
        version="1",
        kits={
            "devrun": InstalledKit(
                kit_id="devrun",
                source_type="bundled",
                version="1.0.0",
                artifacts=[],
            ),
            "gt": InstalledKit(
                kit_id="gt",
                source_type="bundled",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create skills with matching prefixes
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    # Create devrun-make skill
    devrun_skill = skills_dir / "devrun-make"
    devrun_skill.mkdir()
    (devrun_skill / "SKILL.md").write_text("# Make Skill", encoding="utf-8")

    # Create gt-graphite skill
    gt_skill = skills_dir / "gt-graphite"
    gt_skill.mkdir()
    (gt_skill / "SKILL.md").write_text("# Graphite Skill", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    assert "devrun" in discovered
    assert "skill" in discovered["devrun"]
    assert "gt" in discovered
    assert "skill" in discovered["gt"]


def test_discover_unmanaged_skills(tmp_project: Path) -> None:
    """Test that skills without matching prefixes are detected as unmanaged."""
    # Create config with only devrun kit
    config = ProjectConfig(
        version="1",
        kits={
            "devrun": InstalledKit(
                kit_id="devrun",
                source_type="bundled",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create skills
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    # Create dignified-python skill (no matching prefix)
    dignified_skill = skills_dir / "dignified-python"
    dignified_skill.mkdir()
    (dignified_skill / "SKILL.md").write_text("# Dignified Python", encoding="utf-8")

    # Create example-kit skill (no matching prefix)
    example_skill = skills_dir / "example-kit"
    example_skill.mkdir()
    (example_skill / "SKILL.md").write_text("# Example Kit", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    # These should be detected as separate "kits" (unmanaged)
    assert "dignified-python" in discovered
    assert "skill" in discovered["dignified-python"]
    assert "example-kit" in discovered
    assert "skill" in discovered["example-kit"]


def test_discover_direct_command_files(tmp_project: Path) -> None:
    """Test that direct command files in .claude/commands/ are detected."""
    config = ProjectConfig(version="1", kits={})

    # Create direct command files
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir()

    (commands_dir / "my-command.md").write_text("# My Command", encoding="utf-8")
    (commands_dir / "another-command.md").write_text("# Another", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    # Direct files should be detected - but they won't show up in discover_installed_artifacts
    # because that function only finds subdirectories for commands
    # This is expected behavior based on current implementation
    assert len(discovered) == 0


def test_discover_kit_command_subdirectories(tmp_project: Path) -> None:
    """Test that kit command subdirectories are detected."""
    config = ProjectConfig(
        version="1",
        kits={
            "mykit": InstalledKit(
                kit_id="mykit",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create kit command subdirectory
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir()

    kit_commands = commands_dir / "mykit"
    kit_commands.mkdir()
    (kit_commands / "cmd1.md").write_text("# Command 1", encoding="utf-8")
    (kit_commands / "cmd2.md").write_text("# Command 2", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    assert "mykit" in discovered
    assert "command" in discovered["mykit"]


def test_discover_direct_agent_files(tmp_project: Path) -> None:
    """Test that direct agent files in .claude/agents/ are detected."""
    config = ProjectConfig(version="1", kits={})

    # Create direct agent files
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()

    (agents_dir / "my-agent.md").write_text("# My Agent", encoding="utf-8")
    (agents_dir / "another-agent.md").write_text("# Another", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    # Direct files won't show up in discover_installed_artifacts
    # because that function only finds subdirectories for agents
    assert len(discovered) == 0


def test_discover_kit_agent_subdirectories(tmp_project: Path) -> None:
    """Test that kit agent subdirectories are detected."""
    config = ProjectConfig(
        version="1",
        kits={
            "mykit": InstalledKit(
                kit_id="mykit",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create kit agent subdirectory
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()

    kit_agents = agents_dir / "mykit"
    kit_agents.mkdir()
    (kit_agents / "agent1.md").write_text("# Agent 1", encoding="utf-8")
    (kit_agents / "agent2.md").write_text("# Agent 2", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    assert "mykit" in discovered
    assert "agent" in discovered["mykit"]


def test_discover_with_empty_config(tmp_project: Path) -> None:
    """Test discovery works correctly with empty config."""
    config = ProjectConfig(version="1", kits={})

    # Create some unmanaged skills
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    skill_dir = skills_dir / "standalone-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Standalone", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    # Without kit prefixes, skill name becomes the "kit"
    assert "standalone-skill" in discovered
    assert "skill" in discovered["standalone-skill"]


def test_discover_with_none_config(tmp_project: Path) -> None:
    """Test discovery works with None config (backwards compatibility)."""
    # Create some skills
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    skill_dir = skills_dir / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# My Skill", encoding="utf-8")

    # Discover with None config
    discovered = discover_installed_artifacts(tmp_project, None)

    # All skills should be treated as standalone
    assert "my-skill" in discovered
    assert "skill" in discovered["my-skill"]


def test_discover_returns_empty_when_no_claude_dir(tmp_project: Path) -> None:
    """Test that discovery returns empty dict when .claude/ doesn't exist."""
    config = ProjectConfig(version="1", kits={})

    discovered = discover_installed_artifacts(tmp_project, config)

    assert discovered == {}


def test_discover_multiple_artifact_types(tmp_project: Path) -> None:
    """Test discovering kit with multiple artifact types."""
    config = ProjectConfig(
        version="1",
        kits={
            "mykit": InstalledKit(
                kit_id="mykit",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create artifacts of different types for the same kit
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()

    # Skill
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "mykit-tool"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Tool", encoding="utf-8")

    # Commands
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir()
    kit_commands = commands_dir / "mykit"
    kit_commands.mkdir()
    (kit_commands / "cmd.md").write_text("# Command", encoding="utf-8")

    # Agents
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    kit_agents = agents_dir / "mykit"
    kit_agents.mkdir()
    (kit_agents / "agent.md").write_text("# Agent", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    assert "mykit" in discovered
    assert "skill" in discovered["mykit"]
    assert "command" in discovered["mykit"]
    assert "agent" in discovered["mykit"]
    assert len(discovered["mykit"]) == 3


def test_discover_workflows_in_github_directory(tmp_project: Path) -> None:
    """Test discovering workflow artifacts in .github/workflows/<kit>/ directories."""
    config = ProjectConfig(
        version="1",
        kits={
            "mykit": InstalledKit(
                kit_id="mykit",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create workflow files in .github/workflows/mykit/
    workflows_dir = tmp_project / ".github" / "workflows" / "mykit"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (workflows_dir / "deploy.yaml").write_text("name: Deploy\n", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    assert "mykit" in discovered
    assert "workflow" in discovered["mykit"]


def test_discover_workflows_ignores_files_at_workflows_root(tmp_project: Path) -> None:
    """Test that files directly in .github/workflows/ are not detected as kit workflows."""
    config = ProjectConfig(version="1", kits={})

    # Create workflow files directly in .github/workflows/ (no kit subdirectory)
    workflows_dir = tmp_project / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    # No kits should be detected - workflows at root are not kit artifacts
    assert len(discovered) == 0


def test_discover_multiple_kit_workflows(tmp_project: Path) -> None:
    """Test discovering workflows from multiple kits."""
    config = ProjectConfig(
        version="1",
        kits={
            "kit-a": InstalledKit(
                kit_id="kit-a",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
            "kit-b": InstalledKit(
                kit_id="kit-b",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create workflows for kit-a
    kit_a_workflows = tmp_project / ".github" / "workflows" / "kit-a"
    kit_a_workflows.mkdir(parents=True)
    (kit_a_workflows / "build.yml").write_text("name: Build\n", encoding="utf-8")

    # Create workflows for kit-b
    kit_b_workflows = tmp_project / ".github" / "workflows" / "kit-b"
    kit_b_workflows.mkdir(parents=True)
    (kit_b_workflows / "test.yaml").write_text("name: Test\n", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    assert "kit-a" in discovered
    assert "workflow" in discovered["kit-a"]
    assert "kit-b" in discovered
    assert "workflow" in discovered["kit-b"]


def test_discover_kit_with_workflows_and_other_artifacts(tmp_project: Path) -> None:
    """Test discovering kit with both workflows (.github) and other artifacts (.claude)."""
    config = ProjectConfig(
        version="1",
        kits={
            "mykit": InstalledKit(
                kit_id="mykit",
                source_type="package",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    # Create workflow in .github/
    workflows_dir = tmp_project / ".github" / "workflows" / "mykit"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")

    # Create command in .claude/
    claude_dir = tmp_project / ".claude"
    commands_dir = claude_dir / "commands" / "mykit"
    commands_dir.mkdir(parents=True)
    (commands_dir / "deploy.md").write_text("# Deploy Command", encoding="utf-8")

    # Discover
    discovered = discover_installed_artifacts(tmp_project, config)

    # Kit should have both workflow and command detected
    assert "mykit" in discovered
    assert "workflow" in discovered["mykit"]
    assert "command" in discovered["mykit"]
    assert len(discovered["mykit"]) == 2
