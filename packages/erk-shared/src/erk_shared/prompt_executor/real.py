"""Real implementation of PromptExecutor using Claude CLI."""

import subprocess
from pathlib import Path

from erk_shared.prompt_executor.abc import PromptExecutor, PromptResult


class RealPromptExecutor(PromptExecutor):
    """Production implementation using subprocess and Claude CLI."""

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str = "haiku",
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a single prompt via Claude CLI.

        Uses `claude --print` for single-shot prompt execution.

        Args:
            prompt: The prompt text to send to Claude
            model: Model to use (default "haiku" for speed/cost)
            cwd: Optional working directory for the command

        Returns:
            PromptResult with success status and output text
        """
        cmd = [
            "claude",
            "--print",
            "--model",
            model,
            "--dangerously-skip-permissions",
        ]

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

        if result.returncode != 0:
            return PromptResult(
                success=False,
                output="",
                error=result.stderr or "Claude CLI execution failed",
            )

        return PromptResult(
            success=True,
            output=result.stdout.strip(),
            error=None,
        )
