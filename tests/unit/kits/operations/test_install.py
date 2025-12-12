"""Tests for kit installation."""

from pathlib import Path

import pytest

from erk.kits.operations.install import install_kit
from erk.kits.sources.exceptions import ArtifactConflictError
from erk.kits.sources.resolver import ResolvedKit


def test_install_kit_basic(tmp_project: Path) -> None:
    """Test basic kit installation."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test-agent.md\n",
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("# Test Agent", encoding="utf-8")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify
    assert installed.kit_id == "test-kit"
    assert installed.version == "1.0.0"
    assert len(installed.artifacts) == 1

    agent_path = tmp_project / ".claude" / "agents" / "test-agent.md"
    assert agent_path.exists()

    content = agent_path.read_text(encoding="utf-8")
    assert "# Test Agent" in content


def test_install_kit_conflict(tmp_project: Path) -> None:
    """Test installation fails on conflict with ERROR policy."""
    # Create existing artifact
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("Existing", encoding="utf-8")

    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test-agent.md\n",
        encoding="utf-8",
    )

    agents_source = kit_dir / "agents"
    agents_source.mkdir()
    (agents_source / "test-agent.md").write_text("# New Agent", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Try to install - should fail with default (overwrite=False)
    with pytest.raises(ArtifactConflictError, match="Artifact already exists"):
        install_kit(resolved, tmp_project, overwrite=False)


def test_install_kit_creates_directories(tmp_project: Path) -> None:
    """Test installation creates .claude directory structure."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  command:\n"
        "    - commands/test-command.md\n",
        encoding="utf-8",
    )

    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "test-command.md").write_text("# Test Command", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    install_kit(resolved, tmp_project)

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

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test-agent.md\n",
        encoding="utf-8",
    )

    agents_source = kit_dir / "agents"
    agents_source.mkdir()
    (agents_source / "test-agent.md").write_text("# New Agent", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install with overwrite=True
    installed = install_kit(resolved, tmp_project, overwrite=True)

    # Verify new content written
    content = existing.read_text(encoding="utf-8")
    assert "# New Agent" in content
    assert len(installed.artifacts) == 1


def test_install_kit_namespaced_artifacts(tmp_project: Path) -> None:
    """Test installation of namespaced kit artifacts."""
    # Create mock kit with namespaced structure
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: my-kit\n"
        "version: 1.0.0\n"
        "description: Namespaced kit\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/my-kit/helper.md\n"
        "  skill:\n"
        "    - skills/my-kit/tool-a/SKILL.md\n"
        "    - skills/my-kit/tool-b/SKILL.md\n"
        "  command:\n"
        "    - commands/my-kit/build.md\n",
        encoding="utf-8",
    )

    # Create namespaced agent
    agents_dir = kit_dir / "agents" / "my-kit"
    agents_dir.mkdir(parents=True)
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create namespaced skills
    skill_a_dir = kit_dir / "skills" / "my-kit" / "tool-a"
    skill_a_dir.mkdir(parents=True)
    (skill_a_dir / "SKILL.md").write_text("# Tool A Skill", encoding="utf-8")

    skill_b_dir = kit_dir / "skills" / "my-kit" / "tool-b"
    skill_b_dir.mkdir(parents=True)
    (skill_b_dir / "SKILL.md").write_text("# Tool B Skill", encoding="utf-8")

    # Create namespaced command
    commands_dir = kit_dir / "commands" / "my-kit"
    commands_dir.mkdir(parents=True)
    (commands_dir / "build.md").write_text("# Build Command", encoding="utf-8")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="my-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

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

    # Verify artifact content
    agent_content = agent_path.read_text(encoding="utf-8")
    assert "# Helper Agent" in agent_content

    skill_a_content = skill_a_path.read_text(encoding="utf-8")
    assert "# Tool A Skill" in skill_a_content


def test_kit_manifest_namespace_validation() -> None:
    """Test KitManifest namespace validation (informational only, not enforced)."""
    from erk.kits.models.kit import KitManifest

    # Namespace validation is not enforced - all structures are allowed
    manifest = KitManifest(
        name="my-kit",
        version="1.0.0",
        description="Test",
        artifacts={
            "agent": ["agents/helper.md"],  # Any structure allowed
            "skill": ["skills/wrong-namespace/tool/SKILL.md"],  # Any structure allowed
        },
    )
    errors = manifest.validate_namespace_pattern()
    assert errors == []  # No enforcement - returns empty list


