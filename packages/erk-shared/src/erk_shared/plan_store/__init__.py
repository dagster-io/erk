"""Provider-agnostic abstraction for plan storage.

This module provides interfaces and implementations for storing and retrieving
plans across different providers (GitHub, GitLab, Linear, Jira, etc.).

Import from submodules:
- types: Plan, PlanQuery, PlanState, CreatePlanResult
- store: PlanStore (read-only, deprecated - use backend.PlanBackend)
- backend: PlanBackend (full read/write interface, composes gateways)
- github: GitHubPlanStore

Note: PlanBackend is a BACKEND (composes gateways), not a gateway. It has no
fake implementation. Test by injecting fake gateways into real backends.
"""

import os


def get_plan_backend() -> str:
    """Read plan backend from ERK_PLAN_BACKEND env var.

    Valid values: "github" (default), "draft_pr".
    """
    return os.environ.get("ERK_PLAN_BACKEND", "github")
