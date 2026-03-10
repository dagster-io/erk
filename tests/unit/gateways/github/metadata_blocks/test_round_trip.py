"""Parameterized round-trip tests for all metadata block types.

Proves that every registered block type survives render -> parse -> verify
correctly. Uses the block type registry to drive parameterization, ensuring
tests stay in sync with the registry automatically.

Block categories:
- YAML blocks (13): Render as YAML in <details> -> parse back to MetadataBlock
- CONTENT blocks (3): Render with content-specific renderers -> parse back to RawMetadataBlock
"""

import pytest

from erk_shared.gateway.github.metadata.core import (
    create_implementation_status_block,
    create_metadata_block,
    create_objective_header_block,
    create_plan_block,
    create_plan_body_block,
    create_submission_queued_block,
    create_workflow_started_block,
    create_worktree_creation_block,
    parse_metadata_blocks,
    render_metadata_block,
    render_objective_body_block,
    render_plan_body_block,
)
from erk_shared.gateway.github.metadata.plan_header import create_plan_header_block
from erk_shared.gateway.github.metadata.registry import (
    get_all_block_types,
    get_block_type,
    get_content_block_types,
    get_yaml_block_types,
)
from erk_shared.gateway.github.metadata.schemas import PlanRetrySchema
from erk_shared.gateway.github.metadata.session import render_session_prompts_block
from erk_shared.gateway.github.metadata.types import MetadataBlock

# ---------------------------------------------------------------------------
# Sample data for YAML block types
# ---------------------------------------------------------------------------

SAMPLE_DATA: dict[str, dict] = {
    "plan-header": {
        "schema_version": "2",
        "created_at": "2025-01-15T10:00:00Z",
        "created_by": "testuser",
        "plan_comment_id": None,
        "last_dispatched_run_id": None,
        "last_dispatched_node_id": None,
        "last_dispatched_at": None,
        "last_local_impl_at": None,
        "last_local_impl_event": None,
        "last_local_impl_session": None,
        "last_local_impl_user": None,
        "last_remote_impl_at": None,
        "last_remote_impl_run_id": None,
        "last_remote_impl_session_id": None,
    },
    "objective-header": {
        "created_at": "2025-01-15T10:00:00Z",
        "created_by": "testuser",
        "objective_comment_id": None,
    },
    "erk-plan": {
        "pr_number": 42,
        "worktree_name": "test-worktree",
        "timestamp": "2025-01-15T10:00:00Z",
    },
    "erk-worktree-creation": {
        "worktree_name": "test-worktree",
        "branch_name": "plnd/test-branch",
        "timestamp": "2025-01-15T10:00:00Z",
    },
    "erk-implementation-status": {
        "status": "complete",
        "timestamp": "2025-01-15T10:00:00Z",
        "summary": "All phases completed successfully",
    },
    "workflow-started": {
        "status": "started",
        "started_at": "2025-01-15T10:00:00Z",
        "workflow_run_id": "12345678",
        "workflow_run_url": "https://github.com/owner/repo/actions/runs/12345678",
        "pr_number": 42,
    },
    "submission-queued": {
        "status": "queued",
        "queued_at": "2025-01-15T10:00:00Z",
        "submitted_by": "testuser",
        "pr_number": 42,
        "validation_results": {"pr_is_open": True, "has_erk_pr_title": True},
        "expected_workflow": "implement-plan",
        "trigger_mechanism": "label-based-webhook",
    },
    "plan-retry": {
        "retry_timestamp": "2025-01-15T10:00:00Z",
        "triggered_by": "testuser",
        "retry_count": 1,
    },
    "impl-started": {
        "session_id": "abc-123",
        "timestamp": "2025-01-15T10:00:00Z",
        "pr_number": 42,
    },
    "impl-ended": {
        "session_id": "abc-123",
        "timestamp": "2025-01-15T11:00:00Z",
        "pr_number": 42,
        "outcome": "success",
    },
    "learn-invoked": {
        "session_id": "abc-123",
        "timestamp": "2025-01-15T12:00:00Z",
        "pr_number": 42,
    },
    "tripwire-candidates": {
        "source_plan": 42,
        "candidates": [
            {"category": "testing", "description": "Always mock subprocess calls"},
        ],
    },
    "objective-roadmap": {
        "nodes": [
            {"id": "1.1", "title": "Setup", "status": "complete"},
            {"id": "1.2", "title": "Implementation", "status": "pending"},
        ],
    },
}

# Sample content for CONTENT block types
SAMPLE_CONTENT: dict[str, str] = {
    "plan-body": "# Implementation Plan\n\nThis is the plan content.\n\n## Phase 1\n\nDo things.",
    "objective-body": (
        "# Objective\n\nHarden the metadata block system.\n\n## Goals\n\n- Reliability"
    ),
    "planning-session-prompts": "Add round-trip tests for all block types",
}

# ---------------------------------------------------------------------------
# Content block renderers
# ---------------------------------------------------------------------------


def _render_content_block(key: str, content: str) -> str:
    """Render a content block using the appropriate renderer."""
    if key == "plan-body":
        block = create_plan_body_block(content)
        return render_plan_body_block(block)
    if key == "objective-body":
        return render_objective_body_block(content)
    if key == "planning-session-prompts":
        return render_session_prompts_block(
            [content],
            max_prompt_display_length=500,
        )
    raise ValueError(f"No content renderer for key: {key}")


# ---------------------------------------------------------------------------
# Factory blocks for schema-backed types
# ---------------------------------------------------------------------------