def test_bundled_kit_namespace_enforcement(tmp_path: Path) -> None:
    """Test that bundled kits can use any namespace structure (not enforced)."""
    from erk.kits.sources.bundled import BundledKitSource

    # Create a mock bundled kit with any namespace structure
    kit_dir = tmp_path / "data" / "kits" / "any-kit"
    kit_dir.mkdir(parents=True)

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: any-kit\n"
        "version: 1.0.0\n"
        "description: Kit with any namespace structure\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/helper.md\n",  # Any structure is allowed
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create a custom source that points to our temp directory
    class TestBundledSource(BundledKitSource):
        def _get_bundled_kit_path(self, source: str) -> Path | None:
            test_path = tmp_path / "data" / "kits" / source
            if test_path.exists():
                return test_path
            return None

    source = TestBundledSource()

    # Should resolve successfully - namespace validation is not enforced
    resolved = source.resolve("any-kit")
    assert resolved.kit_id == "any-kit"


def test_bundled_kit_valid_namespace_succeeds(tmp_path: Path) -> None:
    """Test that properly namespaced bundled kits resolve successfully."""
    from erk.kits.sources.bundled import BundledKitSource

    # Create a mock bundled kit with valid namespace
    kit_dir = tmp_path / "data" / "kits" / "good-kit"
    kit_dir.mkdir(parents=True)

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: good-kit\n"
        "version: 1.0.0\n"
        "description: Kit with valid namespace\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/good-kit/helper.md\n",  # Properly namespaced
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents" / "good-kit"
    agents_dir.mkdir(parents=True)
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create a custom source that points to our temp directory
    class TestBundledSource(BundledKitSource):
        def _get_bundled_kit_path(self, source: str) -> Path | None:
            test_path = tmp_path / "data" / "kits" / source
            if test_path.exists():
                return test_path
            return None

    source = TestBundledSource()

    # Should resolve successfully
    resolved = source.resolve("good-kit")
    assert resolved.kit_id == "good-kit"


def test_install_kit_with_docs(tmp_project: Path) -> None:
    """Test installation of kit with doc artifacts."""
    # Create mock kit with docs
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test kit with docs\n"
        "artifacts:\n"
        "  doc:\n"
        "    - docs/tools/pytest.md\n"
        "    - docs/tools/pyright.md\n"
        "    - docs/overview.md\n",
        encoding="utf-8",
    )

    # Create doc files with nested structure
    docs_dir = kit_dir / "docs"
    tools_dir = docs_dir / "tools"
    tools_dir.mkdir(parents=True)
    (tools_dir / "pytest.md").write_text("# Pytest Documentation", encoding="utf-8")
    (tools_dir / "pyright.md").write_text("# Pyright Documentation", encoding="utf-8")
    (docs_dir / "overview.md").write_text("# Overview", encoding="utf-8")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify installation metadata
    assert installed.kit_id == "test-kit"
    assert installed.version == "1.0.0"
    assert len(installed.artifacts) == 3

    # Verify doc files are installed in correct structure
    docs_base = tmp_project / ".claude" / "docs"
    assert docs_base.exists()

    # Check nested structure is preserved
    pytest_doc = docs_base / "tools" / "pytest.md"
    assert pytest_doc.exists()
    assert "# Pytest Documentation" in pytest_doc.read_text(encoding="utf-8")

    pyright_doc = docs_base / "tools" / "pyright.md"
    assert pyright_doc.exists()
    assert "# Pyright Documentation" in pyright_doc.read_text(encoding="utf-8")

    overview_doc = docs_base / "overview.md"
    assert overview_doc.exists()
    assert "# Overview" in overview_doc.read_text(encoding="utf-8")


