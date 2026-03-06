"""Health check runner - real implementation.

The HealthCheckRunner ABC is defined in erk_shared.core.health_check_runner
to avoid circular imports. This module provides the real implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from erk_shared.core.health_check_runner import HealthCheckRunner

if TYPE_CHECKING:
    from erk.core.health_checks.models import CheckResult
    from erk_shared.context.context import ErkContext


class RealHealthCheckRunner(HealthCheckRunner):
    """Production implementation that delegates to run_all_checks."""

    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]:
        from erk.core.health_checks import run_all_checks

        return run_all_checks(ctx, check_hooks=check_hooks)
