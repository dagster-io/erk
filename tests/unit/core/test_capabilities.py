"""Tests for the capability system.

These tests verify:
1. The Capability ABC contract
2. The registry functions (register, get, list)
3. The LearnedDocsCapability implementation
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
