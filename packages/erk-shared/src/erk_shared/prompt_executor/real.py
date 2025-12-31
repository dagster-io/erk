"""Real implementation of PromptExecutor using Claude CLI."""

import subprocess
from pathlib import Path

from erk_shared.gateway.time.abc import Time
from erk_shared.prompt_executor.abc import PromptExecutor, PromptResult

# Retry delays following exponential backoff pattern: [0.5, 1.0] (~1.5s max, 2 retries)
RETRY_DELAYS = [0.5, 1.0]


class RealPromptExecutor(PromptExecutor):
    """Production implementation using subprocess and Claude CLI."""

    def __init__(self, time: Time) -> None:
        """Initialize with time dependency for testable delays.

        Args:
            time: Time abstraction for sleep operations (enables fast tests)
        """
        self._time = time

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str = "haiku",
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a single prompt via Claude CLI with retry on empty output.

        Uses `claude --print` for single-shot prompt execution.
        Retries with exponential backoff when result.success=True but output is empty,
        which can happen due to transient LLM API issues.

        Args:
            prompt: The prompt text to send to Claude
            model: Model to use (default "haiku" for speed/cost)
            cwd: Optional working directory for the command

        Returns:
            PromptResult with success status and output text
        """
        last_result: PromptResult | None = None

        for attempt in range(len(RETRY_DELAYS) + 1):
            result = self._execute_once(prompt, model=model, cwd=cwd)

            # Success with non-empty output - done
            if result.success and result.output:
                return result

            last_result = result

            # Retry if attempts remaining
            if attempt < len(RETRY_DELAYS):
                self._time.sleep(RETRY_DELAYS[attempt])

        # Return last result (may be success with empty output, or failure)
        # last_result is always set because the loop runs at least once
        assert last_result is not None
        return last_result

    def _execute_once(
        self,
        prompt: str,
        *,
        model: str,
        cwd: Path | None,
    ) -> PromptResult:
        """Execute a single prompt attempt via Claude CLI.

        Args:
            prompt: The prompt text to send to Claude
            model: Model to use
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
