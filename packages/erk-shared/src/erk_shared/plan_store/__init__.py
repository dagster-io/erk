"""Provider-agnostic abstraction for plan storage.

This module provides interfaces and implementations for storing and retrieving
plans across different providers.

Import from submodules:
- types: Plan, PlanQuery, PlanState, CreatePlanResult
- backend: PlanBackend (abstract interface for plan storage operations)
- planned_pr: PlannedPRBackend (implementation using GitHub PRs)

Note: PlanBackend is a BACKEND (composes gateways), not a gateway. It has no
fake implementation. Test by injecting fake gateways into real backends.
"""
