"""Tests for debug_impl_run exec script.

Tests the pure helper functions and CLI integration via CliRunner.
Uses FakeGitHubActions instead of @patch for dependency injection.
"""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.debug_impl_run import (
    _extract_run_id,
    _find_implement_job,
    debug_impl_run,
)
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_actions import FakeGitHubActions
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
    def test_finds_implement_job(self) -> None:
        jobs_output = "123456\tSetup\n789012\tImplement plan\n345678\tCleanup\n"
        result = _find_implement_job(jobs_output)
        assert result == "789012"

    def test_returns_none_when_no_implement_job(self) -> None:
        jobs_output = "123456\tSetup\n345678\tCleanup\n"
        result = _find_implement_job(jobs_output)
        assert result is None

    def test_returns_none_on_empty_output(self) -> None:
        result = _find_implement_job("")
        assert result is None

    def test_case_insensitive_matching(self) -> None:
        jobs_output = "999\tImplementation Runner\n"
        result = _find_implement_job(jobs_output)
        assert result == "999"


def _make_job_log_with_session() -> str:
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


def _make_full_job_log_with_turns() -> str:
    """Build a fake GH Actions log with full assistant messages and tool uses."""
    init_line = json.dumps(
        {
            "type": "system",
            "subtype": "init",
            "session_id": "sess-full-test-456",
            "model": "claude-opus-4-6",
        }
    )

    # Turn 1: Read a file
    assistant_turn_1 = json.dumps(
        {
            "type": "assistant",
            "content": [
                {"type": "text", "text": "I'll help you analyze the codebase."},
                {
                    "type": "tool_use",
                    "name": "Read",
                    "id": "read_1",
                    "input": {"file_path": "/repo/src/main.py"},
                },
            ],
        }
    )
    tool_result_1 = json.dumps(
        {
            "type": "tool_result",
            "tool_use_id": "read_1",
            "is_error": False,
            "content": "def main():\n    print('hello')",
        }
    )

    # Turn 2: Edit a file
    assistant_turn_2 = json.dumps(
        {
            "type": "assistant",
            "content": [
                {"type": "text", "text": "Now I'll make some improvements."},
                {
                    "type": "tool_use",
                    "name": "Edit",
                    "id": "edit_1",
                    "input": {
                        "file_path": "/repo/src/main.py",
                        "old_string": "print('hello')",
                        "new_string": "print('Hello, World!')",
                    },
                },
            ],
        }
    )
    tool_result_2 = json.dumps(
        {
            "type": "tool_result",
            "tool_use_id": "edit_1",
            "is_error": False,
            "content": "File updated.",
        }
    )

    # Turn 3: Error case
    assistant_turn_3 = json.dumps(
        {
            "type": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "id": "read_2",
                    "input": {"file_path": "/repo/nonexistent.py"},
                }
            ],
        }
    )
    tool_result_3 = json.dumps(
        {
            "type": "tool_result",
            "tool_use_id": "read_2",
            "is_error": True,
            "content": "File not found: /repo/nonexistent.py",
        }
    )

    result_line = json.dumps(
        {
            "type": "result",
            "duration_ms": 180000,
            "num_turns": 3,
            "is_error": False,
            "exit_code": 0,
            "cost_usd": 1.25,
        }
    )

    return "\n".join(
        [
            "2026-01-15T10:30:00.0000000Z ##[group]Run implementation",
            f"2026-01-15T10:30:01.0000000Z {init_line}",
            f"2026-01-15T10:30:02.0000000Z {assistant_turn_1}",
            f"2026-01-15T10:30:03.0000000Z {tool_result_1}",
            f"2026-01-15T10:30:04.0000000Z {assistant_turn_2}",
            f"2026-01-15T10:30:05.0000000Z {tool_result_2}",
            f"2026-01-15T10:30:06.0000000Z {assistant_turn_3}",
            f"2026-01-15T10:30:07.0000000Z {tool_result_3}",
            f"2026-01-15T10:30:08.0000000Z {result_line}",
            "2026-01-15T10:30:09.0000000Z ##[endgroup]",
        ]
    )


