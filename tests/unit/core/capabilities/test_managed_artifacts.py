"""Tests for managed_artifacts property on individual capabilities.

Tests that each capability type correctly declares its managed artifacts.
"""

from erk.capabilities.agents.devrun import DevrunAgentCapability
from erk.capabilities.hooks import HooksCapability
from erk.capabilities.learned_docs import LearnedDocsCapability
from erk.capabilities.ruff_format import RuffFormatCapability
from erk.capabilities.workflows.erk_impl import ErkImplWorkflowCapability
from erk.core.capabilities.registry import get_capability

# =============================================================================
# Tests for ManagedArtifact and managed_artifacts Property
# =============================================================================


def test_skill_capability_managed_artifacts() -> None:
    """Test that SkillCapability declares its managed artifacts."""
    cap = get_capability("dignified-python")
    assert cap is not None
    managed = cap.managed_artifacts

    assert len(managed) == 1
    assert managed[0].name == "dignified-python"
    assert managed[0].artifact_type == "skill"


def test_devrun_agent_managed_artifacts() -> None:
    """Test that DevrunAgentCapability declares its managed artifacts."""
    cap = DevrunAgentCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 1
    assert managed[0].name == "devrun"
    assert managed[0].artifact_type == "agent"


def test_workflow_capability_managed_artifacts() -> None:
    """Test that ErkImplWorkflowCapability declares its managed artifacts."""
    cap = ErkImplWorkflowCapability()
    managed = cap.managed_artifacts

    # Workflow + 3 actions
    assert len(managed) == 4
    names = {(a.name, a.artifact_type) for a in managed}
    assert ("plan-implement", "workflow") in names
    assert ("setup-claude-code", "action") in names
    assert ("setup-claude-erk", "action") in names
    assert ("erk-remote-setup", "action") in names


def test_hooks_capability_managed_artifacts() -> None:
    """Test that HooksCapability declares its managed artifacts."""
    cap = HooksCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 2
    names = {(a.name, a.artifact_type) for a in managed}
    assert ("user-prompt-hook", "hook") in names
    assert ("exit-plan-mode-hook", "hook") in names


def test_ruff_format_capability_managed_artifacts() -> None:
    """Test that RuffFormatCapability declares its managed artifacts."""
    cap = RuffFormatCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 1
    assert managed[0].name == "ruff-format-hook"
    assert managed[0].artifact_type == "hook"


def test_learned_docs_capability_managed_artifacts() -> None:
    """Test that LearnedDocsCapability declares its managed artifacts."""
    cap = LearnedDocsCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 3
    names = {(a.name, a.artifact_type) for a in managed}
    assert ("learned-docs", "skill") in names
    assert ("learn", "command") in names
    assert ("learn", "agent") in names
