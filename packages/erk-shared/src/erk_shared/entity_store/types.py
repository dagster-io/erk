"""Core data types for the entity store."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EntityKind(Enum):
    ISSUE = "issue"
    PR = "pr"


@dataclass(frozen=True)
class LogEntry:
    """An immutable log entry extracted from a GitHub comment."""

    key: str
    data: dict[str, Any]
    comment_id: int
