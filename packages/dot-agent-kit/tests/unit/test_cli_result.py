"""Tests for exit_with_error (exit with JSON output for kit CLI commands)."""

import json

import pytest

from dot_agent_kit.cli_result import exit_with_error


class TestExitWithError:
    """Tests for exit_with_error helper."""

    def test_exit_with_error_exits_with_code_zero(self) -> None:
        """exit_with_error exits with code 0 for graceful degradation."""
        with pytest.raises(SystemExit) as exc_info:
            exit_with_error("some_error", "Some message")

        assert exc_info.value.code == 0

    def test_exit_with_error_outputs_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """exit_with_error outputs properly formatted JSON."""
        with pytest.raises(SystemExit):
            exit_with_error("validation_failed", "Invalid input provided")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["success"] is False
        assert output["error_type"] == "validation_failed"
        assert output["message"] == "Invalid input provided"