def test_install_kit_with_docs_and_agents(tmp_project: Path) -> None:
    """Test installation of kit with both docs and agents."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: devrun\n"
        "version: 0.1.0\n"
        "description: Kit with agent and docs\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/devrun/devrun.md\n"
        "  doc:\n"
        "    - docs/tools/make.md\n",
        encoding="utf-8",
    )

    # Create agent
    agents_dir = kit_dir / "agents" / "devrun"
    agents_dir.mkdir(parents=True)
    (agents_dir / "devrun.md").write_text("# Devrun Agent", encoding="utf-8")

    # Create doc
    docs_dir = kit_dir / "docs" / "tools"
    docs_dir.mkdir(parents=True)
    (docs_dir / "make.md").write_text("# Make Documentation", encoding="utf-8")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="devrun",
        version="0.1.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify both artifact types
    assert len(installed.artifacts) == 2

    # Verify agent installed
    agent_path = tmp_project / ".claude" / "agents" / "devrun" / "devrun.md"
    assert agent_path.exists()
    assert "# Devrun Agent" in agent_path.read_text(encoding="utf-8")

    # Verify doc installed
    doc_path = tmp_project / ".claude" / "docs" / "tools" / "make.md"
    assert doc_path.exists()
    assert "# Make Documentation" in doc_path.read_text(encoding="utf-8")


def test_install_kit_with_workflow(tmp_project: Path) -> None:
    """Test installation of kit with workflow artifact to .github/workflows/."""
    # Create mock kit with workflow
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test kit with workflow\n"
        "artifacts:\n"
        "  workflow:\n"
        "    - workflows/test-kit/deploy.yml\n",
        encoding="utf-8",
    )

    # Create workflow file with nested structure
    workflows_dir = kit_dir / "workflows" / "test-kit"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "deploy.yml").write_text(
        "name: Deploy\non: push\njobs: {}\n",
        encoding="utf-8",
    )

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify installation metadata
    assert installed.kit_id == "test-kit"
    assert installed.version == "1.0.0"
    assert len(installed.artifacts) == 1

    # Verify workflow file is installed in .github/workflows/ (NOT .claude/)
    workflow_path = tmp_project / ".github" / "workflows" / "test-kit" / "deploy.yml"
    assert workflow_path.exists()
    assert "name: Deploy" in workflow_path.read_text(encoding="utf-8")

    # Verify NO workflow was installed in .claude/
    assert not (tmp_project / ".claude" / "workflows").exists()


def test_install_kit_with_workflow_and_agents(tmp_project: Path) -> None:
    """Test installation of kit with both workflows and agents."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: mixed-kit\n"
        "version: 1.0.0\n"
        "description: Kit with both workflow and agent\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/mixed-kit/helper.md\n"
        "  workflow:\n"
        "    - workflows/mixed-kit/ci.yml\n",
        encoding="utf-8",
    )

    # Create agent
    agents_dir = kit_dir / "agents" / "mixed-kit"
    agents_dir.mkdir(parents=True)
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create workflow
    workflows_dir = kit_dir / "workflows" / "mixed-kit"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text(
        "name: CI\non: [push, pull_request]\njobs: {}\n",
        encoding="utf-8",
    )

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="mixed-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify both artifact types
    assert len(installed.artifacts) == 2

    # Verify agent installed in .claude/
    agent_path = tmp_project / ".claude" / "agents" / "mixed-kit" / "helper.md"
    assert agent_path.exists()
    assert "# Helper Agent" in agent_path.read_text(encoding="utf-8")

    # Verify workflow installed in .github/
    workflow_path = tmp_project / ".github" / "workflows" / "mixed-kit" / "ci.yml"
    assert workflow_path.exists()
    assert "name: CI" in workflow_path.read_text(encoding="utf-8")


