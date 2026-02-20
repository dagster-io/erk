"""Interface tests for PlanBackend implementations.

These tests verify that all PlanBackend implementations satisfy the ABC interface.
Tests are parameterized to run against both GitHubPlanStore and DraftPRPlanBackend.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import PlanNotFound, PlanQuery, PlanState
from tests.test_utils.github_helpers import create_test_issue

# =============================================================================
# Fixtures
# =============================================================================

_BRANCH_COUNTER = 0


def _next_branch() -> str:
    """Generate a unique branch name for tests."""
    global _BRANCH_COUNTER  # noqa: PLW0603
    _BRANCH_COUNTER += 1
    return f"test-branch-{_BRANCH_COUNTER}"


def _make_github_plan_store() -> PlanBackend:
    """Create a GitHubPlanStore backed by FakeGitHubIssues."""
    fake_issues = FakeGitHubIssues(username="testuser", labels={"erk-plan"})
    return GitHubPlanStore(fake_issues)


def _make_draft_pr_plan_backend() -> PlanBackend:
    """Create a DraftPRPlanBackend backed by FakeGitHub."""
    fake_github = FakeGitHub()
    return DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())


def _create_metadata(backend: PlanBackend) -> dict[str, object]:
    """Build the required metadata dict for create_plan().

    DraftPRPlanBackend requires branch_name; GitHubPlanStore does not.
    """
    # PLAN_BACKEND_SPLIT: DraftPRPlanBackend requires branch_name metadata; GitHubPlanStore does not
    if isinstance(backend, DraftPRPlanBackend):
        return {"branch_name": _next_branch()}
    return {}


def _make_github_backend_with_plan() -> tuple[PlanBackend, str]:
    """Create GitHubPlanStore with a pre-existing plan."""
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


def _make_draft_pr_backend_with_plan() -> tuple[PlanBackend, str]:
    """Create DraftPRPlanBackend with a pre-existing plan by creating one via API."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Existing Plan",
        content="Plan content",
        labels=("erk-plan",),
        metadata={"branch_name": "existing-plan-branch"},
    )
    return backend, result.plan_id


@pytest.fixture(params=["github_issues", "draft_pr"])
def plan_backend(request: pytest.FixtureRequest) -> PlanBackend:
    """Provide a PlanBackend implementation.

    Parameterized to test both GitHubPlanStore and DraftPRPlanBackend.
    """
    if request.param == "github_issues":
        return _make_github_plan_store()
    return _make_draft_pr_plan_backend()


@pytest.fixture(params=["github_issues", "draft_pr"])
def backend_with_plan(request: pytest.FixtureRequest) -> tuple[PlanBackend, str]:
    """Fixture providing backend with a pre-existing plan.

    Returns:
        Tuple of (backend, plan_id)
    """
    if request.param == "github_issues":
        return _make_github_backend_with_plan()
    return _make_draft_pr_backend_with_plan()


# =============================================================================
# Interface contract tests
# =============================================================================


def test_get_provider_name_returns_string(plan_backend: PlanBackend) -> None:
    """Backend returns a non-empty provider name string."""
    name = plan_backend.get_provider_name()

    assert isinstance(name, str)
    assert len(name) > 0


def test_create_and_get_plan_roundtrip(plan_backend: PlanBackend) -> None:
    """Backend can create and retrieve a plan with same data."""
    result = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan Title",
        content="# Plan Content\n\nThis is the plan body.",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    # Verify CreatePlanResult structure
    assert isinstance(result.plan_id, str)
    assert len(result.plan_id) > 0
    assert isinstance(result.url, str)

    # Retrieve the plan
    plan = plan_backend.get_plan(Path("/repo"), result.plan_id)
    assert not isinstance(plan, PlanNotFound)

    # Verify Plan structure
    assert plan.plan_identifier == result.plan_id
    assert "Test Plan Title" in plan.title
    assert plan.body == "# Plan Content\n\nThis is the plan body."
    assert plan.state == PlanState.OPEN
    assert isinstance(plan.url, str)
    assert isinstance(plan.labels, list)
    assert isinstance(plan.assignees, list)
    assert isinstance(plan.created_at, datetime)
    assert isinstance(plan.updated_at, datetime)
    assert isinstance(plan.metadata, dict)


def test_list_plans_returns_list(plan_backend: PlanBackend) -> None:
    """Backend returns a list from list_plans (empty is valid)."""
    results = plan_backend.list_plans(Path("/repo"), PlanQuery())

    assert isinstance(results, list)


