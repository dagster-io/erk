"""Tests for PlanHeaderData frozen dataclass."""

import dataclasses

import pytest

from erk_shared.gateway.github.metadata.core import (
    find_metadata_block,
    render_metadata_block,
)
from erk_shared.gateway.github.metadata.plan_header import create_plan_header_block
from erk_shared.gateway.github.metadata.plan_header_data import PlanHeaderData
from erk_shared.gateway.github.metadata.schemas import PlanHeaderSchema
from erk_shared.gateway.github.metadata.types import BlockKeys


def _minimal_dict() -> dict:
    return {
        "schema_version": "2",
        "created_at": "2025-01-15T10:00:00Z",
        "created_by": "testuser",
    }


def _full_dict() -> dict:
    return {
        "schema_version": "2",
        "created_at": "2025-01-15T10:00:00Z",
        "created_by": "testuser",
        "worktree_name": "wt-fix-auth",
        "branch_name": "plnd/fix-auth-session",
        "plan_comment_id": 123456,
        "ci_summary_comment_id": 789012,
        "last_dispatched_run_id": "run-42",
        "last_dispatched_node_id": "MDExOlBR_42",
        "last_dispatched_at": "2025-01-15T11:00:00Z",
        "last_local_impl_at": "2025-01-15T12:00:00Z",
        "last_local_impl_event": "started",
        "last_local_impl_session": "sess-local-1",
        "last_local_impl_user": "dev1",
        "last_remote_impl_at": "2025-01-15T13:00:00Z",
        "last_remote_impl_run_id": "run-99",
        "last_remote_impl_session_id": "sess-remote-1",
        "source_repo": "owner/impl-repo",
        "objective_issue": 100,
        "node_ids": ["1.1", "1.2"],
        "created_from_session": "sess-create-1",
        "created_from_workflow_run_url": "https://github.com/owner/repo/actions/runs/55",
        "last_learn_session": "sess-learn-1",
        "last_learn_at": "2025-01-16T10:00:00Z",
        "learn_status": "completed_with_plan",
        "learn_run_id": "run-learn-1",
        "last_session_branch": "session/sess-local-1",
        "last_session_id": "sess-local-1",
        "last_session_at": "2025-01-16T11:00:00Z",
        "last_session_source": "local",
        "learn_plan_issue": 200,
        "learn_plan_pr": 201,
        "learned_from_issue": 50,
        "learn_materials_branch": "learn/sess-learn-1",
        "lifecycle_stage": "impl",
    }


def test_from_dict_all_fields() -> None:
    data = _full_dict()
    header = PlanHeaderData.from_dict(data)

    assert header.created_at == "2025-01-15T10:00:00Z"
    assert header.created_by == "testuser"
    assert header.worktree_name == "wt-fix-auth"
    assert header.branch_name == "plnd/fix-auth-session"
    assert header.plan_comment_id == 123456
    assert header.ci_summary_comment_id == 789012
    assert header.last_dispatched_run_id == "run-42"
    assert header.objective_issue == 100
    assert header.node_ids == ("1.1", "1.2")
    assert header.learn_status == "completed_with_plan"
    assert header.lifecycle_stage == "impl"
    assert header.last_session_source == "local"
    assert header.learn_materials_branch == "learn/sess-learn-1"


def test_from_dict_minimal() -> None:
    data = _minimal_dict()
    header = PlanHeaderData.from_dict(data)

    assert header.created_at == "2025-01-15T10:00:00Z"
    assert header.created_by == "testuser"
    assert header.worktree_name is None
    assert header.branch_name is None
    assert header.plan_comment_id is None
    assert header.node_ids is None
    assert header.lifecycle_stage is None


def test_from_dict_node_ids_list_to_tuple() -> None:
    data = _minimal_dict()
    data["node_ids"] = ["a", "b", "c"]
    header = PlanHeaderData.from_dict(data)

    assert header.node_ids == ("a", "b", "c")
    assert isinstance(header.node_ids, tuple)


def test_to_dict_round_trip() -> None:
    data = _full_dict()
    header = PlanHeaderData.from_dict(data)
    result = header.to_dict()

    schema = PlanHeaderSchema()
    schema.validate(result)

    assert result["schema_version"] == "2"
    assert result["created_at"] == data["created_at"]
    assert result["created_by"] == data["created_by"]
    assert result["worktree_name"] == data["worktree_name"]
    assert result["objective_issue"] == data["objective_issue"]


def test_to_dict_injects_schema_version() -> None:
    header = PlanHeaderData(created_at="2025-01-15T10:00:00Z", created_by="testuser")
    result = header.to_dict()

    assert "schema_version" in result
    assert result["schema_version"] == "2"


def test_to_dict_converts_tuple_to_list() -> None:
    header = PlanHeaderData(
        created_at="2025-01-15T10:00:00Z",
        created_by="testuser",
        node_ids=("x", "y"),
    )
    result = header.to_dict()

    assert result["node_ids"] == ["x", "y"]
    assert isinstance(result["node_ids"], list)


def test_to_dict_omits_none_fields() -> None:
    header = PlanHeaderData(created_at="2025-01-15T10:00:00Z", created_by="testuser")
    result = header.to_dict()

    assert "worktree_name" not in result
    assert "plan_comment_id" not in result
    assert "node_ids" not in result
    assert "lifecycle_stage" not in result


def test_to_metadata_block() -> None:
    header = PlanHeaderData(
        created_at="2025-01-15T10:00:00Z",
        created_by="testuser",
        worktree_name="wt-1",
    )
    block = header.to_metadata_block()

    assert block.key == BlockKeys.PLAN_HEADER
    assert block.data["created_at"] == "2025-01-15T10:00:00Z"
    assert block.data["worktree_name"] == "wt-1"
    assert block.data["schema_version"] == "2"


def test_from_issue_body_parses() -> None:
    block = create_plan_header_block(
        created_at="2025-01-15T10:00:00Z",
        created_by="testuser",
        worktree_name="wt-test",
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        node_ids=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    body = render_metadata_block(block)

    header = PlanHeaderData.from_issue_body(body)
    assert header is not None
    assert header.created_at == "2025-01-15T10:00:00Z"
    assert header.created_by == "testuser"
    assert header.worktree_name == "wt-test"


def test_from_issue_body_returns_none() -> None:
    result = PlanHeaderData.from_issue_body("no metadata here")
    assert result is None


def test_yaml_round_trip() -> None:
    """Create via PlanHeaderData -> render -> parse -> verify fields match."""
    header = PlanHeaderData(
        created_at="2025-01-15T10:00:00Z",
        created_by="testuser",
        worktree_name="wt-round-trip",
        branch_name="plnd/round-trip",
        objective_issue=42,
        node_ids=("n1", "n2"),
        lifecycle_stage="planned",
    )
    rendered = header.to_rendered_block()

    parsed_block = find_metadata_block(rendered, BlockKeys.PLAN_HEADER)
    assert parsed_block is not None

    restored = PlanHeaderData.from_dict(parsed_block.data)
    assert restored.created_at == header.created_at
    assert restored.created_by == header.created_by
    assert restored.worktree_name == header.worktree_name
    assert restored.branch_name == header.branch_name
    assert restored.objective_issue == header.objective_issue
    assert restored.node_ids == header.node_ids
    assert restored.lifecycle_stage == header.lifecycle_stage
    assert restored.plan_comment_id is None


def test_frozen() -> None:
    header = PlanHeaderData(created_at="2025-01-15T10:00:00Z", created_by="testuser")
    with pytest.raises(dataclasses.FrozenInstanceError):
        header.created_at = "other"  # type: ignore[misc]