def test_install_kit_workflow_creates_github_directory(tmp_project: Path) -> None:
    """Test installation creates .github directory structure when needed."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  workflow:\n"
        "    - workflows/test-kit/build.yml\n",
        encoding="utf-8",
    )

    workflows_dir = kit_dir / "workflows" / "test-kit"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "build.yml").write_text("name: Build\n", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Verify .github doesn't exist before install
    assert not (tmp_project / ".github").exists()

    # Install
    install_kit(resolved, tmp_project)

    # Verify directories created
    assert (tmp_project / ".github").exists()
    assert (tmp_project / ".github" / "workflows").exists()
    assert (tmp_project / ".github" / "workflows" / "test-kit" / "build.yml").exists()


def test_install_skill_directory_two_stage(tmp_project: Path) -> None:
    """Test that skill directories use two-stage installation.

    Skills should be:
    1. Installed to .erk/skills/{skill-name}/
    2. Symlinked from .claude/skills/{skill-name}/ -> .erk/skills/{skill-name}/
    """
    # Create mock kit with a skill directory
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test kit with skill directory\n"
        "artifacts:\n"
        "  skill:\n"
        "    - skills/my-skill\n",
        encoding="utf-8",
    )

    # Create skill directory (not a file)
    skill_dir = kit_dir / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# My Skill\nContent here.", encoding="utf-8")
    (skill_dir / "extra.md").write_text("# Extra content", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify the skill was installed using two-stage pattern
    assert installed.kit_id == "test-kit"
    assert len(installed.managed_skills) == 1
    assert ".erk/skills/my-skill" in installed.managed_skills[0]

    # Verify .erk/skills/{skill-name}/ exists (Stage 1)
    erk_skill_path = tmp_project / ".erk" / "skills" / "my-skill"
    assert erk_skill_path.exists()

    # Verify .claude/skills/{skill-name}/ is a symlink (Stage 2)
    claude_skill_path = tmp_project / ".claude" / "skills" / "my-skill"
    assert claude_skill_path.exists()
    assert claude_skill_path.is_symlink()

    # Verify the symlink points to the correct location
    symlink_target = claude_skill_path.resolve()
    assert symlink_target == erk_skill_path.resolve()

    # Verify content is accessible through the symlink
    skill_content = (claude_skill_path / "SKILL.md").read_text(encoding="utf-8")
    assert "# My Skill" in skill_content


def test_install_skill_directory_managed_skills_tracking(tmp_project: Path) -> None:
    """Test that managed_skills tracks the .erk/skills paths correctly."""
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: multi-skill-kit\n"
        "version: 1.0.0\n"
        "description: Kit with multiple skills\n"
        "artifacts:\n"
        "  skill:\n"
        "    - skills/skill-a\n"
        "    - skills/skill-b\n",
        encoding="utf-8",
    )

    # Create multiple skill directories
    for skill_name in ["skill-a", "skill-b"]:
        skill_dir = kit_dir / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="multi-skill-kit",
        version="1.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    installed = install_kit(resolved, tmp_project)

    # Verify managed_skills tracking
    assert len(installed.managed_skills) == 2
    managed_paths = sorted(installed.managed_skills)
    assert ".erk/skills/skill-a" in managed_paths[0]
    assert ".erk/skills/skill-b" in managed_paths[1]

    # Verify artifacts list has the .claude symlink paths
    assert len(installed.artifacts) == 2
    artifact_paths = sorted(installed.artifacts)
    assert ".claude/skills/skill-a" in artifact_paths[0]
    assert ".claude/skills/skill-b" in artifact_paths[1]


def test_install_skill_directory_overwrite(tmp_project: Path) -> None:
    """Test that overwrite=True correctly replaces existing skill installations."""
    # Create existing skill installation
    erk_skills = tmp_project / ".erk" / "skills" / "existing-skill"
    erk_skills.mkdir(parents=True)
    (erk_skills / "SKILL.md").write_text("# Old content", encoding="utf-8")

    claude_skills = tmp_project / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    claude_skill_symlink = claude_skills / "existing-skill"
    claude_skill_symlink.symlink_to("../../.erk/skills/existing-skill")

    # Create kit with updated skill
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 2.0.0\n"
        "description: Updated kit\n"
        "artifacts:\n"
        "  skill:\n"
        "    - skills/existing-skill\n",
        encoding="utf-8",
    )

    skill_dir = kit_dir / "skills" / "existing-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# New content", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="2.0.0",
        source_type="package",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install with overwrite
    installed = install_kit(resolved, tmp_project, overwrite=True)

    # Verify content was updated
    skill_content = (tmp_project / ".claude" / "skills" / "existing-skill" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "# New content" in skill_content
    assert installed.version == "2.0.0"
