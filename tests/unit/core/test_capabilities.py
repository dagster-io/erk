"""Tests for the capability system.

These tests verify:
1. The Capability ABC contract
2. The registry functions (get, list)
3. The LearnedDocsCapability implementation
4. Skill-based capabilities
"""

from pathlib import Path

from erk.core.capabilities.agents import DevrunAgentCapability
from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
)
from erk.core.capabilities.learned_docs import LearnedDocsCapability
from erk.core.capabilities.permissions import ErkBashPermissionsCapability
from erk.core.capabilities.registry import get_capability, list_capabilities
from erk.core.capabilities.skills import (
    DignifiedPythonCapability,
    FakeDrivenTestingCapability,
)
from erk.core.capabilities.workflows import ErkImplWorkflowCapability

# =============================================================================
# Tests for CapabilityResult
# =============================================================================


def test_capability_result_is_frozen() -> None:
    """Test that CapabilityResult is immutable."""
    result = CapabilityResult(success=True, message="test")
    assert result.success is True
    assert result.message == "test"


# =============================================================================
# Tests for Registry Functions
# =============================================================================


def test_get_capability_returns_registered_capability() -> None:
    """Test that get_capability returns a registered capability by name."""
    cap = get_capability("learned-docs")
    assert cap is not None
    assert cap.name == "learned-docs"


def test_get_capability_returns_none_for_unknown() -> None:
    """Test that get_capability returns None for unknown capability names."""
    cap = get_capability("nonexistent-capability")
    assert cap is None


def test_list_capabilities_returns_all_registered() -> None:
    """Test that list_capabilities returns all registered capabilities."""
    caps = list_capabilities()
    assert len(caps) >= 1
    names = [cap.name for cap in caps]
    assert "learned-docs" in names


# =============================================================================
# Tests for LearnedDocsCapability
# =============================================================================


def test_learned_docs_capability_name() -> None:
    """Test that LearnedDocsCapability has correct name."""
    cap = LearnedDocsCapability()
    assert cap.name == "learned-docs"


def test_learned_docs_capability_description() -> None:
    """Test that LearnedDocsCapability has a description."""
    cap = LearnedDocsCapability()
    assert cap.description == "Autolearning documentation system"


def test_learned_docs_is_installed_false_when_missing(tmp_path: Path) -> None:
    """Test that is_installed returns False when docs/learned/ doesn't exist."""
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path) is False


def test_learned_docs_is_installed_true_when_exists(tmp_path: Path) -> None:
    """Test that is_installed returns True when docs/learned/ exists."""
    (tmp_path / "docs" / "learned").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path) is True


def test_learned_docs_install_creates_directory(tmp_path: Path) -> None:
    """Test that install creates docs/learned/ directory."""
    cap = LearnedDocsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert (tmp_path / "docs" / "learned").is_dir()


def test_learned_docs_install_creates_readme(tmp_path: Path) -> None:
    """Test that install creates README.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path)

    readme_path = tmp_path / "docs" / "learned" / "README.md"
    assert readme_path.exists()
    content = readme_path.read_text(encoding="utf-8")
    assert "Learned Documentation" in content
    assert "read_when" in content


def test_learned_docs_install_creates_index(tmp_path: Path) -> None:
    """Test that install creates index.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path)

    index_path = tmp_path / "docs" / "learned" / "index.md"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED FILE" in content
    assert "erk docs sync" in content
    assert "# Agent Documentation" in content


def test_learned_docs_install_creates_tripwires(tmp_path: Path) -> None:
    """Test that install creates tripwires.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path)

    tripwires_path = tmp_path / "docs" / "learned" / "tripwires.md"
    assert tripwires_path.exists()
    content = tripwires_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED FILE" in content
    assert "erk docs sync" in content
    assert "# Tripwires" in content


def test_learned_docs_install_idempotent(tmp_path: Path) -> None:
    """Test that installing twice is idempotent and returns appropriate message."""
    cap = LearnedDocsCapability()

    # First install
    result1 = cap.install(tmp_path)
    assert result1.success is True
    assert "Created" in result1.message

    # Second install
    result2 = cap.install(tmp_path)
    assert result2.success is True
    assert "already exists" in result2.message


def test_learned_docs_install_when_docs_exists_but_not_learned(tmp_path: Path) -> None:
    """Test that install works when docs/ exists but docs/learned/ doesn't."""
    (tmp_path / "docs").mkdir()
    cap = LearnedDocsCapability()

    result = cap.install(tmp_path)

    assert result.success is True
    assert (tmp_path / "docs" / "learned").is_dir()


