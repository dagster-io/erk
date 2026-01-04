"""Provider-agnostic abstraction for plan storage.

This module provides interfaces and implementations for storing and retrieving
plans across different providers (GitHub, GitLab, Linear, Jira, etc.).

Import from submodules:
- types: Plan, PlanQuery, PlanState, CreatePlanResult
- store: PlanStore (read-only, deprecated - use backend.PlanBackend)
- backend: PlanBackend (full read/write interface, composes gateways)
- github: GitHubPlanStore (implements PlanBackend)

Note: PlanBackend is a BACKEND (composes gateways), not a gateway. It has no
fake implementation. Test by injecting fake gateways into real backends.

Example:
    from erk_shared.plan_store.github import GitHubPlanStore
    from erk_shared.plan_store.types import CreatePlanResult

    store = GitHubPlanStore(github_issues)
    result = store.create_plan(repo_root, title, content, labels, metadata)
"""
