"""GitHub implementation of plan event storage.

This module re-exports from erk_shared.plan_store.github_event_store for backwards compatibility.
New code should import directly from erk_shared.plan_store.github_event_store.
"""

from erk_shared.plan_store.github_event_store import GitHubPlanEventStore

__all__ = ["GitHubPlanEventStore"]
