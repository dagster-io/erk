"""Capability registry - hardcoded list of all capabilities."""

from functools import cache

from erk.core.capabilities.agents import DevrunAgentCapability
from erk.core.capabilities.base import Capability
from erk.core.capabilities.dignified_review import DignifiedReviewCapability
from erk.core.capabilities.hooks import HooksCapability
from erk.core.capabilities.learned_docs import LearnedDocsCapability
from erk.core.capabilities.permissions import ErkBashPermissionsCapability
from erk.core.capabilities.ruff_format import RuffFormatCapability
from erk.core.capabilities.skills import DignifiedPythonCapability, FakeDrivenTestingCapability
from erk.core.capabilities.statusline import StatuslineCapability
from erk.core.capabilities.workflows import ErkImplWorkflowCapability


@cache
def _all_capabilities() -> tuple[Capability, ...]:
    """Return all registered capabilities. Cached for performance."""
    return (
        LearnedDocsCapability(),
        DignifiedPythonCapability(),
        FakeDrivenTestingCapability(),
        DignifiedReviewCapability(),
        ErkImplWorkflowCapability(),
        DevrunAgentCapability(),
        ErkBashPermissionsCapability(),
        StatuslineCapability(claude_installation=None),
        HooksCapability(),
        RuffFormatCapability(),
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
        List of all registered capabilities
    """
    return list(_all_capabilities())


def list_required_capabilities() -> list[Capability]:
    """Get all required capabilities (auto-installed during erk init).

    Returns:
        List of capabilities where required=True
    """
    return [cap for cap in _all_capabilities() if cap.required]
