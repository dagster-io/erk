"""TypedDict definitions for objective-update-context JSON output.

These types are the single source of truth for the JSON schema produced by
erk exec objective-update-context and consumed by the
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


class ObjectiveUpdateContextResultDict(TypedDict):
    """Successful result from objective-update-context command."""

    success: bool
    objective: ObjectiveInfoDict
    plan: PlanInfoDict
    pr: PRInfoDict


class ObjectiveUpdateContextErrorDict(TypedDict):
    """Error result from objective-update-context command."""

    success: bool
    error: str
