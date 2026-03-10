"""Tests for impl_run_parser — pure parsing of GitHub Actions log output."""

import json

from erk.core.impl_run_parser import (
    ImplRunSummary,
    ToolAction,
    extract_stream_json_lines,
    format_summary,
    parse_impl_run_summary,
)


def _make_gh_log_line(content: str) -> str:
    """Wrap content in a GitHub Actions timestamp prefix."""
    return f"2026-01-15T10:30:45.1234567Z {content}"


class TestExtractStreamJsonLines:
    def test_strips_timestamps_and_extracts_json(self) -> None:
        log = "\n".join(
            [
                _make_gh_log_line("##[group]Run implementation with claude"),
                _make_gh_log_line('{"type": "system", "subtype": "init"}'),
                _make_gh_log_line('{"type": "assistant", "content": []}'),
                _make_gh_log_line("##[endgroup]"),
            ]
        )
        result, used_group = extract_stream_json_lines(log)
        assert len(result) == 2
        assert '{"type": "system", "subtype": "init"}' in result
        assert '{"type": "assistant", "content": []}' in result
        assert used_group is True

    def test_finds_implementation_step_section(self) -> None:
        log = "\n".join(
            [
                _make_gh_log_line("##[group]Setup environment"),
                _make_gh_log_line('{"type": "setup", "step": 1}'),
                _make_gh_log_line("##[endgroup]"),
                _make_gh_log_line("##[group]Run implementation with plan-implement"),
                _make_gh_log_line('{"type": "system", "subtype": "init"}'),
                _make_gh_log_line("##[endgroup]"),
            ]
        )
        result, used_group = extract_stream_json_lines(log)
        assert len(result) == 1
        assert '"subtype": "init"' in result[0]
        assert used_group is True

    def test_skips_non_json_lines(self) -> None:
        log = "\n".join(
            [
                _make_gh_log_line("##[group]Run implementation with claude"),
                _make_gh_log_line("Setting up environment..."),
                _make_gh_log_line('{"type": "system"}'),
                _make_gh_log_line("Done."),
                _make_gh_log_line("##[endgroup]"),
            ]
        )
        result, used_group = extract_stream_json_lines(log)
        assert len(result) == 1
        assert '{"type": "system"}' in result
        assert used_group is True

    def test_fallback_when_no_group_markers(self) -> None:
        log = "\n".join(
            [
                _make_gh_log_line('{"type": "system", "subtype": "init"}'),
                _make_gh_log_line("Some text output"),
                _make_gh_log_line('{"type": "result", "exit_code": 0}'),
            ]
        )
        result, used_group = extract_stream_json_lines(log)
        assert len(result) == 2
        assert used_group is False

    def test_empty_log(self) -> None:
        result, used_group = extract_stream_json_lines("")
        assert result == []
        assert used_group is False

    def test_handles_lines_without_timestamps(self) -> None:
        log = "\n".join(
            [
                "##[group]Run implementation with claude",
                '{"type": "system"}',
                "##[endgroup]",
            ]
        )
        result, used_group = extract_stream_json_lines(log)
        assert len(result) == 1
        assert used_group is True


