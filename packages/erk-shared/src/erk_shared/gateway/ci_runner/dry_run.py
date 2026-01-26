"""No-op CI runner for dry-run mode.

This module provides a CI runner that prevents actual command execution
while logging what would have been done.
"""

from pathlib import Path

from erk_shared.gateway.ci_runner.abc import CICheckResult, CIRunner
from erk_shared.output.output import user_output


class DryRunCIRunner(CIRunner):
    """No-op wrapper that prevents CI command execution in dry-run mode.

    All CI operations are mutations (they run commands),
    so all methods are no-ops that print what would happen.
    """

    def __init__(self, wrapped: CIRunner) -> None:
        """Create a dry-run wrapper around a CIRunner implementation.

        Args:
            wrapped: The CIRunner implementation to wrap
        """
        self._wrapped = wrapped

    def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult:
        """No-op for CI check in dry-run mode."""
        cmd_str = " ".join(cmd)
        user_output(f"[DRY RUN] Would run CI check '{name}': {cmd_str}")
        return CICheckResult(passed=True, error_type=None)
