"""Printing CI runner wrapper for verbose output.

This module provides a CI runner wrapper that prints styled output
for operations before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.ci_runner.abc import CICheckResult, CIRunner
from erk_shared.printing.base import PrintingBase


class PrintingCIRunner(PrintingBase, CIRunner):
    """Wrapper that prints CI operations before delegating.

    This wrapper prints styled output for CI operations, then delegates
    to the wrapped implementation (which could be Real or DryRun).
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    def run_check(self, *, name: str, cmd: list[str], cwd: Path) -> CICheckResult:
        """Run CI check with printed output."""
        cmd_str = " ".join(cmd)
        self._emit(self._format_command(f"CI check '{name}': {cmd_str}"))
        return self._wrapped.run_check(name=name, cmd=cmd, cwd=cwd)
