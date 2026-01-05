"""Event types for GT operations.

Operations yield events instead of using click.echo directly, enabling:
1. Pure business logic (no CLI dependencies)
2. Testable progress assertions
3. Flexible rendering (CLI, JSON, silent)
"""

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ProgressEvent:
    """Progress notification during operation.

    Yielded by operations to report progress. CLI layer renders these
    appropriately (typically to stderr).

    Attributes:
        message: Human-readable progress message
        style: Visual style hint for rendering
    """

    message: str
    style: Literal["info", "success", "warning", "error"] = "info"


@dataclass(frozen=True)
class CompletionEvent(Generic[T]):
    """Final result of an operation.

    Yielded as the last event by an operation. Contains the result
    that would have been returned directly in the old API.

    Attributes:
        result: The operation result (success or error dataclass)
    """

    result: T
