"""Block type registry for metadata block categorization.

Provides a central registry of all known metadata block types, categorized
as either YAML (structured data parsed as YAML) or CONTENT (raw content
like markdown that should not be YAML-parsed).
"""

from dataclasses import dataclass
from enum import Enum

from erk_shared.gateway.github.metadata.schemas import (
    ImplementationStatusSchema,
    ObjectiveHeaderSchema,
    PlanHeaderSchema,
    PlanRetrySchema,
    PlanSchema,
    SubmissionQueuedSchema,
    WorkflowStartedSchema,
    WorktreeCreationSchema,
)
from erk_shared.gateway.github.metadata.types import MetadataBlockSchema


class BlockCategory(Enum):
    """Category of a metadata block determining how it should be parsed."""

    YAML = "yaml"
    CONTENT = "content"


@dataclass(frozen=True)
class BlockTypeInfo:
    """Information about a registered metadata block type."""

    key: str
    category: BlockCategory
    schema: MetadataBlockSchema | None


# Central registry of all known metadata block types.
# YAML blocks have structured data parsed as YAML.
# CONTENT blocks contain raw content (markdown, etc.) that should not be YAML-parsed.
_BLOCK_TYPE_REGISTRY: dict[str, BlockTypeInfo] = {
    # YAML blocks with schemas
    "plan-header": BlockTypeInfo(
        key="plan-header",
        category=BlockCategory.YAML,
        schema=PlanHeaderSchema(),
    ),
    "objective-header": BlockTypeInfo(
        key="objective-header",
        category=BlockCategory.YAML,
        schema=ObjectiveHeaderSchema(),
    ),
    "erk-plan": BlockTypeInfo(
        key="erk-plan",
        category=BlockCategory.YAML,
        schema=PlanSchema(),
    ),
    "erk-worktree-creation": BlockTypeInfo(
        key="erk-worktree-creation",
        category=BlockCategory.YAML,
        schema=WorktreeCreationSchema(),
    ),
    "erk-implementation-status": BlockTypeInfo(
        key="erk-implementation-status",
        category=BlockCategory.YAML,
        schema=ImplementationStatusSchema(),
    ),
    "workflow-started": BlockTypeInfo(
        key="workflow-started",
        category=BlockCategory.YAML,
        schema=WorkflowStartedSchema(),
    ),
    "submission-queued": BlockTypeInfo(
        key="submission-queued",
        category=BlockCategory.YAML,
        schema=SubmissionQueuedSchema(),
    ),
    "plan-retry": BlockTypeInfo(
        key="plan-retry",
        category=BlockCategory.YAML,
        schema=PlanRetrySchema(),
    ),
    # YAML blocks without schemas
    "impl-started": BlockTypeInfo(
        key="impl-started",
        category=BlockCategory.YAML,
        schema=None,
    ),
    "impl-ended": BlockTypeInfo(
        key="impl-ended",
        category=BlockCategory.YAML,
        schema=None,
    ),
    "learn-invoked": BlockTypeInfo(
        key="learn-invoked",
        category=BlockCategory.YAML,
        schema=None,
    ),
    "tripwire-candidates": BlockTypeInfo(
        key="tripwire-candidates",
        category=BlockCategory.YAML,
        schema=None,
    ),
    "objective-roadmap": BlockTypeInfo(
        key="objective-roadmap",
        category=BlockCategory.YAML,
        schema=None,
    ),
    # Content blocks (not YAML-parsed)
    "plan-body": BlockTypeInfo(
        key="plan-body",
        category=BlockCategory.CONTENT,
        schema=None,
    ),
    "objective-body": BlockTypeInfo(
        key="objective-body",
        category=BlockCategory.CONTENT,
        schema=None,
    ),
    "planning-session-prompts": BlockTypeInfo(
        key="planning-session-prompts",
        category=BlockCategory.CONTENT,
        schema=None,
    ),
}


def get_block_type(key: str) -> BlockTypeInfo | None:
    """Look up a block type by key.

    Args:
        key: The metadata block key (e.g., "plan-header", "plan-body")

    Returns:
        BlockTypeInfo if the key is registered, None otherwise
    """
    return _BLOCK_TYPE_REGISTRY.get(key)


def get_all_block_types() -> dict[str, BlockTypeInfo]:
    """Return all registered block types.

    Returns:
        Dict mapping block key to BlockTypeInfo
    """
    return dict(_BLOCK_TYPE_REGISTRY)


def get_yaml_block_types() -> list[BlockTypeInfo]:
    """Return all block types that should be YAML-parsed.

    Returns:
        List of BlockTypeInfo with category YAML
    """
    return [info for info in _BLOCK_TYPE_REGISTRY.values() if info.category == BlockCategory.YAML]


def get_content_block_types() -> list[BlockTypeInfo]:
    """Return all block types that contain raw content (not YAML).

    Returns:
        List of BlockTypeInfo with category CONTENT
    """
    return [
        info for info in _BLOCK_TYPE_REGISTRY.values() if info.category == BlockCategory.CONTENT
    ]
