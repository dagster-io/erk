"""Fake health check runner for testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from erk.core.health_checks.models import CheckResult
from erk_shared.core.health_check_runner import HealthCheckRunner

if TYPE_CHECKING:
    from erk_shared.context.context import ErkContext


class FakeHealthCheckRunner(HealthCheckRunner):
    """Test fake that returns pre-configured check results."""

    def __init__(self, *, results: list[CheckResult]) -> None:
        self._results = results

    def run_all(self, ctx: ErkContext, *, check_hooks: bool) -> list[CheckResult]:
        return self._results
