"""Provider-agnostic abstraction for managed PR storage.

This module provides interfaces and implementations for storing and retrieving
managed PRs (erk's structured draft PRs with metadata blocks, session tracking,
and lifecycle stages) across different providers.

Import from submodules:
- types: Plan, PlanQuery, PlanState, CreatePlanResult
- backend: ManagedPrBackend (abstract interface for managed PR operations)
- planned_pr: ManagedGitHubPrBackend (implementation using GitHub PRs)

Note: ManagedPrBackend is a BACKEND (composes gateways), not a gateway. It has no
fake implementation. Test by injecting fake gateways into real backends.
"""