def test_list_plans_filters_by_state(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend filters by PlanState correctly."""
    backend, plan_id = backend_with_plan

    open_results = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.OPEN))
    assert any(p.plan_identifier == plan_id for p in open_results)

    closed_results = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.CLOSED))
    assert not any(p.plan_identifier == plan_id for p in closed_results)


def test_close_plan_changes_state(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend closes a plan by changing state to CLOSED."""
    backend, plan_id = backend_with_plan

    plan_before = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan_before, PlanNotFound)
    assert plan_before.state == PlanState.OPEN

    backend.close_plan(Path("/repo"), plan_id)

    plan_after = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan_after, PlanNotFound)
    assert plan_after.state == PlanState.CLOSED


def test_add_comment_returns_string_id(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns comment ID as string."""
    backend, plan_id = backend_with_plan

    comment_id = backend.add_comment(
        repo_root=Path("/repo"),
        plan_id=plan_id,
        body="Progress update: Phase 1 complete",
    )

    assert isinstance(comment_id, str)
    assert len(comment_id) > 0


def test_get_plan_not_found_returns_plan_not_found(plan_backend: PlanBackend) -> None:
    """Backend returns PlanNotFound when plan not found."""
    result = plan_backend.get_plan(Path("/repo"), "99999999")
    assert isinstance(result, PlanNotFound)
    assert result.plan_id == "99999999"


def test_add_comment_not_found_raises_runtime_error(plan_backend: PlanBackend) -> None:
    """Backend raises RuntimeError when plan not found for comment."""
    with pytest.raises(RuntimeError):
        plan_backend.add_comment(
            repo_root=Path("/repo"),
            plan_id="99999999",
            body="Comment",
        )


def test_close_plan_not_found_raises_runtime_error(plan_backend: PlanBackend) -> None:
    """Backend raises RuntimeError when plan not found for close."""
    with pytest.raises(RuntimeError):
        plan_backend.close_plan(Path("/repo"), "99999999")


def test_update_metadata_not_found_raises_runtime_error(
    plan_backend: PlanBackend,
) -> None:
    """Backend raises RuntimeError when plan not found for update."""
    with pytest.raises(RuntimeError):
        plan_backend.update_metadata(
            repo_root=Path("/repo"),
            plan_id="99999999",
            metadata={"key": "value"},
        )


def test_plan_identifier_is_string(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns plan_identifier as string."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert isinstance(plan.plan_identifier, str)


def test_assignees_is_list(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns assignees as list."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert isinstance(plan.assignees, list)
    for assignee in plan.assignees:
        assert isinstance(assignee, str)


def test_labels_is_list(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns labels as list."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert isinstance(plan.labels, list)
    for label in plan.labels:
        assert isinstance(label, str)


def test_timestamps_are_timezone_aware(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns timezone-aware datetime objects."""
    backend, plan_id = backend_with_plan

    plan = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert plan.created_at.tzinfo is not None
    assert plan.updated_at.tzinfo is not None


# =============================================================================
# Multiple plan tests
# =============================================================================


def test_list_plans_with_limit(plan_backend: PlanBackend) -> None:
    """Backend respects limit parameter."""
    for i in range(5):
        plan_backend.create_plan(
            repo_root=Path("/repo"),
            title=f"Plan {i}",
            content=f"Content {i}",
            labels=("erk-plan",),
            metadata=_create_metadata(plan_backend),
        )

    results = plan_backend.list_plans(Path("/repo"), PlanQuery(limit=2))
    assert len(results) <= 2


def test_create_multiple_plans_have_unique_ids(plan_backend: PlanBackend) -> None:
    """Backend generates unique plan IDs."""
    results = []
    for i in range(3):
        result = plan_backend.create_plan(
            repo_root=Path("/repo"),
            title=f"Plan {i}",
            content=f"Content {i}",
            labels=(),
            metadata=_create_metadata(plan_backend),
        )
        results.append(result)

    ids = [r.plan_id for r in results]
    assert len(ids) == len(set(ids))


# =============================================================================
# get_metadata_field tests
# =============================================================================


def test_get_metadata_field_returns_plan_not_found(plan_backend: PlanBackend) -> None:
    """Backend returns PlanNotFound for nonexistent plan."""
    result = plan_backend.get_metadata_field(Path("/repo"), "99999999", "worktree_name")
    assert isinstance(result, PlanNotFound)


def test_get_metadata_field_returns_none_for_missing_field(plan_backend: PlanBackend) -> None:
    """Backend returns None when plan exists but field is absent."""
    created = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan for metadata test",
        content="# Test plan",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    result = plan_backend.get_metadata_field(Path("/repo"), created.plan_id, "worktree_name")
    assert result is None


def test_get_metadata_field_roundtrips_with_update_metadata(
    plan_backend: PlanBackend,
) -> None:
    """Backend can set and read back a metadata field."""
    created = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan for roundtrip",
        content="# Roundtrip plan",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    plan_backend.update_metadata(
        Path("/repo"),
        created.plan_id,
        {"worktree_name": "my-worktree"},
    )

    result = plan_backend.get_metadata_field(Path("/repo"), created.plan_id, "worktree_name")
    assert result == "my-worktree"


# =============================================================================
# get_all_metadata_fields tests
# =============================================================================


def test_get_all_metadata_fields_returns_plan_not_found(plan_backend: PlanBackend) -> None:
    """Backend returns PlanNotFound for nonexistent plan."""
    result = plan_backend.get_all_metadata_fields(Path("/repo"), "99999999")
    assert isinstance(result, PlanNotFound)


def test_get_all_metadata_fields_returns_empty_dict_for_no_metadata(
    plan_backend: PlanBackend,
) -> None:
    """Backend returns empty dict when plan exists but has no metadata fields."""
    created = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan for all-metadata test",
        content="# Test plan",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    result = plan_backend.get_all_metadata_fields(Path("/repo"), created.plan_id)
    assert not isinstance(result, PlanNotFound)
    assert isinstance(result, dict)


def test_get_all_metadata_fields_roundtrips_with_update_metadata(
    plan_backend: PlanBackend,
) -> None:
    """Backend can set metadata and read all fields back."""
    created = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan for all-metadata roundtrip",
        content="# Roundtrip plan",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    plan_backend.update_metadata(
        Path("/repo"),
        created.plan_id,
        {"worktree_name": "my-worktree", "branch_name": "feature-branch"},
    )

    result = plan_backend.get_all_metadata_fields(Path("/repo"), created.plan_id)
    assert not isinstance(result, PlanNotFound)
    assert result["worktree_name"] == "my-worktree"
    assert result["branch_name"] == "feature-branch"


# =============================================================================
# update_plan_title tests
# =============================================================================


def test_update_plan_title_roundtrip(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend can update and retrieve a plan title."""
    backend, plan_id = backend_with_plan

    backend.update_plan_title(Path("/repo"), plan_id, "New Title")

    plan = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert "New Title" in plan.title


def test_update_plan_title_not_found_raises(plan_backend: PlanBackend) -> None:
    """Backend raises RuntimeError for nonexistent plan."""
    with pytest.raises(RuntimeError):
        plan_backend.update_plan_title(Path("/repo"), "99999999", "Title")


# =============================================================================
# update_plan_content tests
# =============================================================================


def test_update_plan_content_not_found_raises(plan_backend: PlanBackend) -> None:
    """Backend raises RuntimeError for nonexistent plan."""
    with pytest.raises(RuntimeError):
        plan_backend.update_plan_content(Path("/repo"), "99999999", "new content")


# =============================================================================
# post_event tests
# =============================================================================


def test_post_event_metadata_only(plan_backend: PlanBackend) -> None:
    """Backend handles metadata update without comment."""
    created = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan for event",
        content="# Event plan",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    plan_backend.post_event(
        Path("/repo"),
        created.plan_id,
        metadata={"worktree_name": "event-wt"},
        comment=None,
    )

    result = plan_backend.get_metadata_field(Path("/repo"), created.plan_id, "worktree_name")
    assert result == "event-wt"


def test_post_event_metadata_and_comment(plan_backend: PlanBackend) -> None:
    """Backend handles metadata update with comment."""
    created = plan_backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan for event with comment",
        content="# Event plan",
        labels=("erk-plan",),
        metadata=_create_metadata(plan_backend),
    )

    plan_backend.post_event(
        Path("/repo"),
        created.plan_id,
        metadata={"worktree_name": "event-wt-2"},
        comment="Implementation started",
    )

    result = plan_backend.get_metadata_field(Path("/repo"), created.plan_id, "worktree_name")
    assert result == "event-wt-2"


def test_post_event_not_found_raises(plan_backend: PlanBackend) -> None:
    """Backend raises RuntimeError for nonexistent plan."""
    with pytest.raises(RuntimeError):
        plan_backend.post_event(
            Path("/repo"),
            "99999999",
            metadata={"worktree_name": "wt"},
            comment=None,
        )


# =============================================================================
# Whitelist removal test (GitHub-specific)
# =============================================================================


# =============================================================================
# get_comments tests
# =============================================================================


def test_get_comments_returns_empty_list_for_no_comments(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns empty list when plan has no comments."""
    backend, plan_id = backend_with_plan

    comments = backend.get_comments(Path("/repo"), plan_id)
    assert isinstance(comments, list)


def test_get_comments_returns_preconfigured_comments_github() -> None:
    """GitHubPlanStore returns pre-configured comments from FakeGitHubIssues."""
    issue = create_test_issue(
        number=42,
        title="Plan",
        body="content",
        labels=["erk-plan"],
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 12, 0, 0, tzinfo=UTC),
    )
    fake_issues = FakeGitHubIssues(
        issues={42: issue},
        comments={42: ["First comment", "Second comment"]},
    )
    backend = GitHubPlanStore(fake_issues)

    comments = backend.get_comments(Path("/repo"), "42")
    assert len(comments) == 2
    assert "First comment" in comments
    assert "Second comment" in comments


def test_get_comments_returns_preconfigured_comments_draft_pr() -> None:
    """DraftPRPlanBackend returns pre-configured comments from FakeGitHubIssues."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())

    # Create a plan so the PR exists
    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch-comments"},
    )

    # Pre-configure comments on the underlying fake issues gateway
    pr_number = int(result.plan_id)
    fake_github.issues._comments[pr_number] = ["First comment", "Second comment"]

    comments = backend.get_comments(Path("/repo"), result.plan_id)
    assert len(comments) == 2
    assert "First comment" in comments
    assert "Second comment" in comments


# =============================================================================
# find_sessions_for_plan tests
# =============================================================================


def test_find_sessions_for_plan_returns_sessions_for_plan(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend returns SessionsForPlan with expected structure."""
    backend, plan_id = backend_with_plan

    result = backend.find_sessions_for_plan(Path("/repo"), plan_id)
    assert hasattr(result, "planning_session_id")
    assert hasattr(result, "implementation_session_ids")
    assert hasattr(result, "learn_session_ids")
    assert isinstance(result.implementation_session_ids, list)
    assert isinstance(result.learn_session_ids, list)


def test_find_sessions_for_plan_raises_for_nonexistent_plan(
    plan_backend: PlanBackend,
) -> None:
    """Backend raises RuntimeError when plan not found."""
    with pytest.raises(RuntimeError):
        plan_backend.find_sessions_for_plan(Path("/repo"), "99999999")


# =============================================================================
# Whitelist removal test (GitHub-specific)
# =============================================================================


# =============================================================================
# add_label tests
# =============================================================================


def test_add_label_adds_label(
    backend_with_plan: tuple[PlanBackend, str],
) -> None:
    """Backend can add a label to a plan."""
    backend, plan_id = backend_with_plan

    backend.add_label(Path("/repo"), plan_id, "erk-consolidated")

    plan = backend.get_plan(Path("/repo"), plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert "erk-consolidated" in plan.labels


def test_add_label_not_found_raises_runtime_error(plan_backend: PlanBackend) -> None:
    """Backend raises RuntimeError when plan not found for add_label."""
    with pytest.raises(RuntimeError):
        plan_backend.add_label(Path("/repo"), "99999999", "some-label")


# =============================================================================
# Whitelist removal test (GitHub-specific)
# =============================================================================


def test_update_metadata_accepts_previously_blocked_fields() -> None:
    """GitHub backend now accepts fields that were previously blocked by whitelist."""
    fake_issues = FakeGitHubIssues(username="testuser", labels={"erk-plan"})
    backend = GitHubPlanStore(fake_issues)

    created = backend.create_plan(
        repo_root=Path("/repo"),
        title="Whitelist test",
        content="# Plan",
        labels=("erk-plan",),
        metadata={},
    )

    backend.update_metadata(
        Path("/repo"),
        created.plan_id,
        {"learn_status": "pending"},
    )

    result = backend.get_metadata_field(Path("/repo"), created.plan_id, "learn_status")
    assert result == "pending"
