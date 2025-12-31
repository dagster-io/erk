"""Tests for RealPromptExecutor retry behavior.

These tests verify:
1. First attempt success returns immediately (no retry)
2. Empty output triggers retry with correct exponential backoff delays
3. All retries exhausted returns last result
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

from erk_shared.gateway.time.fake import FakeTime
from erk_shared.prompt_executor.real import RETRY_DELAYS, RealPromptExecutor


@dataclass(frozen=True)
class FakeCompletedProcess:
    """Fake subprocess.CompletedProcess for testing."""

    returncode: int
    stdout: str
    stderr: str


class TestRealPromptExecutorRetry:
    """Tests for retry behavior in RealPromptExecutor."""

    def test_first_attempt_success_returns_immediately(self) -> None:
        """When first attempt succeeds with output, return immediately without retrying."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        # Mock subprocess.run to return success with output on first call
        with patch("erk_shared.prompt_executor.real.subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="Success output",
                stderr="",
            )

            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is True
            assert result.output == "Success output"
            assert result.error is None
            # Should only call subprocess.run once
            assert mock_run.call_count == 1
            # Should not have slept (no retries needed)
            assert fake_time.sleep_calls == []

    def test_empty_output_triggers_retry_with_correct_delays(self) -> None:
        """When output is empty, retry with exponential backoff until success."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        # Track call count to return empty on first 2 calls, then success
        call_count = 0

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> FakeCompletedProcess:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Return success with empty output (transient failure)
                return FakeCompletedProcess(returncode=0, stdout="", stderr="")
            # Third call succeeds with actual output
            return FakeCompletedProcess(returncode=0, stdout="Final success", stderr="")

        with patch(
            "erk_shared.prompt_executor.real.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is True
            assert result.output == "Final success"
            # Should have retried twice before success
            assert call_count == 3
            # Should have slept with first two retry delays
            assert fake_time.sleep_calls == [RETRY_DELAYS[0], RETRY_DELAYS[1]]

    def test_all_retries_exhausted_returns_last_result(self) -> None:
        """When all retries exhausted, return last result (success with empty output)."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        # Always return empty output
        with patch("erk_shared.prompt_executor.real.subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = executor.execute_prompt("test prompt", model="haiku")

            # Returns success=True but empty output after all retries exhausted
            assert result.success is True
            assert result.output == ""
            assert result.error is None
            # Should have tried 1 + 4 retries = 5 total attempts
            assert mock_run.call_count == len(RETRY_DELAYS) + 1
            # Should have slept for all retry delays
            assert fake_time.sleep_calls == list(RETRY_DELAYS)

    def test_failure_on_first_attempt_retries(self) -> None:
        """When first attempt fails (non-zero returncode), retry."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        call_count = 0

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> FakeCompletedProcess:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                return FakeCompletedProcess(returncode=1, stdout="", stderr="Error")
            # Second call succeeds
            return FakeCompletedProcess(returncode=0, stdout="Success", stderr="")

        with patch(
            "erk_shared.prompt_executor.real.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is True
            assert result.output == "Success"
            assert call_count == 2
            # Should have slept once for the retry
            assert fake_time.sleep_calls == [RETRY_DELAYS[0]]

    def test_all_attempts_fail_returns_last_failure(self) -> None:
        """When all attempts fail, return last failure result."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        # Always fail
        with patch("erk_shared.prompt_executor.real.subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=1,
                stdout="",
                stderr="Persistent error",
            )

            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is False
            assert result.output == ""
            assert result.error == "Persistent error"
            # Should have exhausted all retries
            assert mock_run.call_count == len(RETRY_DELAYS) + 1
            assert fake_time.sleep_calls == list(RETRY_DELAYS)

    def test_cwd_parameter_passed_to_subprocess(self) -> None:
        """Verify cwd parameter is passed through to subprocess.run."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        with patch("erk_shared.prompt_executor.real.subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="Output",
                stderr="",
            )
            test_cwd = Path("/test/path")

            executor.execute_prompt("test prompt", model="sonnet", cwd=test_cwd)

            # Verify cwd was passed to subprocess.run
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs["cwd"] == test_cwd

    def test_model_parameter_in_command(self) -> None:
        """Verify model parameter is included in the claude command."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        with patch("erk_shared.prompt_executor.real.subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="Output",
                stderr="",
            )

            executor.execute_prompt("test prompt", model="opus")

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            # Verify --model opus is in the command
            assert "--model" in cmd
            model_index = cmd.index("--model")
            assert cmd[model_index + 1] == "opus"
