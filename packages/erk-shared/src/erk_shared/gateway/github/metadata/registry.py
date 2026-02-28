"""Block type registry for metadata blocks.

Maps all known block keys to their category (YAML vs content) and schema.
This is the single source of truth for block type metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.github.metadata.types import MetadataBlockSchema


class BlockCategory(Enum):
    """Category of a metadata block."""

    YAML = "yaml"
    CONTENT = "content"


@dataclass(frozen=True)
class BlockTypeInfo:
    """Information about a registered block type."""

    key: str
    category: BlockCategory
    schema: MetadataBlockSchema | None


@cache
def _build_registry() -> dict[str, BlockTypeInfo]:
    """Build the block type registry on first access.

    New block types MUST be added here.
    """
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

    registry: dict[str, BlockTypeInfo] = {}

    def register(key: str, category: BlockCategory, schema: MetadataBlockSchema | None) -> None:
        registry[key] = BlockTypeInfo(key=key, category=category, schema=schema)

    # --- YAML blocks (10) ---
    register("plan-header", BlockCategory.YAML, PlanHeaderSchema())
    register("erk-plan", BlockCategory.YAML, PlanSchema())
    register("erk-implementation-status", BlockCategory.YAML, ImplementationStatusSchema())
    register("erk-worktree-creation", BlockCategory.YAML, WorktreeCreationSchema())
    register("submission-queued", BlockCategory.YAML, SubmissionQueuedSchema())
    register("workflow-started", BlockCategory.YAML, WorkflowStartedSchema())
    register("plan-retry", BlockCategory.YAML, PlanRetrySchema())
    register("objective-header", BlockCategory.YAML, ObjectiveHeaderSchema())
    register("tripwire-candidates", BlockCategory.YAML, None)
    register("objective-roadmap", BlockCategory.YAML, None)

    # --- Content blocks (3) ---
    register("plan-body", BlockCategory.CONTENT, None)
    register("objective-body", BlockCategory.CONTENT, None)
    register("planning-session-prompts", BlockCategory.CONTENT, None)

    return registry


def get_block_type(key: str) -> BlockTypeInfo | None:
    """Look up a block type by key.

    Returns None if the key is not registered.
    """
    return _build_registry().get(key)


def get_all_block_types() -> dict[str, BlockTypeInfo]:
    """Return a copy of the full registry."""
    return dict(_build_registry())


def get_yaml_block_types() -> list[BlockTypeInfo]:
    """Return all YAML-category block types."""
    return [info for info in _build_registry().values() if info.category == BlockCategory.YAML]


def get_content_block_types() -> list[BlockTypeInfo]:
    """Return all content-category block types."""
    return [info for info in _build_registry().values() if info.category == BlockCategory.CONTENT]
