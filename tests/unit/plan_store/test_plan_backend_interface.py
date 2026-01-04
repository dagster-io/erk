"""Shared interface tests for PlanBackend implementations.

These parameterized tests verify that both GitHubPlanStore and FakeLinearPlanBackend
satisfy the PlanBackend ABC interface with consistent behavior.

Purpose:
- Validate the ABC abstraction works for fundamentally different backends
- Catch interface drift between implementations
- Ensure provider-agnostic code works with any backend

Test Matrix:
| Operation      | GitHub Backend         | Linear Backend        |
|----------------|------------------------|-----------------------|
| Plan IDs       | Integer-as-string      | UUID strings          |
| States         | 2 (OPEN, CLOSED)       | 5 -> mapped to 2      |
| Assignees      | List                   | Single -> list        |
| Comment IDs    | Integer-as-string      | UUID strings          |
| Metadata       | YAML in body           | custom_fields         |
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.fake_linear import FakeLinearPlanBackend, LinearIssue
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import PlanQuery, PlanState
from tests.test_utils.github_helpers import create_test_issue

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(params=["github", "linear"])
def plan_backend(request: pytest.FixtureRequest) -> PlanBackend:
    """Parameterized fixture providing both backend implementations.

    Each test using this fixture runs twice:
    1. With GitHubPlanStore (backed by FakeGitHubIssues)
    2. With FakeLinearPlanBackend
    """
    if request.param == "github":
        fake_issues = FakeGitHubIssues(username="testuser", labels={"erk-plan"})
        return GitHubPlanStore(fake_issues)
    else:
        return FakeLinearPlanBackend()


@pytest.fixture(params=["github", "linear"])
def backend_with_plan(request: pytest.FixtureRequest) -> tuple[PlanBackend, str]:
    """Fixture providing backend with a pre-existing plan.

    Returns:
        Tuple of (backend, plan_id)
    """
    if request.param == "github":
        issue = create_test_issue(
            number=42,
            title="Existing Plan",
            body="Plan content",
            labels=["erk-plan"],
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 16, 12, 0, 0, tzinfo=UTC),
        )
        fake_issues = FakeGitHubIssues(issues={42: issue})
        return GitHubPlanStore(fake_issues), "42"
    else:
        now = datetime.now(UTC)
        issue = LinearIssue(
            id="LIN-existing",
            title="Existing Plan",
            description="Plan content",
            state="todo",
            url="https://linear.app/team/issue/LIN-existing",
            labels=("erk-plan",),
            assignee=None,
            created_at=now,
            updated_at=now,
            custom_fields={},
        )
        return FakeLinearPlanBackend(issues={"LIN-existing": issue}), "LIN-existing"


# =============================================================================
# Interface contract tests - both backends must pass these
# =============================================================================


def test_get_provider_name_returns_string(plan_backend: PlanBackend) -> None:
    """Both backends return a non-empty provider name string."""
    name = plan_backend.get_provider_name()

    assert isinstance(name, str)
    assert len(name) > 0


def test_create_and_get_plan_roundtrip(plan_backend: PlanBackend) -> None:
    """Both backends can create and retrieve a plan with same data."""
    result = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan Title",
        content="# Plan Content\n\nThis is the plan body.",
        labels=("erk-plan",),
        metadata={},
    )

    # Verify CreatePlanResult structure
    assert isinstance(result.plan_id, str)
    assert len(result.plan_id) > 0
    assert isinstance(result.url, str)

    # Retrieve the plan
    plan = plan_backend.get_plan(Path("/repo"), result.plan_id)

    # Verify Plan structure
    assert plan.plan_identifier == result.plan_id
    # Title must CONTAIN the original (some backends may add suffixes like [erk-plan])
    assert "Test Plan Title" in plan.title
    assert plan.body == "# Plan Content\n\nThis is the plan body."
    assert plan.state == PlanState.OPEN  # New plans are open
    assert isinstance(plan.url, str)
    assert isinstance(plan.labels, list)
    assert isinstance(plan.assignees, list)
    assert isinstance(plan.created_at, datetime)
    assert isinstance(plan.updated_at, datetime)
    assert isinstance(plan.metadata, dict)


def test_list_plans_returns_list(plan_backend: PlanBackend) -> None:
    """Both backends return a list from list_plans (empty is valid)."""
    results = plan_backend.list_plans(Path("/repo"), PlanQuery())

    assert isinstance(results, list)


def test_list_plans_filters_by_state(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends filter by PlanState correctly."""
    backend, plan_id = backend_with_plan

    # Query for OPEN plans should find the plan
    open_results = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.OPEN))
    assert any(p.plan_identifier == plan_id for p in open_results)

    # Query for CLOSED plans should not find it
    closed_results = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.CLOSED))
    assert not any(p.plan_identifier == plan_id for p in closed_results)


