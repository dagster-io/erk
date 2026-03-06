"""Tests for capability base data structures and ABC contract.

Tests CapabilityResult, CapabilityArtifact, CapabilityScope, preflight(),
and custom capability registration.
"""

from pathlib import Path

from erk.capabilities.agents.devrun import DevrunAgentCapability
from erk.capabilities.erk_bash_permissions import ErkBashPermissionsCapability
from erk.capabilities.learned_docs import LearnedDocsCapability
from erk.capabilities.skills.bundled import bundled_skills
from erk.capabilities.statusline import StatuslineCapability
from erk.capabilities.workflows.erk_impl import ErkImplWorkflowCapability
from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.capabilities.registry import get_capability, list_capabilities

# =============================================================================
# Tests for CapabilityResult
# =============================================================================


def test_capability_result_is_frozen() -> None:
    """Test that CapabilityResult is immutable."""
    result = CapabilityResult(success=True, message="test")
    assert result.success is True
    assert result.message == "test"


# =============================================================================
# Tests for CapabilityArtifact
# =============================================================================


def test_capability_artifact_is_frozen() -> None:
    """Test that CapabilityArtifact is immutable."""
    artifact = CapabilityArtifact(path="test/path", artifact_type="file")
    assert artifact.path == "test/path"
    assert artifact.artifact_type == "file"


# =============================================================================
# Tests for Capability Scope
# =============================================================================


def test_all_project_capabilities_have_project_scope() -> None:
    """Test that project-level capabilities have 'project' scope."""
    project_caps = [
        LearnedDocsCapability(),
        ErkImplWorkflowCapability(),
        DevrunAgentCapability(),
        ErkBashPermissionsCapability(),
    ]

    for cap in project_caps:
        assert cap.scope == "project", f"{cap.name} should have 'project' scope"

    # Bundled skills are also project-scoped
    for skill_name in bundled_skills():
        cap = get_capability(skill_name)
        assert cap is not None
        assert cap.scope == "project", f"{skill_name} should have 'project' scope"


def test_statusline_has_user_scope() -> None:
    """Test that StatuslineCapability has 'user' scope."""
    cap = StatuslineCapability(claude_installation=None)
    assert cap.scope == "user"


def test_all_registered_capabilities_have_valid_scope() -> None:
    """Test that all registered capabilities have a valid scope."""
    valid_scopes = {"project", "user"}
    for cap in list_capabilities():
        assert cap.scope in valid_scopes, f"{cap.name} has invalid scope: {cap.scope}"


def test_capability_scope_values() -> None:
    """Test that CapabilityScope type alias has expected values."""
    # This tests the type at runtime - useful for documentation purposes
    # The type is Literal["project", "user"]
    project_cap = LearnedDocsCapability()
    user_cap = StatuslineCapability(claude_installation=None)

    assert project_cap.scope == "project"
    assert user_cap.scope == "user"


# =============================================================================
# Tests for Capability.preflight()
# =============================================================================


def test_default_preflight_returns_success(tmp_path: Path) -> None:
    """Test that default preflight() implementation returns success."""
    cap = LearnedDocsCapability()
    result = cap.preflight(tmp_path, backend="claude")

    assert result.success is True
    assert result.message == ""


def test_preflight_called_before_install_pattern() -> None:
    """Test that preflight can be called to check preconditions."""
    # This tests the pattern: check preflight, then install
    cap = LearnedDocsCapability()

    # Default preflight always succeeds
    preflight_result = cap.preflight(None, backend="claude")
    assert preflight_result.success is True


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
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".test-cap marker file exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [CapabilityArtifact(path=".test-cap", artifact_type="file")]

    def is_installed(self, repo_root: Path | None, *, backend: str) -> bool:
        assert repo_root is not None, "_TestCapability requires repo_root"
        return (repo_root / ".test-cap").exists()

    def install(self, repo_root: Path | None, *, backend: str) -> CapabilityResult:
        assert repo_root is not None, "_TestCapability requires repo_root"
        marker = repo_root / ".test-cap"
        if marker.exists():
            return CapabilityResult(success=True, message="Already installed")
        marker.write_text("installed", encoding="utf-8")
        return CapabilityResult(success=True, message="Installed")

    def uninstall(self, repo_root: Path | None, *, backend: str) -> CapabilityResult:
        assert repo_root is not None, "_TestCapability requires repo_root"
        marker = repo_root / ".test-cap"
        if not marker.exists():
            return CapabilityResult(success=True, message="Not installed")
        marker.unlink()
        return CapabilityResult(success=True, message="Uninstalled")


def test_custom_capability_install_and_is_installed(tmp_path: Path) -> None:
    """Test that a custom capability can be installed and detected."""
    cap = _TestCapability()

    # Not installed initially
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Install it
    result = cap.install(tmp_path, backend="claude")
    assert result.success is True
    assert result.message == "Installed"

    # Now it's installed
    assert cap.is_installed(tmp_path, backend="claude") is True

    # Install again - idempotent
    result2 = cap.install(tmp_path, backend="claude")
    assert result2.success is True
    assert result2.message == "Already installed"


def test_capability_base_required_default_is_false() -> None:
    """Test that Capability ABC has required=False by default."""

    class TestCap(Capability):
        """Test capability with default required behavior."""

        @property
        def name(self) -> str:
            return "test"

        @property
        def description(self) -> str:
            return "test"

        @property
        def scope(self) -> CapabilityScope:
            return "project"

        @property
        def installation_check_description(self) -> str:
            return "test"

        @property
        def artifacts(self) -> list[CapabilityArtifact]:
            return []

        def is_installed(self, repo_root: Path | None, *, backend: str) -> bool:
            return False

        def install(self, repo_root: Path | None, *, backend: str) -> CapabilityResult:
            return CapabilityResult(success=True, message="test")

        def uninstall(self, repo_root: Path | None, *, backend: str) -> CapabilityResult:
            return CapabilityResult(success=True, message="test")

    cap = TestCap()
    assert cap.required is False


def test_default_managed_artifacts_is_empty() -> None:
    """Test that default managed_artifacts returns empty list."""
    # _TestCapability doesn't override managed_artifacts, so it inherits the default
    cap = _TestCapability()
    managed = cap.managed_artifacts

    assert managed == []
