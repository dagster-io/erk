"""Tests for workflow capabilities.

Tests ErkImplWorkflowCapability, LearnWorkflowCapability,
OneShotWorkflowCapability, PrAddressWorkflowCapability,
and PrRebaseWorkflowCapability.
"""

from pathlib import Path

from erk.capabilities.workflows.erk_impl import ErkImplWorkflowCapability
from erk.capabilities.workflows.learn import LearnWorkflowCapability
from erk.capabilities.workflows.one_shot import OneShotWorkflowCapability
from erk.capabilities.workflows.pr_address import PrAddressWorkflowCapability
from erk.capabilities.workflows.pr_rebase import PrRebaseWorkflowCapability
from erk.core.capabilities.registry import get_capability

# =============================================================================
# Tests for ErkImplWorkflowCapability
# =============================================================================


def test_erk_impl_workflow_capability_properties() -> None:
    """Test ErkImplWorkflowCapability has correct properties."""
    cap = ErkImplWorkflowCapability()
    assert cap.name == "erk-impl-workflow"
    assert "GitHub Action" in cap.description
    assert "plan-implement.yml" in cap.installation_check_description


def test_erk_impl_workflow_artifacts() -> None:
    """Test ErkImplWorkflowCapability lists all artifacts."""
    cap = ErkImplWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 4
    paths = [a.path for a in artifacts]
    assert ".github/workflows/plan-implement.yml" in paths
    assert ".github/actions/setup-claude-code/" in paths
    assert ".github/actions/setup-claude-erk/" in paths
    assert ".github/actions/erk-remote-setup/" in paths


def test_erk_impl_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = ErkImplWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "plan-implement.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_workflow_capability_registered() -> None:
    """Test that workflow capability is registered."""
    cap = get_capability("erk-impl-workflow")
    assert cap is not None
    assert cap.name == "erk-impl-workflow"


# =============================================================================
# Tests for LearnWorkflowCapability
# =============================================================================


def test_learn_workflow_capability_properties() -> None:
    """Test LearnWorkflowCapability has correct properties."""
    cap = LearnWorkflowCapability()
    assert cap.name == "learn-workflow"
    assert "documentation" in cap.description.lower() or "learn" in cap.description.lower()
    assert "learn.yml" in cap.installation_check_description


def test_learn_workflow_artifacts() -> None:
    """Test LearnWorkflowCapability lists correct artifacts."""
    cap = LearnWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    paths = [a.path for a in artifacts]
    assert ".github/workflows/learn.yml" in paths


def test_learn_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = LearnWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "learn.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_learn_workflow_capability_registered() -> None:
    """Test that learn workflow capability is registered."""
    cap = get_capability("learn-workflow")
    assert cap is not None
    assert cap.name == "learn-workflow"


# =============================================================================
# Tests for OneShotWorkflowCapability
# =============================================================================


def test_one_shot_workflow_capability_properties() -> None:
    """Test OneShotWorkflowCapability has correct properties."""
    cap = OneShotWorkflowCapability()
    assert cap.name == "one-shot-workflow"
    assert "one-shot" in cap.description.lower()
    assert "one-shot.yml" in cap.installation_check_description


def test_one_shot_workflow_artifacts() -> None:
    """Test OneShotWorkflowCapability lists correct artifacts."""
    cap = OneShotWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    paths = [a.path for a in artifacts]
    assert ".github/workflows/one-shot.yml" in paths


def test_one_shot_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = OneShotWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "one-shot.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_one_shot_workflow_capability_registered() -> None:
    """Test that one-shot workflow capability is registered."""
    cap = get_capability("one-shot-workflow")
    assert cap is not None
    assert cap.name == "one-shot-workflow"


def test_one_shot_workflow_managed_artifacts() -> None:
    """Test that OneShotWorkflowCapability declares its managed artifacts."""
    cap = OneShotWorkflowCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 1
    assert managed[0].name == "one-shot"
    assert managed[0].artifact_type == "workflow"


# =============================================================================
# Tests for PrAddressWorkflowCapability
# =============================================================================


def test_pr_address_workflow_capability_properties() -> None:
    """Test PrAddressWorkflowCapability has correct properties."""
    cap = PrAddressWorkflowCapability()
    assert cap.name == "pr-address-workflow"
    assert "pr" in cap.description.lower() or "review" in cap.description.lower()
    assert "pr-address.yml" in cap.installation_check_description


def test_pr_address_workflow_artifacts() -> None:
    """Test PrAddressWorkflowCapability lists correct artifacts."""
    cap = PrAddressWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    paths = [a.path for a in artifacts]
    assert ".github/workflows/pr-address.yml" in paths


def test_pr_address_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = PrAddressWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "pr-address.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_pr_address_workflow_capability_registered() -> None:
    """Test that pr-address workflow capability is registered."""
    cap = get_capability("pr-address-workflow")
    assert cap is not None
    assert cap.name == "pr-address-workflow"


def test_pr_address_workflow_managed_artifacts() -> None:
    """Test that PrAddressWorkflowCapability declares its managed artifacts."""
    cap = PrAddressWorkflowCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 1
    assert managed[0].name == "pr-address"
    assert managed[0].artifact_type == "workflow"


# =============================================================================
# Tests for PrRebaseWorkflowCapability
# =============================================================================


def test_pr_rebase_workflow_capability_properties() -> None:
    """Test PrRebaseWorkflowCapability has correct properties."""
    cap = PrRebaseWorkflowCapability()
    assert cap.name == "pr-rebase-workflow"
    assert "rebase" in cap.description.lower() or "rebasing" in cap.description.lower()
    assert "pr-rebase.yml" in cap.installation_check_description


def test_pr_rebase_workflow_artifacts() -> None:
    """Test PrRebaseWorkflowCapability lists correct artifacts."""
    cap = PrRebaseWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    paths = [a.path for a in artifacts]
    assert ".github/workflows/pr-rebase.yml" in paths


def test_pr_rebase_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = PrRebaseWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "pr-rebase.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_pr_rebase_workflow_capability_registered() -> None:
    """Test that pr-rebase workflow capability is registered."""
    cap = get_capability("pr-rebase-workflow")
    assert cap is not None
    assert cap.name == "pr-rebase-workflow"


def test_pr_rebase_workflow_managed_artifacts() -> None:
    """Test that PrRebaseWorkflowCapability declares its managed artifacts."""
    cap = PrRebaseWorkflowCapability()
    managed = cap.managed_artifacts

    assert len(managed) == 1
    assert managed[0].name == "pr-rebase"
    assert managed[0].artifact_type == "workflow"
