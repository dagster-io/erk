"""Core types for planner box management.

A planner box is a registered GitHub Codespace dedicated to remote planning
with Claude Code. This module defines the data structures for tracking
registered planners.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RegisteredPlanner:
    """A registered planner box (GitHub Codespace for planning).

    Attributes:
        name: Friendly name for the planner (used as key)
        gh_name: GitHub codespace name (e.g., "schrockn-curly-rotary-phone-abc123")
        repository: Repository the codespace belongs to (e.g., "dagster-io/dagster")
        configured: Whether the configure wizard has been completed
        registered_at: When the planner was registered
        last_connected_at: When the planner was last connected to (None if never)
    """

    name: str
    gh_name: str
    repository: str
    configured: bool
    registered_at: datetime
    last_connected_at: datetime | None = None
