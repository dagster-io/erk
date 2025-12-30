"""Tests for kit installation."""

from pathlib import Path

import pytest

from erk.kits.models.resolved import ArtifactConflictError, ResolvedKit
from erk.kits.operations.install import install_kit


def _create_kit_artifact(path: Path, content: str, kit_name: str) -> None:
    """Create an artifact file with erk.kit frontmatter.

    Args:
        path: Path to create the file at
        content: Content of the file (after frontmatter)
        kit_name: Kit name for frontmatter
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\nerk:\n  kit: {kit_name}\n---\n"
    path.write_text(frontmatter + content, encoding="utf-8")


def test_install_kit_basic(tmp_project: Path) -> None:
    """Test basic kit installation."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    _create_kit_artifact(agents_dir / "test-agent.md", "# Test Agent", "test-kit")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",  # Not used anymore but kept for compatibility
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)

    # Verify
    assert installed.kit_id == "test-kit"
    assert installed.version == "1.0.0"
    assert len(installed.artifacts) == 1

    agent_path = tmp_project / ".claude" / "agents" / "test-agent.md"
    assert agent_path.exists()

    content = agent_path.read_text(encoding="utf-8")
    assert "# Test Agent" in content


def test_install_kit_conflict(tmp_project: Path) -> None:
    """Test installation fails on conflict with overwrite=False."""
    # Create existing artifact
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("Existing", encoding="utf-8")

    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    agents_source = kit_dir / "agents"
    agents_source.mkdir()
    _create_kit_artifact(agents_source / "test-agent.md", "# New Agent", "test-kit")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Try to install - should fail with default (overwrite=False)
    with pytest.raises(ArtifactConflictError, match="Artifact already exists"):
        install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)


