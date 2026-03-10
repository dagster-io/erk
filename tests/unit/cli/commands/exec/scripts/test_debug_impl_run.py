"""Tests for debug_impl_run exec script.

Tests the pure helper functions and CLI integration via CliRunner.
"""

import json
import subprocess
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.debug_impl_run import (
    _extract_run_id,
    _find_implement_job,
    debug_impl_run,
)
from tests.fakes.tests.shared_context import context_for_test


def _parse_json_from_mixed_output(output: str) -> dict:
    """Parse JSON from CliRunner output that may contain stderr messages.

    CliRunner in Click 8.3 mixes stdout and stderr in result.output.
    This finds the JSON object by locating the first line starting with
    ``{`` and parsing from there to the end.
    """
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("{"):
            # Try to parse from this line to the end
            candidate = "\n".join(lines[i:])
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in output: {output!r}")


class TestExtractRunId:
    def test_numeric_string(self) -> None:
        assert _extract_run_id("22902216182") == "22902216182"

    def test_github_actions_url(self) -> None:
        url = "https://github.com/dagster-io/erk/actions/runs/22902216182"
        assert _extract_run_id(url) == "22902216182"

    def test_github_actions_url_with_attempt(self) -> None:
        url = "https://github.com/dagster-io/erk/actions/runs/22902216182/attempts/1"
        assert _extract_run_id(url) == "22902216182"

    def test_whitespace_stripped(self) -> None:
        assert _extract_run_id("  12345  ") == "12345"

    def test_non_numeric_passthrough(self) -> None:
        assert _extract_run_id("abc") == "abc"


class TestFindImplementJob:
    def test_finds_implement_job(self, tmp_path) -> None:
        mock_stdout = "123456\tSetup\n789012\tImplement plan\n345678\tCleanup\n"
        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_stdout, stderr=""
            )
            result = _find_implement_job("12345", cwd=tmp_path)
        assert result == "789012"

    def test_returns_none_when_no_implement_job(self, tmp_path) -> None:
        mock_stdout = "123456\tSetup\n345678\tCleanup\n"
        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_stdout, stderr=""
            )
            result = _find_implement_job("12345", cwd=tmp_path)
        assert result is None

    def test_returns_none_on_api_failure(self, tmp_path) -> None:
        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="Not Found"
            )
            result = _find_implement_job("12345", cwd=tmp_path)
        assert result is None

    def test_case_insensitive_matching(self, tmp_path) -> None:
        mock_stdout = "999\tImplementation Runner\n"
        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_stdout, stderr=""
            )
            result = _find_implement_job("12345", cwd=tmp_path)
        assert result == "999"


class TestDebugImplRunCli:
    def _make_job_log_with_session(self) -> str:
        """Build a fake GH Actions log containing stream-json lines."""
        init_line = json.dumps(
            {
                "type": "system",
                "subtype": "init",
                "session_id": "sess-test-123",
                "model": "claude-sonnet-4-20250514",
            }
        )
        result_line = json.dumps(
            {
                "type": "result",
                "duration_ms": 60000,
                "num_turns": 5,
                "is_error": False,
                "exit_code": 0,
                "cost_usd": 0.50,
            }
        )
        return "\n".join(
            [
                "2026-01-15T10:30:00.0000000Z ##[group]Run implementation with claude",
                f"2026-01-15T10:30:01.0000000Z {init_line}",
                f"2026-01-15T10:30:02.0000000Z {result_line}",
                "2026-01-15T10:30:03.0000000Z ##[endgroup]",
            ]
        )

    def test_successful_run(self) -> None:
        runner = CliRunner()
        job_log = self._make_job_log_with_session()

        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            # First call: list jobs
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="111\tImplement plan\n",
                    stderr="",
                ),
                # Second call: fetch logs
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=job_log,
                    stderr="",
                ),
            ]
            result = runner.invoke(
                debug_impl_run,
                ["22902216182"],
                obj=context_for_test(),
            )

        assert result.exit_code == 0
        assert "sess-test-123" in result.output
        assert "claude-sonnet-4-20250514" in result.output

    def test_json_output(self) -> None:
        runner = CliRunner()
        job_log = self._make_job_log_with_session()

        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="111\tImplement plan\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=job_log,
                    stderr="",
                ),
            ]
            result = runner.invoke(
                debug_impl_run,
                ["22902216182", "--json"],
                obj=context_for_test(),
            )

        assert result.exit_code == 0
        data = _parse_json_from_mixed_output(result.output)
        assert data["success"] is True
        assert data["session_id"] == "sess-test-123"
        assert data["cost_usd"] == 0.50

    def test_no_implement_job_error(self) -> None:
        runner = CliRunner()

        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="111\tSetup\n222\tCleanup\n",
                stderr="",
            )
            result = runner.invoke(
                debug_impl_run,
                ["12345"],
                obj=context_for_test(),
            )

        assert result.exit_code == 1
        data = _parse_json_from_mixed_output(result.output)
        assert data["error"] == "no_implement_job"

    def test_accepts_github_url(self) -> None:
        runner = CliRunner()
        job_log = self._make_job_log_with_session()

        with patch(
            "erk.cli.commands.exec.scripts.debug_impl_run.run_subprocess_with_context"
        ) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="111\tImplement plan\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=job_log,
                    stderr="",
                ),
            ]
            result = runner.invoke(
                debug_impl_run,
                ["https://github.com/dagster-io/erk/actions/runs/22902216182"],
                obj=context_for_test(),
            )

        assert result.exit_code == 0
        assert "sess-test-123" in result.output
