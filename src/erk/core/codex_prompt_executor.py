"""Codex CLI prompt execution implementation.

This module provides the CodexPromptExecutor implementation that maps erk's
PromptExecutor ABC to OpenAI's Codex CLI. Codex uses a completely different
CLI interface and JSONL streaming format from Claude.

See docs/learned/integrations/codex/codex-cli-reference.md for flag mapping.
See docs/learned/integrations/codex/codex-jsonl-format.md for output format.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from erk.core.codex_output_parser import CodexParserState, parse_codex_jsonl_line
from erk_shared.context.types import permission_mode_to_codex_exec, permission_mode_to_codex_tui
from erk_shared.core.prompt_executor import (
    ErrorEvent,
    ExecutorEvent,
    NoOutputEvent,
    NoTurnsEvent,
    ProcessErrorEvent,
    PromptExecutor,
    PromptResult,
)
from erk_shared.gateway.console.abc import Console
from erk_shared.gateway.console.real import InteractiveConsole

if TYPE_CHECKING:
    from erk_shared.context.types import PermissionMode

# Constants for process execution
PROCESS_TIMEOUT_SECONDS = 600  # 10 minutes
STDERR_JOIN_TIMEOUT = 5.0  # 5 seconds

logger = logging.getLogger(__name__)


def build_codex_exec_args(
    *,
    prompt: str,
    worktree_path: Path,
    permission_mode: PermissionMode,
    json_output: bool,
    model: str | None,
) -> list[str]:
    """Build CLI arguments for codex exec.

    Extracted as a module-level function for testability.

    Args:
        prompt: The prompt text to send.
        worktree_path: Working directory for the agent (passed via --cd).
        permission_mode: Generic permission mode mapped to Codex flags.
        json_output: Whether to request JSONL output (--json flag).
        model: Optional model name to pass via --model.

    Returns:
        List of CLI argument strings.
    """
    cmd = ["codex", "exec"]
    if json_output:
        cmd.append("--json")
    cmd.extend(["--cd", str(worktree_path)])
    cmd.extend(permission_mode_to_codex_exec(permission_mode))
    if model is not None:
        cmd.extend(["--model", model])
    cmd.append(prompt)
    return cmd


def build_codex_tui_args(
    *,
    target_dir: Path,
    permission_mode: PermissionMode,
    model: str | None,
    command: str,
) -> list[str]:
    """Build CLI arguments for codex TUI (interactive) mode.

    Extracted as a module-level function for testability.

    Args:
        target_dir: Directory to start in (passed via --cd).
        permission_mode: Generic permission mode mapped to Codex TUI flags.
        model: Optional model name to pass via --model.
        command: Optional prompt text (positional, since Codex TUI has no slash commands).

    Returns:
        List of CLI argument strings.
    """
    cmd = ["codex"]
    cmd.extend(["--cd", str(target_dir)])
    cmd.extend(permission_mode_to_codex_tui(permission_mode))
    if model is not None:
        cmd.extend(["--model", model])
    if command:
        cmd.append(command)
    return cmd


def build_codex_prompt_args(
    *,
    prompt: str,
    cwd: Path | None,
    permission_mode: PermissionMode,
    model: str,
    output_file: Path,
    system_prompt: str | None,
) -> list[str]:
    """Build CLI arguments for codex exec in prompt mode (non-streaming).

    Args:
        prompt: The prompt text. If system_prompt is provided, it is prepended.
        cwd: Working directory (passed via --cd if provided).
        permission_mode: Generic permission mode mapped to Codex exec flags.
        model: Model name to pass via --model.
        output_file: Path for --output-last-message.
        system_prompt: Optional system prompt prepended to user prompt.

    Returns:
        List of CLI argument strings.
    """
    cmd = ["codex", "exec"]
    cmd.extend(["--output-last-message", str(output_file)])
    if cwd is not None:
        cmd.extend(["--cd", str(cwd)])
    cmd.extend(["--model", model])
    cmd.extend(permission_mode_to_codex_exec(permission_mode))

    # Codex has no --system-prompt flag; prepend to user prompt
    if system_prompt is not None:
        full_prompt = f"<system>\n{system_prompt}\n</system>\n\n{prompt}"
    else:
        full_prompt = prompt

    cmd.append(full_prompt)
    return cmd


class CodexPromptExecutor(PromptExecutor):
    """Production implementation using subprocess and Codex CLI."""

    def __init__(self, console: Console | None) -> None:
        """Initialize CodexPromptExecutor with Console dependency.

        Args:
            console: Console gateway for TTY detection.
                If None, creates an InteractiveConsole instance.
        """
        self._console = console if console is not None else InteractiveConsole()

    def is_available(self) -> bool:
        """Check if Codex CLI is in PATH using shutil.which."""
        return shutil.which("codex") is not None

    def execute_command_streaming(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
        model: str | None = None,
        permission_mode: PermissionMode,
        allow_dangerous: bool = False,
    ) -> Iterator[ExecutorEvent]:
        """Execute Codex CLI command and yield typed events in real-time.

        Implementation details:
        - Uses codex exec --json for JSONL streaming output
        - Passes --cd for working directory (Codex ignores subprocess cwd=)
        - Maps permission_mode to Codex exec flags
        - In verbose mode: runs without --json, output direct to terminal
        - In filtered mode: parses JSONL and yields ExecutorEvent types
        - dangerous/allow_dangerous: ignored (no Codex equivalent, logged at DEBUG)
        """
        if dangerous:
            logger.debug("dangerous flag ignored for Codex (no equivalent)")
        if allow_dangerous:
            logger.debug("allow_dangerous flag ignored for Codex (no equivalent)")

        if verbose:
            # Verbose mode: run without --json, output to terminal
            cmd_args = build_codex_exec_args(
                prompt=command,
                worktree_path=worktree_path,
                permission_mode=permission_mode,
                json_output=False,
                model=model,
            )
            result = subprocess.run(cmd_args, check=False)
            if result.returncode != 0:
                yield ErrorEvent(message=f"Codex command failed with exit code {result.returncode}")
            return

        # Filtered mode: streaming with JSONL parsing
        cmd_args = build_codex_exec_args(
            prompt=command,
            worktree_path=worktree_path,
            permission_mode=permission_mode,
            json_output=True,
            model=model,
        )

        if debug:
            print(f"[DEBUG codex-executor] Starting Popen with args: {cmd_args}", file=sys.stderr)
            sys.stderr.flush()

        try:
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
        except OSError as e:
            yield ProcessErrorEvent(
                message=f"Failed to start Codex CLI: {e}\nCommand: {' '.join(cmd_args)}"
            )
            return

        stderr_output: list[str] = []

        def capture_stderr() -> None:
            if process.stderr:
                for line in process.stderr:
                    stderr_output.append(line)

        stderr_thread = threading.Thread(target=capture_stderr, daemon=True)
        stderr_thread.start()

        # Parse JSONL output line by line
        state = CodexParserState()
        line_count = 0

        if process.stdout:
            for line in process.stdout:
                line_count += 1
                if not line.strip():
                    continue
                events = parse_codex_jsonl_line(line, worktree_path, state)
                yield from events

        # Wait for process completion
        try:
            returncode = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            timeout_minutes = PROCESS_TIMEOUT_SECONDS // 60
            yield ProcessErrorEvent(
                message=f"Codex command timed out after {timeout_minutes} minutes"
            )
            return

        stderr_thread.join(timeout=STDERR_JOIN_TIMEOUT)

        # Detect no output condition
        if line_count == 0:
            diag = "Codex command completed but produced no output"
            diag += f"\n  Exit code: {returncode}"
            diag += f"\n  Working directory: {worktree_path}"
            if stderr_output:
                diag += "\n  Stderr:\n" + "".join(stderr_output)
            yield NoOutputEvent(diagnostic=diag)
            if returncode != 0:
                yield ErrorEvent(message=f"Exit code {returncode}")
            return

        # Hook blocking detection: if no items appeared, emit NoTurnsEvent
        if not state.saw_any_items and returncode == 0:
            diag = "Codex command completed without processing any items"
            diag += "\n  This may indicate the agent had nothing to do"
            diag += f"\n  Working directory: {worktree_path}"
            yield NoTurnsEvent(diagnostic=diag)

        # No text output detection
        if not state.saw_any_text and returncode == 0 and state.saw_any_items:
            diag = "Codex command completed but produced no text output"
            diag += f"\n  Working directory: {worktree_path}"
            yield NoOutputEvent(diagnostic=diag)

        # Non-zero exit code
        if returncode != 0:
            error_msg = "Codex command failed"
            error_msg += f"\n  Exit code: {returncode}"
            error_msg += f"\n  Lines processed: {line_count}"
            if stderr_output:
                error_msg += "\n  Stderr:\n" + "".join(stderr_output).strip()
            yield ErrorEvent(message=error_msg)

    def execute_interactive(
        self,
        *,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
        permission_mode: PermissionMode,
    ) -> None:
        """Execute Codex CLI in interactive TUI mode by replacing current process.

        Implementation details:
        - Verifies Codex CLI is available
        - Uses --cd flag for working directory (not subprocess cwd)
        - Maps permission_mode to Codex TUI flags
        - Codex TUI has no slash commands; command text is positional prompt
        - Replaces current process using os.execvp
        """
        if not self.is_available():
            raise RuntimeError("Codex CLI not found\nInstall from: https://github.com/openai/codex")

        if target_subpath is not None:
            target_dir = worktree_path / target_subpath
        else:
            target_dir = worktree_path

        cmd_args = build_codex_tui_args(
            target_dir=target_dir,
            permission_mode=permission_mode,
            model=model,
            command=command,
        )

        # Redirect stdin/stdout/stderr to /dev/tty if not already TTYs
        if not (self._console.is_stdout_tty() and self._console.is_stderr_tty()):
            try:
                tty_fd = os.open("/dev/tty", os.O_RDWR)
                os.dup2(tty_fd, 0)  # stdin
                os.dup2(tty_fd, 1)  # stdout
                os.dup2(tty_fd, 2)  # stderr
                os.close(tty_fd)
            except OSError:
                logger.debug(
                    "Unable to redirect stdin/stdout/stderr to /dev/tty; "
                    "falling back to inherited descriptors"
                )

        os.execvp("codex", cmd_args)
        # Never returns - process is replaced

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path | None,
        system_prompt: str | None,
        dangerous: bool,
    ) -> PromptResult:
        """Execute a single prompt and return the result.

        Implementation details:
        - Uses --output-last-message to write final message to a temp file
        - Prepends system_prompt to user prompt (Codex has no --system-prompt)
        - Ignores tools param (Codex has no --allowedTools, logged at DEBUG)
        - dangerous flag: mapped to permission mode, not separate flag
        """
        if tools is not None:
            logger.debug("tools parameter ignored for Codex (no --allowedTools equivalent)")

        # Determine permission mode: dangerous uses "dangerous", default "edits"
        pm: PermissionMode = "dangerous" if dangerous else "edits"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "output.txt"

            cmd_args = build_codex_prompt_args(
                prompt=prompt,
                cwd=cwd,
                permission_mode=pm,
                model=model,
                output_file=output_file,
                system_prompt=system_prompt,
            )

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                error_parts = [f"Exit code {result.returncode}"]
                if result.stderr and result.stderr.strip():
                    error_parts.append(f"stderr: {result.stderr.strip()}")
                return PromptResult(
                    success=False,
                    output="",
                    error=" | ".join(error_parts),
                )

            # Read output from the temp file
            if output_file.exists():
                output = output_file.read_text(encoding="utf-8").strip()
            else:
                output = ""

            return PromptResult(
                success=True,
                output=output,
                error=None,
            )

    def execute_prompt_passthrough(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
        dangerous: bool,
    ) -> int:
        """Execute prompt with output streaming directly to terminal.

        Implementation details:
        - Uses codex exec --json with output direct to terminal
        - Passes --cd for working directory
        - Ignores tools param (logged at DEBUG)
        - stdin=subprocess.DEVNULL to prevent interactive prompts
        """
        if tools is not None:
            logger.debug("tools parameter ignored for Codex (no --allowedTools equivalent)")

        pm: PermissionMode = "dangerous" if dangerous else "edits"

        cmd_args = build_codex_exec_args(
            prompt=prompt,
            worktree_path=cwd,
            permission_mode=pm,
            json_output=True,
            model=model,
        )

        result = subprocess.run(
            cmd_args,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode
