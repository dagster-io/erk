"""Shared test fixtures for implement command tests."""

from erk_shared.plan_store.types import Plan
from tests.test_utils.plan_helpers import make_test_plan


def create_sample_plan_issue(issue_number: str = "42") -> Plan:
    """Create a sample plan issue for testing.

    This is a thin wrapper around make_test_plan with implement-specific defaults.
    """
    return make_test_plan(
        issue_number,
        title="Add Authentication Feature",
        body="# Implementation Plan\n\nAdd user authentication to the application.",
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan", "enhancement"],
        assignees=["alice"],
    )
