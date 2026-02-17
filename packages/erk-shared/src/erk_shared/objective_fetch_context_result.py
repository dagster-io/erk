"""TypedDict definitions for objective-fetch-context JSON output.

These types are the single source of truth for the JSON schema produced by
erk exec objective-fetch-context and consumed by the
objective-update-with-landed-pr slash command.
"""

from typing import TypedDict


class ObjectiveInfoDict(TypedDict):
    """Objective issue information."""

    number: int
    title: str
    body: str
    state: str
    labels: list[str]
    url: str


class PlanInfoDict(TypedDict):
    """Plan issue information."""

    number: int
    title: str
    body: str


class PRInfoDict(TypedDict):
    """PR information."""

    number: int
    title: str
    body: str
    url: str


class RoadmapContextDict(TypedDict):
    """Parsed roadmap context from the objective body."""

    phases: list[dict]
    matched_steps: list[str]
    summary: dict[str, int]
    next_step: dict[str, str] | None
    all_complete: bool


class ObjectiveFetchContextResultDict(TypedDict):
    """Successful result from objective-fetch-context command."""

    success: bool
    objective: ObjectiveInfoDict
    plan: PlanInfoDict
    pr: PRInfoDict
    roadmap: RoadmapContextDict


class ObjectiveFetchContextErrorDict(TypedDict):
    """Error result from objective-fetch-context command."""

    success: bool
    error: str