def test_learned_docs_installation_check_description() -> None:
    """Test that LearnedDocsCapability has an installation check description."""
    cap = LearnedDocsCapability()
    assert "docs/learned" in cap.installation_check_description


def test_learned_docs_artifacts() -> None:
    """Test that LearnedDocsCapability lists its artifacts."""
    cap = LearnedDocsCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 6
    paths = [a.path for a in artifacts]
    assert "docs/learned/" in paths
    assert "docs/learned/README.md" in paths
    assert "docs/learned/index.md" in paths
    assert "docs/learned/tripwires.md" in paths
    assert ".claude/skills/learned-docs/" in paths
    assert ".claude/skills/learned-docs/SKILL.md" in paths

    # Verify artifact types
    for artifact in artifacts:
        if artifact.path in ("docs/learned/", ".claude/skills/learned-docs/"):
            assert artifact.artifact_type == "directory"
        else:
            assert artifact.artifact_type == "file"


# =============================================================================
# Tests for CapabilityArtifact
# =============================================================================


def test_capability_artifact_is_frozen() -> None:
    """Test that CapabilityArtifact is immutable."""
    artifact = CapabilityArtifact(path="test/path", artifact_type="file")
    assert artifact.path == "test/path"
    assert artifact.artifact_type == "file"


# =============================================================================
# Tests for Custom Capability Registration
# =============================================================================


class _TestCapability(Capability):
    """A test capability for testing the registration system."""

    @property
    def name(self) -> str:
        return "test-cap"

    @property
    def description(self) -> str:
        return "Test capability"

    @property
    def installation_check_description(self) -> str:
        return ".test-cap marker file exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [CapabilityArtifact(path=".test-cap", artifact_type="file")]

    def is_installed(self, repo_root: Path) -> bool:
        return (repo_root / ".test-cap").exists()

    def install(self, repo_root: Path) -> CapabilityResult:
        marker = repo_root / ".test-cap"
        if marker.exists():
            return CapabilityResult(success=True, message="Already installed")
        marker.write_text("installed", encoding="utf-8")
        return CapabilityResult(success=True, message="Installed")


def test_custom_capability_install_and_is_installed(tmp_path: Path) -> None:
    """Test that a custom capability can be installed and detected."""
    cap = _TestCapability()

    # Not installed initially
    assert cap.is_installed(tmp_path) is False

    # Install it
    result = cap.install(tmp_path)
    assert result.success is True
    assert result.message == "Installed"

    # Now it's installed
    assert cap.is_installed(tmp_path) is True

    # Install again - idempotent
    result2 = cap.install(tmp_path)
    assert result2.success is True
    assert result2.message == "Already installed"


# =============================================================================
# Tests for Skill Capabilities
# =============================================================================


def test_dignified_python_capability_properties() -> None:
    """Test DignifiedPythonCapability has correct properties."""
    cap = DignifiedPythonCapability()
    assert cap.name == "dignified-python"
    assert cap.skill_name == "dignified-python"
    assert "Python" in cap.description
    assert ".claude/skills/dignified-python" in cap.installation_check_description


def test_fake_driven_testing_capability_properties() -> None:
    """Test FakeDrivenTestingCapability has correct properties."""
    cap = FakeDrivenTestingCapability()
    assert cap.name == "fake-driven-testing"
    assert cap.skill_name == "fake-driven-testing"
    assert "test" in cap.description.lower()


def test_skill_capability_is_installed_false_when_missing(tmp_path: Path) -> None:
    """Test skill capability is_installed returns False when skill directory missing."""
    cap = DignifiedPythonCapability()
    assert cap.is_installed(tmp_path) is False


def test_skill_capability_is_installed_true_when_exists(tmp_path: Path) -> None:
    """Test skill capability is_installed returns True when skill directory exists."""
    (tmp_path / ".claude" / "skills" / "dignified-python").mkdir(parents=True)
    cap = DignifiedPythonCapability()
    assert cap.is_installed(tmp_path) is True


def test_skill_capability_artifacts() -> None:
    """Test that skill capabilities list correct artifacts."""
    cap = DignifiedPythonCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/skills/dignified-python/"
    assert artifacts[0].artifact_type == "directory"


def test_all_skill_capabilities_registered() -> None:
    """Test that all skill capabilities are registered."""
    expected_skills = [
        "dignified-python",
        "fake-driven-testing",
    ]
    for skill_name in expected_skills:
        cap = get_capability(skill_name)
        assert cap is not None, f"Skill '{skill_name}' not registered"
        assert cap.name == skill_name