def test_install_kit_creates_directories(tmp_project: Path) -> None:
    """Test installation creates .claude directory structure."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()
    _create_kit_artifact(commands_dir / "test-command.md", "# Test Command", "test-kit")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Install
    install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)

    # Verify directories created
    assert (tmp_project / ".claude").exists()
    assert (tmp_project / ".claude" / "commands").exists()
    assert (tmp_project / ".claude" / "commands" / "test-command.md").exists()


def test_install_kit_overwrite_policy(tmp_project: Path) -> None:
    """Test overwrite=True replaces existing files."""
    # Create existing artifact
    claude_dir = tmp_project / ".claude/agents"
    claude_dir.mkdir(parents=True)
    existing = claude_dir / "test-agent.md"
    existing.write_text("Original content", encoding="utf-8")

    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    agents_source = kit_dir / "agents"
    agents_source.mkdir()
    _create_kit_artifact(agents_source / "test-agent.md", "# New Agent", "test-kit")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Install with overwrite=True
    installed = install_kit(resolved, tmp_project, overwrite=True, filtered_artifacts=None)

    # Verify new content written
    content = existing.read_text(encoding="utf-8")
    assert "# New Agent" in content
    assert len(installed.artifacts) == 1


def test_install_kit_namespaced_artifacts(tmp_project: Path) -> None:
    """Test installation of namespaced kit artifacts."""
    # Create mock kit with namespaced structure
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    # Create namespaced agent
    agents_dir = kit_dir / "agents" / "my-kit"
    agents_dir.mkdir(parents=True)
    _create_kit_artifact(agents_dir / "helper.md", "# Helper Agent", "my-kit")

    # Create namespaced skills
    skill_a_dir = kit_dir / "skills" / "my-kit" / "tool-a"
    skill_a_dir.mkdir(parents=True)
    _create_kit_artifact(skill_a_dir / "SKILL.md", "# Tool A Skill", "my-kit")

    skill_b_dir = kit_dir / "skills" / "my-kit" / "tool-b"
    skill_b_dir.mkdir(parents=True)
    _create_kit_artifact(skill_b_dir / "SKILL.md", "# Tool B Skill", "my-kit")

    # Create namespaced command
    commands_dir = kit_dir / "commands" / "my-kit"
    commands_dir.mkdir(parents=True)
    _create_kit_artifact(commands_dir / "build.md", "# Build Command", "my-kit")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="my-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)

    # Verify namespaced structure is preserved in .claude/
    claude_dir = tmp_project / ".claude"

    # Check agent namespace
    agent_path = claude_dir / "agents" / "my-kit" / "helper.md"
    assert agent_path.exists()
    assert "# Helper Agent" in agent_path.read_text(encoding="utf-8")

    # Check skill namespaces
    skill_a_path = claude_dir / "skills" / "my-kit" / "tool-a" / "SKILL.md"
    assert skill_a_path.exists()
    assert "# Tool A Skill" in skill_a_path.read_text(encoding="utf-8")

    skill_b_path = claude_dir / "skills" / "my-kit" / "tool-b" / "SKILL.md"
    assert skill_b_path.exists()
    assert "# Tool B Skill" in skill_b_path.read_text(encoding="utf-8")

    # Check command namespace
    command_path = claude_dir / "commands" / "my-kit" / "build.md"
    assert command_path.exists()
    assert "# Build Command" in command_path.read_text(encoding="utf-8")

    # Verify all artifacts were installed
    assert len(installed.artifacts) == 4


def test_install_kit_with_docs(tmp_project: Path) -> None:
    """Test installation of kit with doc artifacts."""
    # Create mock kit with docs
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    # Create doc files with nested structure
    docs_dir = kit_dir / "docs"
    tools_dir = docs_dir / "tools"
    tools_dir.mkdir(parents=True)
    _create_kit_artifact(tools_dir / "pytest.md", "# Pytest Documentation", "test-kit")
    _create_kit_artifact(tools_dir / "pyright.md", "# Pyright Documentation", "test-kit")
    _create_kit_artifact(docs_dir / "overview.md", "# Overview", "test-kit")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)

    # Verify installation metadata
    assert installed.kit_id == "test-kit"
    assert installed.version == "1.0.0"
    assert len(installed.artifacts) == 3

    # Verify doc files are installed in correct structure
    # Kit docs are installed to .erk/docs/kits/ (not .claude/docs/)
    docs_base = tmp_project / ".erk" / "docs" / "kits"
    assert docs_base.exists()

    # Check nested structure is preserved
    pytest_doc = docs_base / "tools" / "pytest.md"
    assert pytest_doc.exists()
    assert "# Pytest Documentation" in pytest_doc.read_text(encoding="utf-8")


def test_install_kit_with_docs_and_agents(tmp_project: Path) -> None:
    """Test installation of kit with both docs and agents."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    # Create agent
    agents_dir = kit_dir / "agents" / "devrun"
    agents_dir.mkdir(parents=True)
    _create_kit_artifact(agents_dir / "devrun.md", "# Devrun Agent", "devrun")

    # Create doc
    docs_dir = kit_dir / "docs" / "tools"
    docs_dir.mkdir(parents=True)
    _create_kit_artifact(docs_dir / "make.md", "# Make Documentation", "devrun")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="devrun",
        version="0.1.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)

    # Verify both artifact types
    assert len(installed.artifacts) == 2

    # Verify agent installed
    agent_path = tmp_project / ".claude" / "agents" / "devrun" / "devrun.md"
    assert agent_path.exists()
    assert "# Devrun Agent" in agent_path.read_text(encoding="utf-8")

    # Verify doc installed (kit docs go to .erk/docs/kits/)
    doc_path = tmp_project / ".erk" / "docs" / "kits" / "tools" / "make.md"
    assert doc_path.exists()
    assert "# Make Documentation" in doc_path.read_text(encoding="utf-8")


def test_install_kit_installs_all_artifacts(tmp_project: Path) -> None:
    """Test installation installs all markdown files from kit directories."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()

    # Create artifacts - all should be installed regardless of frontmatter
    _create_kit_artifact(agents_dir / "correct.md", "# Correct Agent", "test-kit")
    _create_kit_artifact(agents_dir / "other.md", "# Other Agent", "other-kit")
    (agents_dir / "no-frontmatter.md").write_text("# No Frontmatter", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=kit_dir / "kit.yaml",
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project, overwrite=False, filtered_artifacts=None)

    # All artifacts should be installed (directory-based discovery)
    assert len(installed.artifacts) == 3
    assert (tmp_project / ".claude" / "agents" / "correct.md").exists()
    assert (tmp_project / ".claude" / "agents" / "other.md").exists()
    assert (tmp_project / ".claude" / "agents" / "no-frontmatter.md").exists()
