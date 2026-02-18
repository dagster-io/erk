"""Tests for Codex JSONL output parser."""

from __future__ import annotations

import json
from pathlib import Path

from erk.core.codex_output_parser import CodexParserState, parse_codex_jsonl_line
from erk_shared.core.prompt_executor import (
    ErrorEvent,
    IssueNumberEvent,
    PrNumberEvent,
    PrUrlEvent,
    SpinnerUpdateEvent,
    TextEvent,
    ToolEvent,
)

WORKTREE = Path("/test/repo")


def _parse(data: dict) -> list:
    """Helper: parse a dict as JSONL and return events with fresh state."""
    state = CodexParserState()
    return parse_codex_jsonl_line(json.dumps(data), WORKTREE, state)


class TestThreadStarted:
    """thread.started captures thread_id in state, emits no events."""

    def test_captures_thread_id(self) -> None:
        state = CodexParserState()
        events = parse_codex_jsonl_line(
            json.dumps({"type": "thread.started", "thread_id": "abc-123"}),
            WORKTREE,
            state,
        )
        assert events == []
        assert state.thread_id == "abc-123"

    def test_ignores_missing_thread_id(self) -> None:
        state = CodexParserState()
        events = parse_codex_jsonl_line(
            json.dumps({"type": "thread.started"}),
            WORKTREE,
            state,
        )
        assert events == []
        assert state.thread_id is None


class TestItemStarted:
    """item.started events emit SpinnerUpdateEvent and set saw_any_items."""

    def test_command_execution_emits_spinner(self) -> None:
        events = _parse(
            {
                "type": "item.started",
                "item": {
                    "id": "item_0",
                    "type": "command_execution",
                    "command": "bash -lc 'echo hello'",
                    "status": "in_progress",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], SpinnerUpdateEvent)
        assert "echo hello" in events[0].status

    def test_mcp_tool_call_emits_spinner(self) -> None:
        events = _parse(
            {
                "type": "item.started",
                "item": {
                    "id": "item_1",
                    "type": "mcp_tool_call",
                    "server": "myserver",
                    "tool": "read_file",
                    "status": "in_progress",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], SpinnerUpdateEvent)
        assert "myserver/read_file" in events[0].status

    def test_sets_saw_any_items(self) -> None:
        state = CodexParserState()
        parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.started",
                    "item": {"id": "item_0", "type": "command_execution", "command": "ls"},
                }
            ),
            WORKTREE,
            state,
        )
        assert state.saw_any_items is True

    def test_web_search_emits_spinner(self) -> None:
        events = _parse(
            {
                "type": "item.started",
                "item": {
                    "id": "item_2",
                    "type": "web_search",
                    "query": "python asyncio tutorial",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], SpinnerUpdateEvent)
        assert "Searching:" in events[0].status
        assert "python asyncio tutorial" in events[0].status

    def test_unknown_item_type_returns_empty(self) -> None:
        events = _parse(
            {
                "type": "item.started",
                "item": {"id": "item_0", "type": "unknown_future_type"},
            }
        )
        assert events == []


class TestItemCompletedAgentMessage:
    """item.completed + agent_message emits TextEvent."""

    def test_emits_text_event(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "agent_message",
                    "text": "I've completed the task.",
                },
            }
        )
        assert len(events) >= 1
        assert isinstance(events[0], TextEvent)
        assert events[0].content == "I've completed the task."

    def test_sets_saw_any_text(self) -> None:
        state = CodexParserState()
        parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"id": "item_0", "type": "agent_message", "text": "Hello"},
                }
            ),
            WORKTREE,
            state,
        )
        assert state.saw_any_text is True

    def test_empty_text_returns_empty(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {"id": "item_0", "type": "agent_message", "text": ""},
            }
        )
        assert events == []

    def test_extracts_pr_metadata_from_text(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "agent_message",
                    "text": "Created PR #42: Fix bug\nhttps://github.com/o/r/pull/42",
                },
            }
        )
        # TextEvent + PrUrlEvent + PrNumberEvent + PrTitleEvent
        assert any(isinstance(e, TextEvent) for e in events)
        assert any(
            isinstance(e, PrUrlEvent) and e.url == "https://github.com/o/r/pull/42" for e in events
        )
        assert any(isinstance(e, PrNumberEvent) and e.number == 42 for e in events)

    def test_extracts_issue_number_from_text(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "agent_message",
                    "text": "Linked to issue #123",
                },
            }
        )
        assert any(isinstance(e, TextEvent) for e in events)
        assert any(isinstance(e, IssueNumberEvent) and e.number == 123 for e in events)


