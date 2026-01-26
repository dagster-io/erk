"""Capability registry - hardcoded list of all capabilities."""

from functools import cache

from erk.capabilities.agents.devrun import DevrunAgentCapability
from erk.capabilities.code_reviews_system import CodeReviewsSystemCapability
from erk.capabilities.erk_bash_permissions import ErkBashPermissionsCapability
from erk.capabilities.hooks import HooksCapability
from erk.capabilities.learned_docs import LearnedDocsCapability
from erk.capabilities.reminders.devrun import DevrunReminderCapability
from erk.capabilities.reminders.dignified_python import DignifiedPythonReminderCapability
from erk.capabilities.reminders.explore_docs import ExploreDocsReminderCapability
from erk.capabilities.reminders.tripwires import TripwiresReminderCapability
from erk.capabilities.reviews.dignified_code_simplifier import (
    DignifiedCodeSimplifierReviewDefCapability,
)
from erk.capabilities.reviews.dignified_python import DignifiedPythonReviewDefCapability
from erk.capabilities.reviews.tripwires import TripwiresReviewDefCapability
from erk.capabilities.ruff_format import RuffFormatCapability
from erk.capabilities.skills.dignified_python import DignifiedPythonCapability
from erk.capabilities.skills.fake_driven_testing import FakeDrivenTestingCapability
from erk.capabilities.statusline import StatuslineCapability
from erk.capabilities.workflows.erk_impl import ErkImplWorkflowCapability
from erk.capabilities.workflows.learn import LearnWorkflowCapability
from erk.core.capabilities.base import Capability


@cache
def _all_capabilities() -> tuple[Capability, ...]:
    """Return all registered capabilities. Cached for performance."""
    return (
        LearnedDocsCapability(),
        DignifiedPythonCapability(),
        FakeDrivenTestingCapability(),
        # Code reviews system and individual review definitions
        CodeReviewsSystemCapability(),
        TripwiresReviewDefCapability(),
        DignifiedPythonReviewDefCapability(),
        DignifiedCodeSimplifierReviewDefCapability(),
        # Workflows
        ErkImplWorkflowCapability(),
        LearnWorkflowCapability(),
        DevrunAgentCapability(),
        ErkBashPermissionsCapability(),
        StatuslineCapability(claude_installation=None),
        HooksCapability(),
        RuffFormatCapability(),
        # Reminder capabilities - opt-in context injection (required=False)
        DevrunReminderCapability(),
        DignifiedPythonReminderCapability(),
        ExploreDocsReminderCapability(),
        TripwiresReminderCapability(),
    )


def get_capability(name: str) -> Capability | None:
    """Get a capability by name.

    Args:
        name: The capability name

    Returns:
        The capability if found, None otherwise
    """
    for cap in _all_capabilities():
        if cap.name == name:
            return cap
    return None


def list_capabilities() -> list[Capability]:
    """Get all registered capabilities.

    Returns:
        List of all registered capabilities, sorted alphabetically by name
    """
    return sorted(_all_capabilities(), key=lambda c: c.name)


def list_required_capabilities() -> list[Capability]:
    """Get all required capabilities (auto-installed during erk init).

    Returns:
        List of capabilities where required=True
    """
    return [cap for cap in _all_capabilities() if cap.required]


@cache
def get_managed_artifacts() -> dict[tuple[str, str], str]:
    """Get all artifacts managed by capabilities.

    Returns dict mapping (artifact_name, artifact_type) -> capability_name.
    This is the single source of truth for artifact management detection.
    """
    result: dict[tuple[str, str], str] = {}
    for cap in _all_capabilities():
        for artifact in cap.managed_artifacts:
            key = (artifact.name, artifact.artifact_type)
            if key not in result:
                result[key] = cap.name
    return result


def is_capability_managed(name: str, artifact_type: str) -> bool:
    """Check if an artifact is managed by a capability.

    Args:
        name: The artifact name (e.g., "dignified-python", "ruff-format-hook")
        artifact_type: The artifact type (e.g., "skill", "hook")

    Returns:
        True if the artifact is declared as managed by some capability
    """
    return (name, artifact_type) in get_managed_artifacts()
