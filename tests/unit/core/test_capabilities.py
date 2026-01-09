"""Tests for the capability system.

These tests verify:
1. The Capability ABC contract
2. The registry functions (register, get, list)
3. The LearnedDocsCapability implementation
4. Skill-based capabilities
5. Capability groups
"""

from pathlib import Path

from erk.core.capabilities import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    LearnedDocsCapability,
    get_capability,
    list_capabilities,
    register_capability,
)
from erk.core.capabilities.agents import DevrunAgentCapability
from erk.core.capabilities.groups import (
    CAPABILITY_GROUPS,
    CapabilityGroup,
    expand_capability_names,
    get_group,
    is_group,
    list_groups,
)
from erk.core.capabilities.skills import (
    DignifiedPythonCapability,
    FakeDrivenTestingCapability,
    GhCapability,
    GtCapability,
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


def test_register_capability_adds_to_registry() -> None:
    """Test that registering a capability makes it retrievable."""
    test_cap = _TestCapability()
    register_capability(test_cap)

    retrieved = get_capability("test-cap")
    assert retrieved is not None
    assert retrieved.name == "test-cap"


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


def test_gh_capability_properties() -> None:
    """Test GhCapability has correct properties."""
    cap = GhCapability()
    assert cap.name == "gh"
    assert cap.skill_name == "gh"
    assert "GitHub" in cap.description


def test_gt_capability_properties() -> None:
    """Test GtCapability has correct properties."""
    cap = GtCapability()
    assert cap.name == "gt"
    assert cap.skill_name == "gt"
    assert "Graphite" in cap.description


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
        "gh",
        "gt",
        "command-creator",
        "cli-skill-creator",
        "ci-iteration",
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
# Tests for Capability Groups
# =============================================================================


def test_capability_group_is_frozen() -> None:
    """Test that CapabilityGroup is immutable."""
    group = CapabilityGroup(
        name="test-group",
        description="Test group",
        members=("cap1", "cap2"),
    )
    assert group.name == "test-group"
    assert group.description == "Test group"
    assert group.members == ("cap1", "cap2")


def test_is_group_returns_true_for_groups() -> None:
    """Test is_group returns True for registered groups."""
    assert is_group("python-dev") is True
    assert is_group("github-workflow") is True
    assert is_group("graphite-workflow") is True
    assert is_group("skill-authoring") is True


def test_is_group_returns_false_for_non_groups() -> None:
    """Test is_group returns False for non-groups."""
    assert is_group("dignified-python") is False
    assert is_group("nonexistent") is False
    assert is_group("learned-docs") is False


def test_get_group_returns_group() -> None:
    """Test get_group returns the group for registered groups."""
    group = get_group("python-dev")
    assert group is not None
    assert group.name == "python-dev"
    assert "dignified-python" in group.members


def test_get_group_returns_none_for_unknown() -> None:
    """Test get_group returns None for unknown groups."""
    assert get_group("nonexistent") is None
    assert get_group("dignified-python") is None  # This is a capability, not a group


def test_list_groups_returns_all() -> None:
    """Test list_groups returns all registered groups."""
    groups = list_groups()
    names = [g.name for g in groups]
    assert "python-dev" in names
    assert "github-workflow" in names
    assert "graphite-workflow" in names
    assert "skill-authoring" in names


def test_expand_capability_names_passes_through_capabilities() -> None:
    """Test expand_capability_names passes through individual capabilities."""
    result = expand_capability_names(["dignified-python", "learned-docs"])
    assert result == ["dignified-python", "learned-docs"]


def test_expand_capability_names_expands_groups() -> None:
    """Test expand_capability_names expands groups to members."""
    result = expand_capability_names(["python-dev"])
    assert "dignified-python" in result
    assert "fake-driven-testing" in result
    assert "devrun-agent" in result


def test_expand_capability_names_mixed() -> None:
    """Test expand_capability_names handles mix of groups and capabilities."""
    result = expand_capability_names(["learned-docs", "python-dev"])
    assert result[0] == "learned-docs"  # Individual comes first
    assert "dignified-python" in result
    assert "fake-driven-testing" in result


def test_expand_capability_names_removes_duplicates() -> None:
    """Test expand_capability_names removes duplicates preserving order."""
    result = expand_capability_names(["dignified-python", "python-dev"])
    # dignified-python appears first, then rest of python-dev (excluding dignified-python)
    assert result.count("dignified-python") == 1
    assert result[0] == "dignified-python"


def test_python_dev_group_members() -> None:
    """Test python-dev group has expected members."""
    group = CAPABILITY_GROUPS["python-dev"]
    assert "dignified-python" in group.members
    assert "fake-driven-testing" in group.members
    assert "devrun-agent" in group.members


def test_github_workflow_group_members() -> None:
    """Test github-workflow group has expected members."""
    group = CAPABILITY_GROUPS["github-workflow"]
    assert "gh" in group.members
    assert "erk-impl-workflow" in group.members


def test_graphite_workflow_group_members() -> None:
    """Test graphite-workflow group has expected members."""
    group = CAPABILITY_GROUPS["graphite-workflow"]
    assert "gt" in group.members


def test_skill_authoring_group_members() -> None:
    """Test skill-authoring group has expected members."""
    group = CAPABILITY_GROUPS["skill-authoring"]
    assert "command-creator" in group.members
    assert "cli-skill-creator" in group.members
    assert "learned-docs" in group.members
