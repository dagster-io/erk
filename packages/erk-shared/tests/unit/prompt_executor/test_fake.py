"""Unit tests for FakePromptExecutor and retry configuration.

Tests:
- FakePromptExecutor transient_failures behavior (Layer 1: test infrastructure)
- RETRY_DELAYS constants validation

For RealPromptExecutor subprocess integration tests, see:
tests/integration/prompt_executor/test_real.py
"""

from erk_shared.prompt_executor.fake import FakePromptExecutor
from erk_shared.prompt_executor.real import RETRY_DELAYS


class TestRetryDelaysConstants:
    """Tests for retry delay configuration."""

    def test_retry_delays_has_two_entries(self) -> None:
        """Verify RETRY_DELAYS has exactly 2 entries for 2 retries."""
        assert len(RETRY_DELAYS) == 2

    def test_retry_delays_are_exponential_backoff(self) -> None:
        """Verify delays follow exponential backoff pattern."""
        assert RETRY_DELAYS[0] == 0.5
        assert RETRY_DELAYS[1] == 1.0
        # Each delay should be >= previous (exponential growth)
        for i in range(1, len(RETRY_DELAYS)):
            assert RETRY_DELAYS[i] >= RETRY_DELAYS[i - 1]

    def test_total_retry_time_is_reasonable(self) -> None:
        """Verify total maximum retry time is under 2 seconds."""
        total_time = sum(RETRY_DELAYS)
        assert total_time <= 2.0  # ~1.5s max with current delays


class TestFakePromptExecutorTransientFailures:
    """Tests for FakePromptExecutor transient_failures behavior.

    These tests verify the fake correctly simulates retry scenarios.
    Layer 1: Testing the test infrastructure itself.
    """

    def test_transient_failures_returns_empty_then_success(self) -> None:
        """With transient_failures=2, first 2 calls return empty, third returns output."""
        executor = FakePromptExecutor(output="Final output", transient_failures=2)

        # First call - empty (transient failure)
        result1 = executor.execute_prompt("test")
        assert result1.success is True
        assert result1.output == ""

        # Second call - empty (transient failure)
        result2 = executor.execute_prompt("test")
        assert result2.success is True
        assert result2.output == ""

        # Third call - actual output
        result3 = executor.execute_prompt("test")
        assert result3.success is True
        assert result3.output == "Final output"

        assert executor.attempt_count == 3

    def test_zero_transient_failures_returns_output_immediately(self) -> None:
        """With transient_failures=0, first call returns configured output."""
        executor = FakePromptExecutor(output="Immediate output", transient_failures=0)

        result = executor.execute_prompt("test")

        assert result.success is True
        assert result.output == "Immediate output"
        assert executor.attempt_count == 1

    def test_transient_failures_tracks_all_calls(self) -> None:
        """Verify prompt_calls tracks all attempts including transient failures."""
        executor = FakePromptExecutor(output="Success", transient_failures=1)

        executor.execute_prompt("prompt1", model="haiku")
        executor.execute_prompt("prompt2", model="sonnet")

        assert len(executor.prompt_calls) == 2
        assert executor.prompt_calls[0].prompt == "prompt1"
        assert executor.prompt_calls[0].model == "haiku"
        assert executor.prompt_calls[1].prompt == "prompt2"
        assert executor.prompt_calls[1].model == "sonnet"

    def test_should_fail_takes_precedence_over_transient_failures(self) -> None:
        """When should_fail=True, always return failure regardless of transient_failures."""
        executor = FakePromptExecutor(
            output="Never seen",
            should_fail=True,
            error="Always fails",
            transient_failures=5,
        )

        result = executor.execute_prompt("test")

        assert result.success is False
        assert result.error == "Always fails"
        assert result.output == ""