class TestDebugImplRunCli:
    def _make_context(
        self, *, run_jobs: dict[str, str], job_logs: dict[str, str | None]
    ) -> "context_for_test":
        """Create test context with FakeGitHubActions."""
        fake_actions = FakeGitHubActions(run_jobs=run_jobs, job_logs=job_logs)
        fake_github = FakeLocalGitHub(actions_gateway=fake_actions)
        return context_for_test(github=fake_github)

    def test_successful_run(self) -> None:
        runner = CliRunner()
        job_log = _make_job_log_with_session()
        ctx = self._make_context(
            run_jobs={"22902216182": "111\tImplement plan\n"},
            job_logs={"111": job_log},
        )

        result = runner.invoke(
            debug_impl_run,
            ["22902216182"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "sess-test-123" in result.output
        assert "claude-sonnet-4-20250514" in result.output

    def test_json_output(self) -> None:
        runner = CliRunner()
        job_log = _make_job_log_with_session()
        ctx = self._make_context(
            run_jobs={"22902216182": "111\tImplement plan\n"},
            job_logs={"111": job_log},
        )

        result = runner.invoke(
            debug_impl_run,
            ["22902216182", "--json"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = _parse_json_from_mixed_output(result.output)
        assert data["success"] is True
        assert data["session_id"] == "sess-test-123"
        assert data["cost_usd"] == 0.50

    def test_no_implement_job_error(self) -> None:
        runner = CliRunner()
        ctx = self._make_context(
            run_jobs={"12345": "111\tSetup\n222\tCleanup\n"},
            job_logs={},
        )

        result = runner.invoke(
            debug_impl_run,
            ["12345"],
            obj=ctx,
        )

        assert result.exit_code == 1
        data = _parse_json_from_mixed_output(result.output)
        assert data["error"] == "no_implement_job"

    def test_accepts_github_url(self) -> None:
        runner = CliRunner()
        job_log = _make_job_log_with_session()
        ctx = self._make_context(
            run_jobs={"22902216182": "111\tImplement plan\n"},
            job_logs={"111": job_log},
        )

        result = runner.invoke(
            debug_impl_run,
            ["https://github.com/dagster-io/erk/actions/runs/22902216182"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "sess-test-123" in result.output

    def test_parses_assistant_messages_and_tool_actions(self) -> None:
        """Test that full multi-turn sessions with tool uses are parsed correctly."""
        runner = CliRunner()
        job_log = _make_full_job_log_with_turns()
        ctx = self._make_context(
            run_jobs={"22902216182": "111\tImplement plan\n"},
            job_logs={"111": job_log},
        )

        result = runner.invoke(
            debug_impl_run,
            ["22902216182", "--json"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = _parse_json_from_mixed_output(result.output)
        assert data["success"] is True
        assert data["session_id"] == "sess-full-test-456"
        assert data["num_turns"] == 3
        assert data["is_error"] is False

        # Verify tool actions were extracted
        tool_actions = data.get("tool_actions", [])
        assert len(tool_actions) >= 3, f"Expected >= 3 tool actions, got {len(tool_actions)}"

        # Verify tool names
        tool_names = [action["tool_name"] for action in tool_actions]
        assert "Read" in tool_names
        assert "Edit" in tool_names

        # Verify files were tracked
        files_read = data.get("files_read", [])
        files_modified = data.get("files_modified", [])
        assert any("main.py" in f for f in files_read), (
            f"Expected main.py in files_read, got {files_read}"
        )
        assert any("main.py" in f for f in files_modified), (
            f"Expected main.py in files_modified, got {files_modified}"
        )

        # Verify error messages were captured
        error_messages = data.get("error_messages", [])
        assert len(error_messages) > 0, "Expected error messages from tool_result"
        assert any("nonexistent.py" in msg for msg in error_messages)

        # Verify assistant messages were stored
        assistant_messages = data.get("assistant_messages", [])
        assert len(assistant_messages) > 0, "Expected assistant messages"
