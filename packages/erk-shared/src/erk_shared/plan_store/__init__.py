"""Provider-agnostic abstraction for plan storage.

This module provides interfaces and implementations for storing and retrieving
plans across different providers (GitHub, GitLab, Linear, Jira, etc.).

Import from submodules:
- types: Plan, PlanQuery, PlanState
- store: PlanStore
- github: GitHubPlanStore
"""
