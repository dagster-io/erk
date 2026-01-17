"""Shared test fixtures for implement command tests."""

from datetime import UTC, datetime

from erk_shared.plan_store.types import Plan
from tests.test_utils.plan_helpers import make_test_plan


def create_sample_plan_issue(issue_number: str = "42") -> Plan:
    """Create a sample plan issue for testing."""
    return make_test_plan(
        issue_number,
        title="Add Authentication Feature",
        body="# Implementation Plan\n\nAdd user authentication to the application.",
        labels=["erk-plan", "enhancement"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
