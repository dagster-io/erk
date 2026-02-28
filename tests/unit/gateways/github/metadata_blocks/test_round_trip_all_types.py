"""Parameterized round-trip tests for all registered block types."""

from typing import Any

import pytest

from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    parse_metadata_blocks,
    render_metadata_block,
    render_objective_body_block,
    render_plan_body_block,
)
from erk_shared.gateway.github.metadata.registry import (
    BlockCategory,
    get_all_block_types,
    get_block_type,
    get_content_block_types,
    get_yaml_block_types,
)
from erk_shared.gateway.github.metadata.session import render_session_prompts_block
from erk_shared.gateway.github.metadata.types import MetadataBlock

# --- Fixtures: minimal valid sample data for each YAML block ---

YAML_BLOCK_SAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "plan-header",
        {
            "schema_version": "2",
            "created_at": "2025-01-01T00:00:00Z",
            "created_by": "test-user",
        },
    ),
    (
        "erk-plan",
        {
            "plan_number": 1,
            "worktree_name": "test-wt",
            "timestamp": "2025-01-01T00:00:00Z",
        },
    ),
    (
        "erk-implementation-status",
        {
            "status": "complete",
            "timestamp": "2025-01-01T00:00:00Z",
        },
    ),
    (
        "erk-worktree-creation",
        {
            "worktree_name": "test-wt",
            "branch_name": "feature/test",
            "timestamp": "2025-01-01T00:00:00Z",
        },
    ),
    (
        "submission-queued",
        {
            "status": "queued",
            "queued_at": "2025-01-01T00:00:00Z",
            "submitted_by": "test-user",
            "plan_number": 42,
            "validation_results": {"issue_is_open": True},
            "expected_workflow": "implement-plan",
            "trigger_mechanism": "label-based-webhook",
        },
    ),
    (
        "workflow-started",
        {
            "status": "started",
            "started_at": "2025-01-01T00:00:00Z",
            "workflow_run_id": "12345",
            "workflow_run_url": "https://github.com/owner/repo/actions/runs/12345",
            "plan_number": 42,
        },
    ),
    (
        "plan-retry",
        {
            "retry_timestamp": "2025-01-01T00:00:00Z",
            "triggered_by": "test-user",
            "retry_count": 1,
        },
    ),
    (
        "objective-header",
        {
            "created_at": "2025-01-01T00:00:00Z",
            "created_by": "test-user",
        },
    ),
    (
        "tripwire-candidates",
        {
            "candidates": [
                {
                    "action": "calling os.chdir()",
                    "warning": "Use pathlib instead",
                    "target_doc_path": "architecture/erk-architecture.md",
                }
            ]
        },
    ),
    (
        "objective-roadmap",
        {
            "nodes": [
                {"id": "1.1", "description": "First node", "status": "pending"}
            ]
        },
    ),
]


@pytest.mark.parametrize(
    "key,sample_data",
    YAML_BLOCK_SAMPLES,
    ids=[s[0] for s in YAML_BLOCK_SAMPLES],
)
def test_yaml_block_round_trip(key: str, sample_data: dict[str, Any]) -> None:
    """YAML blocks survive create -> render -> parse round-trip."""
    block = create_metadata_block(key=key, data=sample_data, schema=None)
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)

    assert len(result.blocks) == 1
    assert result.blocks[0].key == key
    assert result.blocks[0].data == sample_data
    assert not result.has_errors
    assert len(result.content_blocks) == 0


@pytest.mark.parametrize(
    "key,sample_data",
    YAML_BLOCK_SAMPLES,
    ids=[s[0] for s in YAML_BLOCK_SAMPLES],
)
def test_yaml_block_schema_round_trip(key: str, sample_data: dict[str, Any]) -> None:
    """YAML blocks created with their registered schema survive round-trip."""
    block_type = get_block_type(key)
    assert block_type is not None

    block = create_metadata_block(key=key, data=sample_data, schema=block_type.schema)
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)

    assert len(result.blocks) == 1
    assert result.blocks[0].data == sample_data


# --- Content block tests ---


def test_content_block_plan_body_not_in_errors() -> None:
    """plan-body blocks are routed to content_blocks, not errors."""
    block = MetadataBlock(key="plan-body", data={"content": "# My Plan\n\nSome content."})
    rendered = render_plan_body_block(block)
    result = parse_metadata_blocks(rendered)

    assert len(result.errors) == 0
    assert any(b.key == "plan-body" for b in result.content_blocks)
    assert len(result.blocks) == 0


def test_content_block_objective_body_not_in_errors() -> None:
    """objective-body blocks are routed to content_blocks, not errors."""
    rendered = render_objective_body_block("# Objective\n\nSome objective content.")
    result = parse_metadata_blocks(rendered)

    assert len(result.errors) == 0
    assert any(b.key == "objective-body" for b in result.content_blocks)
    assert len(result.blocks) == 0


def test_content_block_session_prompts_not_in_errors() -> None:
    """planning-session-prompts blocks are routed to content_blocks, not errors."""
    rendered = render_session_prompts_block(
        ["prompt 1", "prompt 2"],
        max_prompt_display_length=500,
    )
    result = parse_metadata_blocks(rendered)

    assert len(result.errors) == 0
    assert any(b.key == "planning-session-prompts" for b in result.content_blocks)
    assert len(result.blocks) == 0


# --- Registry completeness tests ---


def test_registry_has_all_block_types() -> None:
    """Registry contains all 13 block types."""
    all_types = get_all_block_types()
    assert len(all_types) == 13


def test_registry_yaml_count() -> None:
    """Registry has 10 YAML block types."""
    yaml_types = get_yaml_block_types()
    assert len(yaml_types) == 10
    assert all(t.category == BlockCategory.YAML for t in yaml_types)


def test_registry_content_count() -> None:
    """Registry has 3 content block types."""
    content_types = get_content_block_types()
    assert len(content_types) == 3
    assert all(t.category == BlockCategory.CONTENT for t in content_types)


def test_registry_yaml_and_content_are_disjoint() -> None:
    """YAML and content block sets don't overlap."""
    yaml_keys = {t.key for t in get_yaml_block_types()}
    content_keys = {t.key for t in get_content_block_types()}
    assert yaml_keys & content_keys == set()


def test_registry_covers_all_sample_data() -> None:
    """Every YAML sample has a corresponding registry entry."""
    for key, _ in YAML_BLOCK_SAMPLES:
        block_type = get_block_type(key)
        assert block_type is not None, f"Block type '{key}' not in registry"
        assert block_type.category == BlockCategory.YAML


def test_unknown_block_still_attempts_yaml_parse() -> None:
    """Blocks with unknown keys still attempt YAML parsing (backward compat)."""
    from erk_shared.gateway.github.metadata.core import create_metadata_block, render_metadata_block

    block = create_metadata_block(key="some-unknown-key", data={"field": "value"}, schema=None)
    rendered = render_metadata_block(block)
    result = parse_metadata_blocks(rendered)

    assert len(result.blocks) == 1
    assert result.blocks[0].key == "some-unknown-key"
    assert result.blocks[0].data == {"field": "value"}
    assert len(result.content_blocks) == 0
    assert len(result.errors) == 0
