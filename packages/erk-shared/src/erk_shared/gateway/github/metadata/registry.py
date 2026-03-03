"""Block type registry for metadata block categorization.

Provides a central registry of all known metadata block types, categorized
as either YAML (structured data parsed as YAML) or CONTENT (raw content
like markdown that should not be YAML-parsed).

Block key constants are defined in ``types.BlockKeys``. Import
``BlockKeys`` instead of hardcoding string literals in production code.
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
from erk_shared.gateway.github.metadata.types import BlockKeys, MetadataBlockSchema


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
    BlockKeys.PLAN_HEADER: BlockTypeInfo(
        key=BlockKeys.PLAN_HEADER,
        category=BlockCategory.YAML,
        schema=PlanHeaderSchema(),
    ),
    BlockKeys.OBJECTIVE_HEADER: BlockTypeInfo(
        key=BlockKeys.OBJECTIVE_HEADER,
        category=BlockCategory.YAML,
        schema=ObjectiveHeaderSchema(),
    ),
    BlockKeys.ERK_PLAN: BlockTypeInfo(
        key=BlockKeys.ERK_PLAN,
        category=BlockCategory.YAML,
        schema=PlanSchema(),
    ),
    BlockKeys.ERK_WORKTREE_CREATION: BlockTypeInfo(
        key=BlockKeys.ERK_WORKTREE_CREATION,
        category=BlockCategory.YAML,
        schema=WorktreeCreationSchema(),
    ),
    BlockKeys.ERK_IMPLEMENTATION_STATUS: BlockTypeInfo(
        key=BlockKeys.ERK_IMPLEMENTATION_STATUS,
        category=BlockCategory.YAML,
        schema=ImplementationStatusSchema(),
    ),
    BlockKeys.WORKFLOW_STARTED: BlockTypeInfo(
        key=BlockKeys.WORKFLOW_STARTED,
        category=BlockCategory.YAML,
        schema=WorkflowStartedSchema(),
    ),
    BlockKeys.SUBMISSION_QUEUED: BlockTypeInfo(
        key=BlockKeys.SUBMISSION_QUEUED,
        category=BlockCategory.YAML,
        schema=SubmissionQueuedSchema(),
    ),
    BlockKeys.PLAN_RETRY: BlockTypeInfo(
        key=BlockKeys.PLAN_RETRY,
        category=BlockCategory.YAML,
        schema=PlanRetrySchema(),
    ),
    # YAML blocks without schemas
    BlockKeys.IMPL_STARTED: BlockTypeInfo(
        key=BlockKeys.IMPL_STARTED,
        category=BlockCategory.YAML,
        schema=None,
    ),
    BlockKeys.IMPL_ENDED: BlockTypeInfo(
        key=BlockKeys.IMPL_ENDED,
        category=BlockCategory.YAML,
        schema=None,
    ),
    BlockKeys.LEARN_INVOKED: BlockTypeInfo(
        key=BlockKeys.LEARN_INVOKED,
        category=BlockCategory.YAML,
        schema=None,
    ),
    BlockKeys.TRIPWIRE_CANDIDATES: BlockTypeInfo(
        key=BlockKeys.TRIPWIRE_CANDIDATES,
        category=BlockCategory.YAML,
        schema=None,
    ),
    BlockKeys.OBJECTIVE_ROADMAP: BlockTypeInfo(
        key=BlockKeys.OBJECTIVE_ROADMAP,
        category=BlockCategory.YAML,
        schema=None,
    ),
    # Content blocks (not YAML-parsed)
    BlockKeys.PLAN_BODY: BlockTypeInfo(
        key=BlockKeys.PLAN_BODY,
        category=BlockCategory.CONTENT,
        schema=None,
    ),
    BlockKeys.OBJECTIVE_BODY: BlockTypeInfo(
        key=BlockKeys.OBJECTIVE_BODY,
        category=BlockCategory.CONTENT,
        schema=None,
    ),
    BlockKeys.PLANNING_SESSION_PROMPTS: BlockTypeInfo(
        key=BlockKeys.PLANNING_SESSION_PROMPTS,
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
