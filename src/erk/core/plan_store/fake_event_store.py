"""In-memory fake implementation for plan event storage.

This module re-exports from erk_shared.plan_store.fake_event_store for backwards compatibility.
New code should import directly from erk_shared.plan_store.fake_event_store.
"""

from erk_shared.plan_store.fake_event_store import FakePlanEventStore

__all__ = ["FakePlanEventStore"]