def test_close_plan_changes_state(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends close a plan by changing state to CLOSED."""
    backend, plan_id = backend_with_plan

    # Verify initially OPEN
    plan_before = backend.get_plan(Path("/repo"), plan_id)
    assert plan_before.state == PlanState.OPEN

    # Close it
    backend.close_plan(Path("/repo"), plan_id)

    # Verify now CLOSED
    plan_after = backend.get_plan(Path("/repo"), plan_id)
    assert plan_after.state == PlanState.CLOSED


def test_add_comment_returns_string_id(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends return comment ID as string."""
    backend, plan_id = backend_with_plan

    comment_id = backend.add_comment(
        repo_root=Path("/repo"),
        plan_id=plan_id,
        body="Progress update: Phase 1 complete",
    )

    assert isinstance(comment_id, str)
    assert len(comment_id) > 0


def _get_nonexistent_id(plan_backend: PlanBackend) -> str:
    """Get a valid-format but nonexistent plan ID for the backend.

    GitHub requires numeric IDs, Linear uses UUID-style IDs.
    """
    if plan_backend.get_provider_name() == "github":
        return "99999999"  # Valid numeric format but doesn't exist
    else:
        return "nonexistent-plan-id-12345"  # UUID-style for Linear


def test_get_plan_not_found_raises_runtime_error(plan_backend: PlanBackend) -> None:
    """Both backends raise RuntimeError when plan not found."""
    nonexistent_id = _get_nonexistent_id(plan_backend)
    with pytest.raises(RuntimeError):
        plan_backend.get_plan(Path("/repo"), nonexistent_id)


def test_add_comment_not_found_raises_runtime_error(plan_backend: PlanBackend) -> None:
    """Both backends raise RuntimeError when plan not found for comment."""
    nonexistent_id = _get_nonexistent_id(plan_backend)
    with pytest.raises(RuntimeError):
        plan_backend.add_comment(
            repo_root=Path("/repo"),
            plan_id=nonexistent_id,
            body="Comment",
        )


def test_close_plan_not_found_raises_runtime_error(plan_backend: PlanBackend) -> None:
    """Both backends raise RuntimeError when plan not found for close."""
    nonexistent_id = _get_nonexistent_id(plan_backend)
    with pytest.raises(RuntimeError):
        plan_backend.close_plan(Path("/repo"), nonexistent_id)


def test_update_metadata_not_found_raises_runtime_error(
    plan_backend: PlanBackend,
) -> None:
    """Both backends raise RuntimeError when plan not found for update."""
    nonexistent_id = _get_nonexistent_id(plan_backend)
    with pytest.raises(RuntimeError):
        plan_backend.update_metadata(
            repo_root=Path("/repo"),
            plan_id=nonexistent_id,
            metadata={"key": "value"},
        )


def test_plan_identifier_is_string(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends return plan_identifier as string (not int)."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)

    assert isinstance(plan.plan_identifier, str)
    # Note: GitHub uses "42", Linear uses "LIN-abc123"
    # Both are valid strings


def test_assignees_is_list(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends return assignees as list (even if empty or single)."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)

    assert isinstance(plan.assignees, list)
    # All items should be strings
    for assignee in plan.assignees:
        assert isinstance(assignee, str)


def test_labels_is_list(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends return labels as list."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)

    assert isinstance(plan.labels, list)
    # All items should be strings
    for label in plan.labels:
        assert isinstance(label, str)


def test_timestamps_are_timezone_aware(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Both backends return timezone-aware datetime objects."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)

    # Both timestamps should be timezone-aware
    assert plan.created_at.tzinfo is not None
    assert plan.updated_at.tzinfo is not None


# =============================================================================
# Multiple plan tests
# =============================================================================


def test_list_plans_with_limit(plan_backend: PlanBackend) -> None:
    """Both backends respect limit parameter."""
    # Create multiple plans
    for i in range(5):
        plan_backend.create_plan(
            repo_root=Path("/repo"),
            title=f"Plan {i}",
            content=f"Content {i}",
            labels=("erk-plan",),
            metadata={},
        )

    # Query with limit
    results = plan_backend.list_plans(Path("/repo"), PlanQuery(limit=2))

    assert len(results) <= 2


def test_create_multiple_plans_have_unique_ids(plan_backend: PlanBackend) -> None:
    """Both backends generate unique plan IDs."""
    results = []
    for i in range(3):
        result = plan_backend.create_plan(
            repo_root=Path("/repo"),
            title=f"Plan {i}",
            content=f"Content {i}",
            labels=(),
            metadata={},
        )
        results.append(result)

    # All IDs should be unique
    ids = [r.plan_id for r in results]
    assert len(ids) == len(set(ids))
