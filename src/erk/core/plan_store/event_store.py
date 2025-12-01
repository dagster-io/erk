"""Abstract interface for plan event storage providers.

This module re-exports from erk_shared.plan_store.event_store for backwards compatibility.
New code should import directly from erk_shared.plan_store.event_store.
"""

from erk_shared.plan_store.event_store import PlanEvent, PlanEventStore, PlanEventType

__all__ = ["PlanEvent", "PlanEventStore", "PlanEventType"]
