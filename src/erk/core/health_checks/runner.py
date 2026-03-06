"""Health check runner abstraction for dependency injection.

Provides an ABC for running health checks, enabling tests to inject
fake results without monkeypatching.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from erk.core.health_checks import run_all_checks
from erk.core.health_checks.models import CheckResult

if TYPE_CHECKING:
    from erk_shared.context.context import ErkContext


class HealthCheckRunner(ABC):
    """Abstract interface for running health checks."""

    @abstractmethod
    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]: ...


class RealHealthCheckRunner(HealthCheckRunner):
    """Production implementation that delegates to run_all_checks."""

    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]:
        return run_all_checks(ctx, check_hooks=check_hooks)
