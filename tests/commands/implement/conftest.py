"""Shared test fixtures for implement command tests."""

from datetime import UTC, datetime

from erk_shared.plan_store.types import Plan, PlanState


def create_sample_plan_issue(issue_number: str = "42") -> Plan:
    """Create a sample plan issue for testing."""
    return Plan(
        plan_identifier=issue_number,
        title="Add Authentication Feature",
        body="# Implementation Plan\n\nAdd user authentication to the application.",
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan", "enhancement"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