class TestItemCompletedCommandExecution:
    """item.completed + command_execution emits ToolEvent."""

    def test_successful_command(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "command_execution",
                    "command": "bash -lc 'echo hi'",
                    "aggregated_output": "hi\n",
                    "exit_code": 0,
                    "status": "completed",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "echo hi" in events[0].summary
        assert "hi" in events[0].summary

    def test_failed_command_shows_exit_code(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "command_execution",
                    "command": "false",
                    "aggregated_output": "",
                    "exit_code": 1,
                    "status": "completed",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "Exit code: 1" in events[0].summary


class TestItemCompletedFileChange:
    """item.completed + file_change emits ToolEvent."""

    def test_file_change_summary(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "file_change",
                    "changes": [
                        {"path": "src/main.py", "kind": "update"},
                        {"path": "tests/test_main.py", "kind": "add"},
                    ],
                    "status": "completed",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "update: src/main.py" in events[0].summary
        assert "add: tests/test_main.py" in events[0].summary

    def test_empty_changes_returns_generic(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "file_change",
                    "changes": [],
                    "status": "completed",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "File changes applied" in events[0].summary


class TestItemCompletedMcpToolCall:
    """item.completed + mcp_tool_call emits ToolEvent."""

    def test_successful_mcp_call(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "mcp_tool_call",
                    "server": "fs",
                    "tool": "read_file",
                    "status": "completed",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "fs/read_file" in events[0].summary

    def test_mcp_call_with_error(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "mcp_tool_call",
                    "server": "fs",
                    "tool": "read_file",
                    "error": "File not found",
                    "status": "failed",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "error" in events[0].summary
        assert "File not found" in events[0].summary


class TestItemCompletedError:
    """item.completed + error item type emits ErrorEvent."""

    def test_error_item(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "error",
                    "message": "Something went wrong",
                },
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert events[0].message == "Something went wrong"


class TestTurnFailed:
    """turn.failed emits ErrorEvent."""

    def test_turn_failed_with_message(self) -> None:
        events = _parse(
            {
                "type": "turn.failed",
                "error": {"message": "Rate limit exceeded"},
            }
        )
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert events[0].message == "Rate limit exceeded"

    def test_turn_failed_without_message(self) -> None:
        events = _parse({"type": "turn.failed", "error": {}})
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert "Turn failed" in events[0].message


class TestTopLevelError:
    """Top-level error events emit ErrorEvent."""

    def test_error_event(self) -> None:
        events = _parse({"type": "error", "message": "Connection lost"})
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert events[0].message == "Connection lost"

    def test_error_without_message(self) -> None:
        events = _parse({"type": "error"})
        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert "Unknown error" in events[0].message


class TestTurnCompleted:
    """turn.completed logs token usage but emits no events."""

    def test_turn_completed_emits_no_events(self) -> None:
        events = _parse(
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 200},
            }
        )
        assert events == []

    def test_turn_completed_without_usage(self) -> None:
        events = _parse({"type": "turn.completed"})
        assert events == []


class TestIgnoredEvents:
    """Events that should produce no output."""

    def test_turn_started_ignored(self) -> None:
        assert _parse({"type": "turn.started"}) == []

    def test_item_updated_ignored(self) -> None:
        events = _parse(
            {
                "type": "item.updated",
                "item": {"id": "item_0", "type": "command_execution"},
            }
        )
        assert events == []

    def test_reasoning_item_ignored(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {"id": "item_0", "type": "reasoning", "text": "Thinking..."},
            }
        )
        assert events == []

    def test_todo_list_item_ignored(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "todo_list",
                    "items": [{"text": "Step 1", "completed": False}],
                },
            }
        )
        assert events == []

    def test_collab_tool_call_item_ignored(self) -> None:
        events = _parse(
            {
                "type": "item.completed",
                "item": {"id": "item_0", "type": "collab_tool_call", "tool": "spawn_agent"},
            }
        )
        assert events == []


class TestMalformedInput:
    """Malformed input returns empty list."""

    def test_empty_line(self) -> None:
        state = CodexParserState()
        assert parse_codex_jsonl_line("", WORKTREE, state) == []

    def test_whitespace_only(self) -> None:
        state = CodexParserState()
        assert parse_codex_jsonl_line("   \n  ", WORKTREE, state) == []

    def test_invalid_json(self) -> None:
        state = CodexParserState()
        assert parse_codex_jsonl_line("{not valid json}", WORKTREE, state) == []

    def test_json_array_instead_of_object(self) -> None:
        state = CodexParserState()
        assert parse_codex_jsonl_line("[1, 2, 3]", WORKTREE, state) == []

    def test_missing_type_field(self) -> None:
        state = CodexParserState()
        assert parse_codex_jsonl_line('{"data": "hello"}', WORKTREE, state) == []

    def test_missing_item_field(self) -> None:
        state = CodexParserState()
        events = parse_codex_jsonl_line(
            json.dumps({"type": "item.completed"}),
            WORKTREE,
            state,
        )
        assert events == []


class TestStateMutation:
    """Tests that parser state is correctly mutated across calls."""

    def test_thread_id_persists_across_calls(self) -> None:
        state = CodexParserState()
        parse_codex_jsonl_line(
            json.dumps({"type": "thread.started", "thread_id": "my-thread"}),
            WORKTREE,
            state,
        )
        # Subsequent calls see the thread_id
        assert state.thread_id == "my-thread"

        # Another event doesn't clear thread_id
        parse_codex_jsonl_line(
            json.dumps({"type": "turn.started"}),
            WORKTREE,
            state,
        )
        assert state.thread_id == "my-thread"

    def test_saw_any_items_tracks_items(self) -> None:
        state = CodexParserState()
        assert state.saw_any_items is False

        parse_codex_jsonl_line(
            json.dumps({"type": "turn.started"}),
            WORKTREE,
            state,
        )
        assert state.saw_any_items is False

        parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.started",
                    "item": {"id": "item_0", "type": "command_execution", "command": "ls"},
                }
            ),
            WORKTREE,
            state,
        )
        assert state.saw_any_items is True

    def test_saw_any_text_tracks_agent_messages(self) -> None:
        state = CodexParserState()
        assert state.saw_any_text is False

        # command_execution doesn't set saw_any_text
        parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "id": "item_0",
                        "type": "command_execution",
                        "command": "ls",
                        "aggregated_output": "file.py",
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
            WORKTREE,
            state,
        )
        assert state.saw_any_text is False

        # agent_message sets saw_any_text
        parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"id": "item_1", "type": "agent_message", "text": "Done!"},
                }
            ),
            WORKTREE,
            state,
        )
        assert state.saw_any_text is True

    def test_command_captured_from_item_started_used_in_completed(self) -> None:
        """item.started captures command, item.completed uses it if missing."""
        state = CodexParserState()

        # item.started with command
        parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.started",
                    "item": {
                        "id": "item_0",
                        "type": "command_execution",
                        "command": "echo captured",
                    },
                }
            ),
            WORKTREE,
            state,
        )

        # item.completed without command — should fall back to captured
        events = parse_codex_jsonl_line(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "id": "item_0",
                        "type": "command_execution",
                        "command": "",
                        "aggregated_output": "captured\n",
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
            WORKTREE,
            state,
        )
        assert len(events) == 1
        assert isinstance(events[0], ToolEvent)
        assert "echo captured" in events[0].summary
