"""Codex implementation of ReviewExecutor.

This module provides the OpenAI Codex CLI implementation for code review execution.
"""

import shutil
import subprocess
from pathlib import Path

from erk_shared.review_executor.abc import ReviewExecutor


class RealCodexReviewExecutor(ReviewExecutor):
    """Production implementation using Codex CLI for code reviews.

    Uses the Codex CLI with full-auto mode for non-interactive execution,
    allowing output to stream directly to stdout/stderr.

    Example:
        >>> executor = RealCodexReviewExecutor()
        >>> if executor.is_available():
        ...     exit_code = executor.execute_review(
        ...         prompt="Review this code...",
        ...         model="gpt-5-codex",
        ...         tools=None,
        ...         cwd=repo_root,
        ...     )
    """

    def execute_review(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path,
    ) -> int:
        """Execute review using Codex CLI with passthrough output.

        Uses subprocess.run with stdin=subprocess.DEVNULL to prevent
        interactive prompts, while allowing stdout/stderr to pass through.

        Note: Codex CLI doesn't support tool restrictions, so the tools
        parameter is ignored.

        Args:
            prompt: The review prompt text
            model: Codex model to use (e.g., "gpt-5-codex")
            tools: Ignored - Codex doesn't support tool restrictions
            cwd: Working directory for execution

        Returns:
            Exit code from Codex CLI (0 for success)
        """
        # Note: tools parameter is ignored as Codex doesn't support tool restrictions
        cmd = ["codex", "exec", "--full-auto", prompt]
        if model:
            cmd.extend(["--model", model])

        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode

    def is_available(self) -> bool:
        """Check if Codex CLI is in PATH."""
        return shutil.which("codex") is not None