FACTORY_BLOCKS: dict[str, MetadataBlock] = {
    "erk-implementation-status": create_implementation_status_block(
        status="complete",
        timestamp="2025-01-15T10:00:00Z",
        summary="All phases completed successfully",
    ),
    "erk-worktree-creation": create_worktree_creation_block(
        worktree_name="test-worktree",
        branch_name="plnd/test-branch",
        timestamp="2025-01-15T10:00:00Z",
    ),
    "erk-plan": create_plan_block(
        plan_number=42,
        worktree_name="test-worktree",
        timestamp="2025-01-15T10:00:00Z",
    ),
    "submission-queued": create_submission_queued_block(
        queued_at="2025-01-15T10:00:00Z",
        submitted_by="testuser",
        plan_number=42,
        validation_results={"pr_is_open": True, "has_erk_pr_title": True},
        expected_workflow="implement-plan",
    ),
    "workflow-started": create_workflow_started_block(
        started_at="2025-01-15T10:00:00Z",
        workflow_run_id="12345678",
        workflow_run_url="https://github.com/owner/repo/actions/runs/12345678",
        plan_number=42,
    ),
    "plan-header": create_plan_header_block(
        created_at="2025-01-15T10:00:00Z",
        created_by="testuser",
        worktree_name=None,
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
        created_from_session=None,
        created_from_workflow_run_url=None,
        created_from_workflow_run_id=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    ),
    "objective-header": create_objective_header_block(
        created_at="2025-01-15T10:00:00Z",
        created_by="testuser",
        objective_comment_id=None,
        slug=None,
    ),
    "plan-retry": create_metadata_block(
        key="plan-retry",
        data={
            "retry_timestamp": "2025-01-15T10:00:00Z",
            "triggered_by": "testuser",
            "retry_count": 1,
        },
        schema=PlanRetrySchema(),
    ),
}

SCHEMA_BACKED_KEYS = list(FACTORY_BLOCKS.keys())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestYamlBlockRoundTrip:
    """Render -> parse -> verify for every YAML block type."""

    @pytest.mark.parametrize("key", [info.key for info in get_yaml_block_types()], ids=str)
    def test_yaml_block_round_trip(self, key: str) -> None:
        data = SAMPLE_DATA[key]
        block = MetadataBlock(key=key, data=data)
        rendered = render_metadata_block(block)
        result = parse_metadata_blocks(rendered)

        assert not result.has_errors, f"Parse errors for {key}: {result.errors}"
        assert len(result.blocks) == 1
        assert result.blocks[0].key == key
        assert result.blocks[0].data == data
        assert len(result.content_blocks) == 0


class TestContentBlockRoundTrip:
    """Render -> parse -> verify for every CONTENT block type."""

    @pytest.mark.parametrize("key", [info.key for info in get_content_block_types()], ids=str)
    def test_content_block_round_trip(self, key: str) -> None:
        rendered = _render_content_block(key, SAMPLE_CONTENT[key])
        result = parse_metadata_blocks(rendered)

        assert len(result.blocks) == 0, f"Content block {key} should not appear in YAML blocks"
        assert len(result.errors) == 0, f"Parse errors for {key}: {result.errors}"
        assert len(result.content_blocks) == 1
        assert result.content_blocks[0].key == key


class TestSchemaFactoryRoundTrip:
    """Factory -> render -> parse -> schema.validate() for schema-backed types."""

    @pytest.mark.parametrize("key", SCHEMA_BACKED_KEYS, ids=str)
    def test_schema_factory_round_trip(self, key: str) -> None:
        block = FACTORY_BLOCKS[key]
        rendered = render_metadata_block(block)
        result = parse_metadata_blocks(rendered)

        assert not result.has_errors, f"Parse errors for {key}: {result.errors}"
        assert len(result.blocks) == 1

        info = get_block_type(key)
        assert info is not None, f"Block type {key} not found in registry"
        assert info.schema is not None, f"Block type {key} should have a schema"
        # Schema validation should not raise
        info.schema.validate(result.blocks[0].data)


class TestRegistryCompleteness:
    """Every registered block type has sample data for round-trip testing."""

    def test_all_registered_types_have_sample_data(self) -> None:
        all_keys = set(get_all_block_types().keys())
        yaml_keys = set(SAMPLE_DATA.keys())
        content_keys = set(SAMPLE_CONTENT.keys())
        covered_keys = yaml_keys | content_keys

        missing = all_keys - covered_keys
        assert not missing, f"Block types missing sample data: {missing}"
        assert covered_keys == all_keys

    def test_yaml_sample_data_matches_yaml_registry(self) -> None:
        yaml_registry_keys = {info.key for info in get_yaml_block_types()}
        assert set(SAMPLE_DATA.keys()) == yaml_registry_keys

    def test_content_sample_data_matches_content_registry(self) -> None:
        content_registry_keys = {info.key for info in get_content_block_types()}
        assert set(SAMPLE_CONTENT.keys()) == content_registry_keys

    def test_factory_blocks_cover_all_schema_backed_types(self) -> None:
        schema_backed = {
            info.key for info in get_all_block_types().values() if info.schema is not None
        }
        assert set(FACTORY_BLOCKS.keys()) == schema_backed

    def test_registry_has_expected_count(self) -> None:
        all_types = get_all_block_types()
        yaml_types = get_yaml_block_types()
        content_types = get_content_block_types()

        assert len(all_types) == 16
        assert len(yaml_types) == 13
        assert len(content_types) == 3
        assert len(yaml_types) + len(content_types) == len(all_types)
