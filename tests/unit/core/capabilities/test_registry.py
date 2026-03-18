"""Tests for capability registry functions.

Tests get_capability, list_capabilities, list_required_capabilities,
get_managed_artifacts, and is_capability_managed.
"""

from erk.capabilities.agents.devrun import DevrunAgentCapability
from erk.capabilities.erk_bash_permissions import ErkBashPermissionsCapability
from erk.capabilities.learned_docs import LearnedDocsCapability
from erk.capabilities.skills.bundled import bundled_skills, is_required_bundled_skill
from erk.capabilities.statusline import StatuslineCapability
from erk.capabilities.workflows.erk_impl import ErkImplWorkflowCapability
from erk.capabilities.workflows.learn import LearnWorkflowCapability
from erk.capabilities.workflows.one_shot import OneShotWorkflowCapability
from erk.capabilities.workflows.pr_address import PrAddressWorkflowCapability
from erk.capabilities.workflows.pr_rebase import PrRebaseWorkflowCapability
from erk.core.capabilities.registry import (
    get_capability,
    get_managed_artifacts,
    is_capability_managed,
    list_capabilities,
    list_required_capabilities,
)

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


def test_list_capabilities_returns_sorted_alphabetically() -> None:
    """Test that list_capabilities returns capabilities sorted alphabetically by name."""
    caps = list_capabilities()
    names = [cap.name for cap in caps]
    assert names == sorted(names)


# =============================================================================
# Tests for Required Capabilities
# =============================================================================


def test_list_required_capabilities_returns_only_required() -> None:
    """Test that list_required_capabilities returns only capabilities with required=True."""
    required_caps = list_required_capabilities()

    # All returned capabilities should have required=True
    for cap in required_caps:
        assert cap.required is True, f"{cap.name} has required=False but was returned"


def test_list_required_capabilities_includes_hooks() -> None:
    """Test that HooksCapability is in the list of required capabilities."""
    required_caps = list_required_capabilities()
    names = [cap.name for cap in required_caps]

    assert "erk-hooks" in names


def test_default_capabilities_not_required() -> None:
    """Test that default capabilities are NOT required."""
    # Most capabilities should be optional
    optional_caps = [
        LearnedDocsCapability(),
        DevrunAgentCapability(),
        ErkBashPermissionsCapability(),
        StatuslineCapability(claude_installation=None),
    ]

    for cap in optional_caps:
        assert cap.required is False, f"{cap.name} should not be required"

    # Bundled skills not in the required set should be optional
    for skill_name in bundled_skills():
        if is_required_bundled_skill(skill_name):
            continue
        cap = get_capability(skill_name)
        assert cap is not None
        assert cap.required is False, f"{skill_name} should not be required"


def test_workflow_capabilities_are_required() -> None:
    """Test that all workflow capabilities are required."""
    workflow_caps = [
        ErkImplWorkflowCapability(),
        LearnWorkflowCapability(),
        OneShotWorkflowCapability(),
        PrAddressWorkflowCapability(),
        PrRebaseWorkflowCapability(),
    ]

    for cap in workflow_caps:
        assert cap.required is True, f"{cap.name} should be required"


# =============================================================================
# Tests for get_managed_artifacts and is_capability_managed
# =============================================================================


def test_get_managed_artifacts_returns_dict() -> None:
    """Test that get_managed_artifacts returns a dict of all managed artifacts."""
    managed = get_managed_artifacts()

    assert isinstance(managed, dict)
    # Should contain at least the skills we know about
    assert ("fake-driven-testing", "skill") in managed


def test_get_managed_artifacts_contains_all_artifact_types() -> None:
    """Test that get_managed_artifacts includes various artifact types."""
    managed = get_managed_artifacts()

    # Check for different types
    artifact_types = {atype for _, atype in managed.keys()}
    assert "skill" in artifact_types
    assert "agent" in artifact_types
    assert "workflow" in artifact_types
    assert "action" in artifact_types
    assert "hook" in artifact_types
    assert "review" in artifact_types


def test_get_managed_artifacts_maps_to_capability_name() -> None:
    """Test that get_managed_artifacts values are capability names."""
    managed = get_managed_artifacts()

    # Check a few known mappings
    assert managed[("fake-driven-testing", "skill")] == "fake-driven-testing"
    assert managed[("devrun", "agent")] == "devrun-agent"
    assert managed[("plan-implement", "workflow")] == "erk-impl-workflow"


def test_is_capability_managed_returns_true_for_known_artifacts() -> None:
    """Test is_capability_managed returns True for artifacts declared by capabilities."""
    assert is_capability_managed("fake-driven-testing", "skill") is True
    assert is_capability_managed("devrun", "agent") is True
    assert is_capability_managed("plan-implement", "workflow") is True
    assert is_capability_managed("user-prompt-hook", "hook") is True
    assert is_capability_managed("ruff-format-hook", "hook") is True
    assert is_capability_managed("tripwires", "review") is True


def test_is_capability_managed_returns_false_for_unknown_artifacts() -> None:
    """Test is_capability_managed returns False for unknown artifacts."""
    assert is_capability_managed("unknown-skill", "skill") is False
    assert is_capability_managed("custom-agent", "agent") is False
    assert is_capability_managed("user-workflow", "workflow") is False


def test_is_capability_managed_type_matters() -> None:
    """Test that is_capability_managed checks both name AND type."""
    # fake-driven-testing is a skill, not an agent
    assert is_capability_managed("fake-driven-testing", "skill") is True
    assert is_capability_managed("fake-driven-testing", "agent") is False