# =============================================================================
# Tests for Workflow Capabilities
# =============================================================================


def test_erk_impl_workflow_capability_properties() -> None:
    """Test ErkImplWorkflowCapability has correct properties."""
    cap = ErkImplWorkflowCapability()
    assert cap.name == "erk-impl-workflow"
    assert "GitHub Action" in cap.description
    assert "erk-impl.yml" in cap.installation_check_description


def test_erk_impl_workflow_artifacts() -> None:
    """Test ErkImplWorkflowCapability lists all artifacts."""
    cap = ErkImplWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 3
    paths = [a.path for a in artifacts]
    assert ".github/workflows/erk-impl.yml" in paths
    assert ".github/actions/setup-claude-code/" in paths
    assert ".github/actions/setup-claude-erk/" in paths


def test_erk_impl_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = ErkImplWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path) is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "erk-impl.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path) is True


def test_workflow_capability_registered() -> None:
    """Test that workflow capability is registered."""
    cap = get_capability("erk-impl-workflow")
    assert cap is not None
    assert cap.name == "erk-impl-workflow"


# =============================================================================
# Tests for Agent Capabilities
# =============================================================================


def test_devrun_agent_capability_properties() -> None:
    """Test DevrunAgentCapability has correct properties."""
    cap = DevrunAgentCapability()
    assert cap.name == "devrun-agent"
    assert "pytest" in cap.description or "execution" in cap.description.lower()
    assert "devrun" in cap.installation_check_description


def test_devrun_agent_artifacts() -> None:
    """Test DevrunAgentCapability lists correct artifacts."""
    cap = DevrunAgentCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/agents/devrun.md"
    assert artifacts[0].artifact_type == "file"


def test_devrun_agent_is_installed(tmp_path: Path) -> None:
    """Test agent is_installed checks for agent file."""
    cap = DevrunAgentCapability()

    # Not installed when agent file missing
    assert cap.is_installed(tmp_path) is False

    # Installed when agent file exists
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "devrun.md").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path) is True


def test_agent_capability_registered() -> None:
    """Test that agent capability is registered."""
    cap = get_capability("devrun-agent")
    assert cap is not None
    assert cap.name == "devrun-agent"


# =============================================================================
# Tests for Permission Capabilities
# =============================================================================


def test_erk_bash_permissions_capability_properties() -> None:
    """Test ErkBashPermissionsCapability has correct properties."""
    cap = ErkBashPermissionsCapability()
    assert cap.name == "erk-bash-permissions"
    assert "Bash(erk:*)" in cap.description
    assert "settings.json" in cap.installation_check_description


def test_erk_bash_permissions_artifacts() -> None:
    """Test ErkBashPermissionsCapability lists correct artifacts."""
    cap = ErkBashPermissionsCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/settings.json"
    assert artifacts[0].artifact_type == "file"


def test_erk_bash_permissions_is_installed_false_when_no_settings(tmp_path: Path) -> None:
    """Test is_installed returns False when settings.json doesn't exist."""
    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path) is False


def test_erk_bash_permissions_is_installed_false_when_not_in_allow(tmp_path: Path) -> None:
    """Test is_installed returns False when permission not in allow list."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"permissions": {"allow": []}}), encoding="utf-8")

    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path) is False


def test_erk_bash_permissions_is_installed_true_when_present(tmp_path: Path) -> None:
    """Test is_installed returns True when permission is in allow list."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(erk:*)"]}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path) is True


def test_erk_bash_permissions_install_creates_settings(tmp_path: Path) -> None:
    """Test install creates settings.json if it doesn't exist."""
    import json

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert ".claude/settings.json" in result.created_files

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "Bash(erk:*)" in settings["permissions"]["allow"]


def test_erk_bash_permissions_install_adds_to_existing(tmp_path: Path) -> None:
    """Test install adds permission to existing settings.json."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Read(/tmp/*)"]}, "hooks": {}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert "Added" in result.message

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "Bash(erk:*)" in settings["permissions"]["allow"]
    assert "Read(/tmp/*)" in settings["permissions"]["allow"]
    assert "hooks" in settings  # Preserves existing keys


def test_erk_bash_permissions_install_idempotent(tmp_path: Path) -> None:
    """Test install is idempotent when permission already exists."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(erk:*)"]}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert "already" in result.message

    # Verify it wasn't duplicated
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["permissions"]["allow"].count("Bash(erk:*)") == 1


def test_permission_capability_registered() -> None:
    """Test that permission capability is registered."""
    cap = get_capability("erk-bash-permissions")
    assert cap is not None
    assert cap.name == "erk-bash-permissions"
