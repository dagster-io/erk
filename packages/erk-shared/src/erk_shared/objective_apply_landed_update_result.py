"""TypedDict definitions for objective-apply-landed-update JSON output.

These types are the single source of truth for the JSON schema produced by
erk exec objective-apply-landed-update and consumed by the
objective-update-with-landed-pr slash command.
"""

from typing import TypedDict

from erk_shared.objective_fetch_context_result import (
    ObjectiveInfoDict,
    PlanInfoDict,
    PRInfoDict,
    RoadmapContextDict,
)


class NodeUpdateDict(TypedDict):
    """Information about a single node update."""

    node_id: str
    previous_pr: str | None


class ApplyLandedUpdateResultDict(TypedDict):
    """Successful result from objective-apply-landed-update command."""

    success: bool
    objective: ObjectiveInfoDict
    plan: PlanInfoDict
    pr: PRInfoDict
    roadmap: RoadmapContextDict
    node_updates: list[NodeUpdateDict]
    action_comment_id: int


class ApplyLandedUpdateErrorDict(TypedDict):
    """Error result from objective-apply-landed-update command."""

    success: bool
    error: str
