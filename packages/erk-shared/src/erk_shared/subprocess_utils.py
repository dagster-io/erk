"""Simple subprocess utilities for erk-shared.

This module provides basic subprocess execution for GitHub CLI commands.
It's intentionally minimal to avoid pulling in complex dependencies.
"""

import logging
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Any

logger = logging.getLogger(__name__)


def _build_timing_description(cmd: Sequence[str]) -> str:
    """Build a timing log description from a command.

    For GraphQL queries, replaces the query text with a character count
    to avoid verbose output in logs.
    """
    cmd_list = list(cmd)
    # Check if this is a GraphQL command with query parameter
    if len(cmd_list) >= 4 and cmd_list[1:3] == ["api", "graphql"]:
        # Find query parameter and replace it
        result_parts = []
        for part in cmd_list:
            if part.startswith("query="):
                query_len = len(part) - len("query=")
                result_parts.append(f"query=<{query_len} chars>")
            else:
                result_parts.append(part)
        return " ".join(result_parts)
    return " ".join(str(arg) for arg in cmd)


def run_subprocess_with_context(
    cmd: Sequence[str],
    operation_context: str,
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    encoding: str = "utf-8",
    check: bool = True,
    stdout: int | IO[Any] | None = None,
    stderr: int | IO[Any] | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Execute subprocess with enriched error reporting for integration layer.

    Wraps subprocess.run() to catch CalledProcessError and re-raise as RuntimeError
    with operation context, stderr output, and command details.

    Args:
        cmd: Command and arguments to execute
        operation_context: Human-readable description of operation
        cwd: Working directory for command execution
        capture_output: Whether to capture stdout/stderr (default: True)
        text: Whether to decode output as text (default: True)
        encoding: Text encoding to use (default: "utf-8")
        check: Whether to raise on non-zero exit (default: True)
        stdout: File descriptor or file object for stdout
        stderr: File descriptor or file object for stderr
        **kwargs: Additional arguments passed to subprocess.run()

    Returns:
        CompletedProcess instance from subprocess.run()

    Raises:
        RuntimeError: If command fails with enriched error context
        FileNotFoundError: If command binary is not found
    """
    timing_desc = _build_timing_description(cmd)
    start_time = time.perf_counter()
    logger.debug("Starting: %s", timing_desc)

    try:
        # Handle stdout/stderr arguments
        if capture_output and (stdout is not None or stderr is not None):
            capture_output = False

        # Execute subprocess
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=text,
            encoding=encoding,
            check=check,
            stdout=stdout,
            stderr=stderr,
            **kwargs,
        )
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.debug("Completed in %dms: %s", elapsed_ms, timing_desc)
        return result

    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(str(arg) for arg in cmd)
        error_msg = f"Failed to {operation_context}"
        error_msg += f"\nCommand: {cmd_str}"
        error_msg += f"\nExit code: {e.returncode}"

        if e.stdout:
            stdout_text = e.stdout if isinstance(e.stdout, str) else e.stdout.decode("utf-8")
            stdout_stripped = stdout_text.strip()
            if stdout_stripped:
                error_msg += f"\nstdout: {stdout_stripped}"

        if e.stderr:
            stderr_text = e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8")
            stderr_stripped = stderr_text.strip()
            if stderr_stripped:
                error_msg += f"\nstderr: {stderr_stripped}"

        raise RuntimeError(error_msg) from e

    except FileNotFoundError as e:
        cmd_str = " ".join(str(arg) for arg in cmd)
        error_msg = f"Command not found while trying to {operation_context}: {cmd[0]}"
        error_msg += f"\nFull command: {cmd_str}"
        raise RuntimeError(error_msg) from e


def execute_gh_command(cmd: list[str], cwd: Path) -> str:
    """Execute a gh CLI command and return stdout.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for command execution

    Returns:
        stdout from the command

    Raises:
        RuntimeError: If command fails with enriched error context
        FileNotFoundError: If gh is not installed
    """
    timing_desc = _build_timing_description(cmd)
    result = run_subprocess_with_context(
        cmd,
        operation_context=f"execute gh command '{timing_desc}'",
        cwd=cwd,
    )
    stdout_preview = result.stdout[:200] if result.stdout else "(empty)"
    logger.debug("gh command stdout preview: %s", stdout_preview)
    return result.stdout
