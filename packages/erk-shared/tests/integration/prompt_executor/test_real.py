"""Integration tests for RealPromptExecutor retry behavior.

These tests use mocking to verify subprocess integration:
1. First attempt success returns immediately (no retry)
2. Empty output triggers retry with correct exponential backoff delays
3. All retries exhausted returns last result

Note: These are Layer 2 integration sanity tests that verify the Real
implementation correctly integrates with subprocess. They use mocking
because subprocess.run is an external boundary.
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


class TestRealPromptExecutorSubprocessIntegration:
    """Integration tests for RealPromptExecutor subprocess behavior."""

    def test_first_attempt_success_returns_immediately(self) -> None:
        """When first attempt succeeds with output, return immediately without retrying."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

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
            assert mock_run.call_count == 1
            assert fake_time.sleep_calls == []

    def test_empty_output_triggers_retry_with_correct_delays(self) -> None:
        """When output is empty, retry with exponential backoff until success."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        call_count = 0

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> FakeCompletedProcess:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return FakeCompletedProcess(returncode=0, stdout="", stderr="")
            return FakeCompletedProcess(returncode=0, stdout="Final success", stderr="")

        with patch(
            "erk_shared.prompt_executor.real.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is True
            assert result.output == "Final success"
            assert call_count == 3
            assert fake_time.sleep_calls == [RETRY_DELAYS[0], RETRY_DELAYS[1]]

    def test_all_retries_exhausted_returns_last_result(self) -> None:
        """When all retries exhausted, return last result (success with empty output)."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

        with patch("erk_shared.prompt_executor.real.subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is True
            assert result.output == ""
            assert result.error is None
            assert mock_run.call_count == len(RETRY_DELAYS) + 1
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
                return FakeCompletedProcess(returncode=1, stdout="", stderr="Error")
            return FakeCompletedProcess(returncode=0, stdout="Success", stderr="")

        with patch(
            "erk_shared.prompt_executor.real.subprocess.run",
            side_effect=mock_subprocess_run,
        ):
            result = executor.execute_prompt("test prompt", model="haiku")

            assert result.success is True
            assert result.output == "Success"
            assert call_count == 2
            assert fake_time.sleep_calls == [RETRY_DELAYS[0]]

    def test_all_attempts_fail_returns_last_failure(self) -> None:
        """When all attempts fail, return last failure result."""
        fake_time = FakeTime()
        executor = RealPromptExecutor(fake_time)

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
            assert "--model" in cmd
            model_index = cmd.index("--model")
            assert cmd[model_index + 1] == "opus"
