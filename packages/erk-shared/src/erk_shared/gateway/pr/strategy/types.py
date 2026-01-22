"""Type definitions for PR submit strategy pattern.

These types define the result and error types returned by submit strategies,
enabling a unified interface across different submission flows (Graphite, standard).
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent


@dataclass(frozen=True)
class SubmitStrategyResult:
    """Result from any submit strategy.

    Represents a successful PR submission via any strategy (Graphite or standard).
    Contains all information needed for subsequent phases (diff extraction, finalize).
    """

    pr_number: int
    base_branch: str
    graphite_url: str | None  # None for standard (non-Graphite) flow
    pr_url: str
    branch_name: str
    was_created: bool


@dataclass(frozen=True)
class SubmitStrategyError:
    """Error from submit strategy.

    Represents a failure during PR submission. The error_type field enables
    programmatic handling of different failure modes.
    """

    error_type: str
    message: str
    details: dict[str, str]


# Type alias for strategy execute() return type - avoids 100+ char lines
StrategyOutcome = SubmitStrategyResult | SubmitStrategyError
StrategyGenerator = Generator[
    "ProgressEvent | CompletionEvent[StrategyOutcome]",
    None,
    None,
]
