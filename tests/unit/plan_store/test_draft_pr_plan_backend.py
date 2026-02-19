"""DraftPRPlanBackend-specific tests.

Tests for behaviors unique to the draft PR backend that aren't covered
by the parameterized interface tests in test_plan_backend_interface.py.
"""

from pathlib import Path

import pytest

from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.plan_store.draft_pr import (
    DraftPRPlanBackend,
    _build_pr_body,
    _extract_plan_content_from_body,
)
from erk_shared.plan_store.types import PlanNotFound, PlanQuery, PlanState

# =============================================================================
# Provider name
# =============================================================================


def test_provider_name() -> None:
    """DraftPRPlanBackend identifies itself correctly."""
    backend = DraftPRPlanBackend(FakeGitHub())
    assert backend.get_provider_name() == "github-draft-pr"


# =============================================================================
# create_plan specifics
# =============================================================================


def test_create_plan_requires_branch_name() -> None:
    """create_plan raises RuntimeError when branch_name is missing from metadata."""
    backend = DraftPRPlanBackend(FakeGitHub())

    with pytest.raises(RuntimeError, match="branch_name is required"):
        backend.create_plan(
            repo_root=Path("/repo"),
            title="Test Plan",
            content="# Plan",
            labels=("erk-plan",),
            metadata={},
        )


def test_create_plan_creates_draft_pr() -> None:
    """create_plan creates a draft PR, not a regular PR."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch"},
    )

    # Verify it was created as draft
    pr = fake_github.get_pr(Path("/repo"), int(result.plan_id))
    assert not isinstance(pr, PRNotFound)
    assert pr.is_draft is True


def test_create_plan_uses_trunk_branch_as_pr_base() -> None:
    """create_plan uses trunk_branch from metadata as the PR base branch."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch", "trunk_branch": "main"},
    )

    assert fake_github.created_prs[0][3] == "main"


def test_create_plan_falls_back_to_master_when_trunk_branch_missing() -> None:
    """create_plan falls back to 'master' as PR base when trunk_branch is absent."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch"},
    )

    assert fake_github.created_prs[0][3] == "master"


def test_create_plan_falls_back_to_master_when_trunk_branch_not_string() -> None:
    """create_plan falls back to 'master' when trunk_branch is a non-string value."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch", "trunk_branch": 42},
    )

    assert fake_github.created_prs[0][3] == "master"


def test_create_plan_adds_erk_plan_label() -> None:
    """create_plan adds the erk-plan label to the PR."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch"},
    )

    # Check label was added
    assert fake_github.has_pr_label(Path("/repo"), int(result.plan_id), "erk-plan")


def test_create_plan_adds_extra_labels() -> None:
    """create_plan adds extra labels beyond erk-plan."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Plan",
        labels=("erk-plan", "erk-learn"),
        metadata={"branch_name": "test-branch"},
    )

    pr_number = int(result.plan_id)
    assert fake_github.has_pr_label(Path("/repo"), pr_number, "erk-plan")
    assert fake_github.has_pr_label(Path("/repo"), pr_number, "erk-learn")


def test_create_plan_embeds_plan_content_in_pr_body() -> None:
    """create_plan puts plan content in the PR body after metadata."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="# Detailed Plan\n\nStep 1: Do things.",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch"},
    )

    pr = fake_github.get_pr(Path("/repo"), int(result.plan_id))
    assert not isinstance(pr, PRNotFound)
    assert "# Detailed Plan" in pr.body
    assert "Step 1: Do things." in pr.body


# =============================================================================
# resolve_plan_id_for_branch
# =============================================================================


def test_resolve_plan_id_for_branch_finds_created_pr() -> None:
    """resolve_plan_id_for_branch finds a PR created via create_plan."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan",
        content="Content",
        labels=("erk-plan",),
        metadata={"branch_name": "my-plan-branch"},
    )

    plan_id = backend.resolve_plan_id_for_branch(Path("/repo"), "my-plan-branch")
    assert plan_id == result.plan_id


def test_resolve_plan_id_for_branch_returns_none_for_unknown() -> None:
    """resolve_plan_id_for_branch returns None for non-existent branch."""
    backend = DraftPRPlanBackend(FakeGitHub())
    assert backend.resolve_plan_id_for_branch(Path("/repo"), "nonexistent") is None


# =============================================================================
# get_plan_for_branch
# =============================================================================


def test_get_plan_for_branch_roundtrip() -> None:
    """get_plan_for_branch returns plan created via create_plan."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    backend.create_plan(
        repo_root=Path("/repo"),
        title="Branch Plan",
        content="Content for branch",
        labels=("erk-plan",),
        metadata={"branch_name": "my-branch"},
    )

    plan = backend.get_plan_for_branch(Path("/repo"), "my-branch")
    assert not isinstance(plan, PlanNotFound)
    assert plan.body == "Content for branch"


def test_get_plan_for_branch_returns_plan_not_found() -> None:
    """get_plan_for_branch returns PlanNotFound for non-existent branch."""
    backend = DraftPRPlanBackend(FakeGitHub())
    result = backend.get_plan_for_branch(Path("/repo"), "nonexistent")
    assert isinstance(result, PlanNotFound)


# =============================================================================
# update_plan_content
# =============================================================================


def test_update_plan_content_roundtrip() -> None:
    """update_plan_content updates the plan body returned by get_plan."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan",
        content="Original content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch"},
    )

    backend.update_plan_content(Path("/repo"), result.plan_id, "Updated content")

    plan = backend.get_plan(Path("/repo"), result.plan_id)
    assert not isinstance(plan, PlanNotFound)
    assert plan.body == "Updated content"


# =============================================================================
# list_plans filtering
# =============================================================================


def test_list_plans_includes_only_draft_prs_with_erk_plan_label() -> None:
    """list_plans only returns draft PRs that have the erk-plan label."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github)

    # Create a plan (draft with erk-plan label)
    backend.create_plan(
        repo_root=Path("/repo"),
        title="Real Plan",
        content="Plan content",
        labels=("erk-plan",),
        metadata={"branch_name": "plan-branch"},
    )

    plans = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.OPEN))
    assert len(plans) == 1
    assert plans[0].title == "Real Plan"


# =============================================================================
# Body parsing helpers
# =============================================================================


def test_build_pr_body_combines_metadata_and_content() -> None:
    """_build_pr_body creates a body with metadata block and plan content."""
    result = _build_pr_body("metadata block", "plan content")
    assert "metadata block" in result
    assert "plan content" in result
    assert "\n\n---\n\n" in result


def test_extract_plan_content_from_body_extracts_after_separator() -> None:
    """_extract_plan_content_from_body extracts content after the separator."""
    body = "metadata block\n\n---\n\nplan content here"
    assert _extract_plan_content_from_body(body) == "plan content here"


def test_extract_plan_content_from_body_returns_full_body_if_no_separator() -> None:
    """_extract_plan_content_from_body returns full body if no separator found."""
    body = "just plain text"
    assert _extract_plan_content_from_body(body) == "just plain text"
