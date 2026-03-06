"""Health check runner abstraction for dependency injection.

Provides an ABC for running health checks, enabling tests to inject
fake results without monkeypatching.

The real implementation (RealHealthCheckRunner) remains in
erk.core.health_checks.runner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk.core.health_checks.models import CheckResult
    from erk_shared.context.context import ErkContext


class HealthCheckRunner(ABC):
    """Abstract interface for running health checks."""

    @abstractmethod
    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]: ...
