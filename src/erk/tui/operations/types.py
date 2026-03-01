"""Types for TUI background operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationResult:
    """Result of a streaming subprocess operation."""

    success: bool
    output_lines: tuple[str, ...]
    return_code: int
