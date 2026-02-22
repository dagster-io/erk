"""Provider-agnostic abstraction for plan storage.

This module provides interfaces and implementations for storing and retrieving
plans via draft-PR-based plan storage.

Import from submodules:
- types: Plan, PlanQuery, PlanState, CreatePlanResult
- store: PlanStore (read-only, deprecated - use backend.PlanBackend)
- backend: PlanBackend (full read/write interface, composes gateways)

Note: PlanBackend is a BACKEND (composes gateways), not a gateway. It has no
fake implementation. Test by injecting fake gateways into real backends.
"""
