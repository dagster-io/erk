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
from typing import Literal, cast

PlanBackendType = Literal["draft_pr", "github"]


def get_plan_backend() -> PlanBackendType:
    """Read plan backend from ERK_PLAN_BACKEND env var.

    Valid values: "github" (default), "draft_pr".
    """
    value = os.environ.get("ERK_PLAN_BACKEND", "github")
    if value not in ("draft_pr", "github"):
        return "github"
    return cast(PlanBackendType, value)
