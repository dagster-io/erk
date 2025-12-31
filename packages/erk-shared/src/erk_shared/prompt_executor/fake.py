"""Fake implementation of PromptExecutor for testing."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.prompt_executor.abc import PromptExecutor, PromptResult


@dataclass(frozen=True)
class PromptCall:
    """Record of a prompt execution call."""

    prompt: str
    model: str
    cwd: Path | None


class FakePromptExecutor(PromptExecutor):
    """In-memory fake implementation of PromptExecutor for testing.

    Constructor injection pattern: all behavior is configured via constructor
    parameters. No magic, no post-construction setup methods.

    Attributes:
        prompt_calls: Read-only list of all prompt calls made (for assertions)

    Example:
        >>> executor = FakePromptExecutor(output='["1. First step", "2. Second step"]')
        >>> result = executor.execute_prompt("Extract steps", model="haiku")
        >>> assert result.success
        >>> assert result.output == '["1. First step", "2. Second step"]'
        >>> assert len(executor.prompt_calls) == 1

    Transient failures example (simulates retry behavior):
        >>> executor = FakePromptExecutor(output="Success!", transient_failures=2)
        >>> # First two calls return success with empty output (triggers retry)
        >>> result1 = executor.execute_prompt("test")
        >>> assert result1.success and result1.output == ""
        >>> result2 = executor.execute_prompt("test")
        >>> assert result2.success and result2.output == ""
        >>> # Third call returns actual output
        >>> result3 = executor.execute_prompt("test")
        >>> assert result3.success and result3.output == "Success!"
    """

    def __init__(
        self,
        *,
        output: str = "[]",
        error: str | None = None,
        should_fail: bool = False,
        transient_failures: int = 0,
    ) -> None:
        """Create FakePromptExecutor with pre-configured behavior.

        Args:
            output: Output to return on successful calls. Defaults to empty JSON
                    array for compatibility with step extraction prompts.
            error: Error message to return on failure (requires should_fail=True)
            should_fail: If True, execute_prompt returns failure
            transient_failures: Number of empty responses to return before success.
                    Simulates transient LLM API issues where success=True but
                    output is empty. After transient_failures calls, returns
                    the configured output.
        """
        self._output = output
        self._error = error
        self._should_fail = should_fail
        self._transient_failures = transient_failures
        self._attempt_count = 0
        self._prompt_calls: list[PromptCall] = []

    @property
    def prompt_calls(self) -> list[PromptCall]:
        """Read-only access to recorded prompt calls."""
        return self._prompt_calls

    @property
    def attempt_count(self) -> int:
        """Read-only access to attempt count (for test assertions)."""
        return self._attempt_count

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str = "haiku",
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a prompt and return configured result.

        Records the call for later assertion.

        Args:
            prompt: The prompt text
            model: Model to use
            cwd: Working directory

        Returns:
            PromptResult based on configured behavior
        """
        self._prompt_calls.append(PromptCall(prompt=prompt, model=model, cwd=cwd))
        self._attempt_count += 1

        if self._should_fail:
            return PromptResult(
                success=False,
                output="",
                error=self._error or "Simulated failure",
            )

        # Simulate transient failures (success with empty output)
        if self._attempt_count <= self._transient_failures:
            return PromptResult(
                success=True,
                output="",
                error=None,
            )

        return PromptResult(
            success=True,
            output=self._output,
            error=None,
        )
