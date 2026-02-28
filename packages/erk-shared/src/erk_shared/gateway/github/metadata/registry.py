"""Block type registry for metadata blocks.

Maps all known block keys to their category (YAML vs content) and schema.
This is the single source of truth for block type metadata.
"""

from __future__ import annotations

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
    """Category of a metadata block."""

    YAML = "yaml"
    CONTENT = "content"


@dataclass(frozen=True)
class BlockTypeInfo:
    """Information about a registered block type."""

    key: str
    category: BlockCategory
    schema: MetadataBlockSchema | None


# The canonical registry of all known block types.
# Populated at import time. New block types MUST be added here.
_REGISTRY: dict[str, BlockTypeInfo] = {}


def _register(key: str, category: BlockCategory, schema: MetadataBlockSchema | None) -> None:
    _REGISTRY[key] = BlockTypeInfo(key=key, category=category, schema=schema)


# --- YAML blocks (10) ---
_register("plan-header", BlockCategory.YAML, PlanHeaderSchema())
_register("erk-plan", BlockCategory.YAML, PlanSchema())
_register("erk-implementation-status", BlockCategory.YAML, ImplementationStatusSchema())
_register("erk-worktree-creation", BlockCategory.YAML, WorktreeCreationSchema())
_register("submission-queued", BlockCategory.YAML, SubmissionQueuedSchema())
_register("workflow-started", BlockCategory.YAML, WorkflowStartedSchema())
_register("plan-retry", BlockCategory.YAML, PlanRetrySchema())
_register("objective-header", BlockCategory.YAML, ObjectiveHeaderSchema())
_register("tripwire-candidates", BlockCategory.YAML, None)
_register("objective-roadmap", BlockCategory.YAML, None)

# --- Content blocks (3) ---
_register("plan-body", BlockCategory.CONTENT, None)
_register("objective-body", BlockCategory.CONTENT, None)
_register("planning-session-prompts", BlockCategory.CONTENT, None)


def get_block_type(key: str) -> BlockTypeInfo | None:
    """Look up a block type by key.

    Returns None if the key is not registered.
    """
    return _REGISTRY.get(key)


def get_all_block_types() -> dict[str, BlockTypeInfo]:
    """Return a copy of the full registry."""
    return dict(_REGISTRY)


def get_yaml_block_types() -> list[BlockTypeInfo]:
    """Return all YAML-category block types."""
    return [info for info in _REGISTRY.values() if info.category == BlockCategory.YAML]


def get_content_block_types() -> list[BlockTypeInfo]:
    """Return all content-category block types."""
    return [info for info in _REGISTRY.values() if info.category == BlockCategory.CONTENT]
