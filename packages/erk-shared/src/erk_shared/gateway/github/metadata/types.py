"""Core data structures and constants for GitHub metadata blocks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class BlockKeys:
    """Canonical metadata block key constants.

    Import this class instead of hardcoding string literals::

        from erk_shared.gateway.github.metadata.types import BlockKeys

        find_metadata_block(body, BlockKeys.PLAN_HEADER)
    """

    PLAN_HEADER = "plan-header"
    PLAN_BODY = "plan-body"
    OBJECTIVE_HEADER = "objective-header"
    OBJECTIVE_BODY = "objective-body"
    OBJECTIVE_ROADMAP = "objective-roadmap"
    ERK_PLAN = "erk-plan"
    ERK_WORKTREE_CREATION = "erk-worktree-creation"
    ERK_IMPLEMENTATION_STATUS = "erk-implementation-status"
    WORKFLOW_STARTED = "workflow-started"
    SUBMISSION_QUEUED = "submission-queued"
    PLAN_RETRY = "plan-retry"
    IMPL_STARTED = "impl-started"
    IMPL_ENDED = "impl-ended"
    LEARN_INVOKED = "learn-invoked"
    TRIPWIRE_CANDIDATES = "tripwire-candidates"
    PLANNING_SESSION_PROMPTS = "planning-session-prompts"


@dataclass(frozen=True)
class MetadataBlock:
    """A metadata block with a key and structured YAML data."""

    key: str
    data: dict[str, Any]


@dataclass(frozen=True)
class RawMetadataBlock:
    """A raw metadata block with unparsed body content."""

    key: str
    body: str  # Raw content between HTML comment markers


@dataclass(frozen=True)
class MetadataBlockError:
    """A metadata block that failed to parse."""

    key: str
    message: str


@dataclass(frozen=True)
class MetadataParseResult:
    """Result of parsing metadata blocks, with explicit error reporting."""

    blocks: tuple[MetadataBlock, ...]
    errors: tuple[MetadataBlockError, ...]
    content_blocks: tuple[RawMetadataBlock, ...] = field(default_factory=tuple)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class MetadataBlockSchema(ABC):
    """Base class for metadata block schemas."""

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> None:
        """Validate data against schema. Raises ValueError if invalid."""
        ...

    @abstractmethod
    def get_key(self) -> str:
        """Return the metadata block key this schema validates."""
        ...
