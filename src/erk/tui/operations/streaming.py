"""Streaming operation infrastructure for TUI background tasks."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import click

from erk.tui.operations.types import OperationResult

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp


class StreamingOperationsMixin:
    """Mixin providing operation lifecycle tracking and streaming subprocess execution.

    Methods access self._status_bar, self._provider, and self.call_from_thread
    which are provided by ErkDashApp at runtime through inheritance.
    """

    def _start_operation(self: ErkDashApp, *, op_id: str, label: str) -> None:
        """Register a background operation in the status bar."""
        if self._status_bar is not None:
            self._status_bar.start_operation(op_id=op_id, label=label)

    def _update_operation(self: ErkDashApp, *, op_id: str, progress: str) -> None:
        """Update the progress line for a background operation."""
        if self._status_bar is not None:
            self._status_bar.update_operation(op_id=op_id, progress=progress)

    def _finish_operation(self: ErkDashApp, *, op_id: str) -> None:
        """Remove a completed background operation from the status bar."""
        if self._status_bar is not None:
            self._status_bar.finish_operation(op_id=op_id)

    def _run_streaming_operation(
        self: ErkDashApp,
        *,
        op_id: str,
        command: list[str],
    ) -> OperationResult:
        """Run a subprocess with live output streaming to the status bar.

        Must be called from a background thread (@work(thread=True)).
        Uses Popen with merged stdout/stderr for real-time progress.

        Args:
            op_id: Operation identifier for status bar updates
            command: Command and arguments to execute

        Returns:
            Result with success flag, collected output lines, and return code
        """
        output_lines: list[str] = []
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            bufsize=1,
            text=True,
            cwd=str(self._provider.repo_root),
        )
        if proc.stdout is not None:
            for line in proc.stdout:
                clean = click.unstyle(line.rstrip())
                if clean:
                    output_lines.append(clean)
                    self.call_from_thread(self._update_operation, op_id=op_id, progress=clean)
        return_code = proc.wait()
        return OperationResult(
            success=return_code == 0,
            output_lines=tuple(output_lines),
            return_code=return_code,
        )
