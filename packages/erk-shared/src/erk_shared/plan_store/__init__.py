"""Provider-agnostic abstraction for plan storage.

This module provides interfaces and implementations for storing and retrieving
plans across different providers (GitHub, GitLab, Linear, Jira, etc.).

Import from submodules:
- types: Plan, PlanQuery, PlanState, CreatePlanResult
- backend: PlanBackend (preferred interface)
- store: PlanStore (deprecated, use PlanBackend)
- github: GitHubPlanStore
"""
