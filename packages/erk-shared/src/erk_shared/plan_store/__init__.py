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

from __future__ import annotations

import os
from typing import cast

from erk_shared.context.types import PlanBackendType


def get_plan_backend() -> PlanBackendType:
    """Resolve plan backend: env var > default ("github").

    Two-tier resolution:
    1. ERK_PLAN_BACKEND env var (highest priority, for CI)
    2. "github" (default)

    Returns:
        Resolved plan backend type.
    """
    env_value = os.environ.get("ERK_PLAN_BACKEND")
    if env_value is not None and env_value in ("draft_pr", "github"):
        return cast(PlanBackendType, env_value)
    return "github"