class TestParseImplRunSummary:
    def test_basic_session(self) -> None:
        lines = [
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "session_id": "sess-123",
                    "model": "claude-sonnet-4-20250514",
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "duration_ms": 120000,
                    "num_turns": 15,
                    "is_error": False,
                    "exit_code": 0,
                    "cost_usd": 1.50,
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert summary.session_id == "sess-123"
        assert summary.model == "claude-sonnet-4-20250514"
        assert summary.duration_ms == 120000
        assert summary.num_turns == 15
        assert summary.is_error is False
        assert summary.exit_code == 0
        assert summary.cost_usd == 1.50

    def test_with_tool_actions(self) -> None:
        lines = [
            json.dumps(
                {
                    "type": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/repo/src/foo.py"},
                        },
                    ],
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "/repo/src/bar.py"},
                        },
                    ],
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert len(summary.tool_actions) == 2
        assert summary.tool_actions[0].tool_name == "Read"
        assert summary.tool_actions[1].tool_name == "Edit"
        assert "/repo/src/foo.py" in summary.files_read
        assert "/repo/src/bar.py" in summary.files_modified

    def test_with_errors(self) -> None:
        lines = [
            json.dumps(
                {
                    "type": "tool_result",
                    "is_error": True,
                    "content": "Command failed: exit code 1",
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "is_error": True,
                    "exit_code": 1,
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert len(summary.error_messages) == 1
        assert "Command failed" in summary.error_messages[0]
        assert summary.is_error is True
        assert summary.exit_code == 1

    def test_assistant_text_extraction(self) -> None:
        lines = [
            json.dumps(
                {
                    "type": "assistant",
                    "content": [
                        {"type": "text", "text": "Setting up the implementation environment."},
                    ],
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert len(summary.assistant_messages) == 1
        assert "Setting up" in summary.assistant_messages[0]

    def test_assistant_text_truncation(self) -> None:
        long_text = "A" * 300
        lines = [
            json.dumps(
                {
                    "type": "assistant",
                    "content": [{"type": "text", "text": long_text}],
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert len(summary.assistant_messages) == 1
        assert len(summary.assistant_messages[0]) == 203  # 200 + "..."
        assert summary.assistant_messages[0].endswith("...")

    def test_empty_lines(self) -> None:
        summary = parse_impl_run_summary([])
        assert summary.session_id is None
        assert summary.tool_actions == []

    def test_malformed_json_lines_skipped(self) -> None:
        lines = [
            "not json",
            json.dumps({"type": "system", "subtype": "init", "session_id": "abc"}),
            "{broken",
        ]
        summary = parse_impl_run_summary(lines)
        assert summary.session_id == "abc"

    def test_deduplicates_file_reads(self) -> None:
        lines = [
            json.dumps(
                {
                    "type": "assistant",
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "/repo/a.py"}},
                    ],
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "/repo/a.py"}},
                    ],
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert len(summary.files_read) == 1

    def test_tool_result_error_with_list_content(self) -> None:
        lines = [
            json.dumps(
                {
                    "type": "tool_result",
                    "is_error": True,
                    "content": [{"type": "text", "text": "Permission denied"}],
                }
            ),
        ]
        summary = parse_impl_run_summary(lines)
        assert len(summary.error_messages) == 1
        assert "Permission denied" in summary.error_messages[0]


class TestFormatSummary:
    def test_basic_formatting(self) -> None:
        summary = ImplRunSummary(
            session_id="sess-abc",
            model="claude-sonnet-4-20250514",
            duration_ms=90000,
            num_turns=10,
            is_error=False,
            exit_code=0,
            cost_usd=0.75,
            tool_actions=[
                ToolAction(tool_name="Read", summary="Read src/foo.py"),
                ToolAction(tool_name="Edit", summary="Editing src/foo.py..."),
            ],
            error_messages=[],
            files_read=["src/foo.py"],
            files_modified=["src/foo.py"],
            assistant_messages=["Starting implementation."],
        )
        output = format_summary(summary)
        assert "sess-abc" in output
        assert "claude-sonnet-4-20250514" in output
        assert "1m 30s" in output
        assert "Turns: 10" in output
        assert "$0.75" in output
        assert "Exit Code: 0" in output
        assert "Read src/foo.py" in output
        assert "Files Read (1)" in output
        assert "Files Modified (1)" in output

    def test_error_formatting(self) -> None:
        summary = ImplRunSummary(
            session_id=None,
            model=None,
            duration_ms=None,
            num_turns=None,
            is_error=True,
            exit_code=1,
            cost_usd=None,
            tool_actions=[],
            error_messages=["Command failed: exit code 1"],
            files_read=[],
            files_modified=[],
            assistant_messages=[],
        )
        output = format_summary(summary)
        assert "Error: True" in output
        assert "Exit Code: 1" in output
        assert "Command failed" in output

    def test_empty_summary(self) -> None:
        summary = ImplRunSummary(
            session_id=None,
            model=None,
            duration_ms=None,
            num_turns=None,
            is_error=None,
            exit_code=None,
            cost_usd=None,
            tool_actions=[],
            error_messages=[],
            files_read=[],
            files_modified=[],
            assistant_messages=[],
        )
        output = format_summary(summary)
        assert "Implementation Run Summary" in output
