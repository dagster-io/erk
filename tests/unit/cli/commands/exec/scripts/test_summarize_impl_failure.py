"""Tests for summarize-impl-failure exec command.

Tests the pure functions: _extract_session_tail, _build_failure_prompt,
_build_comment_body. The CLI command calls gh and Haiku via integrations,
so it is tested via CI integration rather than unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from erk.cli.commands.exec.scripts.summarize_impl_failure import (
    SessionTail,
    _build_comment_body,
    _build_failure_prompt,
    _extract_session_tail,
)


def _make_session_entry(entry_type: str, text: str) -> dict:
    """Create a minimal session JSONL entry."""
    if entry_type == "user":
        return {
            "type": "user",
            "message": {"content": [{"type": "text", "text": text}]},
        }
    if entry_type == "assistant":
        return {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": text}]},
        }
    if entry_type == "result":
        return {
            "type": "result",
            "message": {"content": text},
        }
    return {"type": entry_type, "message": {}}


class TestExtractSessionTail:
    """Tests for _extract_session_tail."""

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = _extract_session_tail(tmp_path / "missing.jsonl", max_entries=50)
        assert result is None

    def test_empty_file(self, tmp_path: Path) -> None:
        session_file = tmp_path / "empty.jsonl"
        session_file.write_text("", encoding="utf-8")
        result = _extract_session_tail(session_file, max_entries=50)
        assert result is None

    def test_whitespace_only_file(self, tmp_path: Path) -> None:
        session_file = tmp_path / "whitespace.jsonl"
        session_file.write_text("  \n  \n  ", encoding="utf-8")
        result = _extract_session_tail(session_file, max_entries=50)
        assert result is None

    def test_small_session(self, tmp_path: Path) -> None:
        entries = [
            _make_session_entry("user", "implement the feature"),
            _make_session_entry("assistant", "I'll start implementing"),
        ]
        session_file = tmp_path / "small.jsonl"
        session_file.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = _extract_session_tail(session_file, max_entries=50)

        assert result is not None
        assert result.total_events == 2
        assert result.has_result_event is False
        assert "<session>" in result.last_entries_xml
        assert "implement the feature" in result.last_entries_xml

    def test_large_session_truncated(self, tmp_path: Path) -> None:
        entries = [_make_session_entry("user", f"message {i}") for i in range(100)]
        session_file = tmp_path / "large.jsonl"
        session_file.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = _extract_session_tail(session_file, max_entries=10)

        assert result is not None
        assert result.total_events == 100
        # Should contain only the last 10 entries
        assert "message 90" in result.last_entries_xml
        assert "message 99" in result.last_entries_xml
        # Should not contain early entries
        assert "message 0" not in result.last_entries_xml

    def test_has_result_event(self, tmp_path: Path) -> None:
        entries = [
            _make_session_entry("user", "do something"),
            _make_session_entry("assistant", "done"),
            _make_session_entry("result", "success"),
        ]
        session_file = tmp_path / "with_result.jsonl"
        session_file.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = _extract_session_tail(session_file, max_entries=50)

        assert result is not None
        assert result.has_result_event is True

    def test_no_result_event(self, tmp_path: Path) -> None:
        entries = [
            _make_session_entry("user", "do something"),
            _make_session_entry("assistant", "working on it"),
        ]
        session_file = tmp_path / "no_result.jsonl"
        session_file.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = _extract_session_tail(session_file, max_entries=50)

        assert result is not None
        assert result.has_result_event is False

    def test_preserves_git_branch_metadata(self, tmp_path: Path) -> None:
        entries = [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "hello"}]},
                "gitBranch": "feature/my-branch",
            },
        ]
        session_file = tmp_path / "with_branch.jsonl"
        session_file.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = _extract_session_tail(session_file, max_entries=50)

        assert result is not None
        assert "feature/my-branch" in result.last_entries_xml


class TestBuildFailurePrompt:
    """Tests for _build_failure_prompt."""

    def test_with_template(self, tmp_path: Path) -> None:
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        template = prompts_dir / "impl-failure-summarize.md"
        template.write_text(
            "Exit: {{ EXIT_CODE }}\nTail: {{ SESSION_TAIL }}",
            encoding="utf-8",
        )

        tail = SessionTail(
            total_events=10,
            last_entries_xml="<session>...</session>",
            has_result_event=False,
        )
        result = _build_failure_prompt(
            session_tail=tail,
            exit_code=1,
            prompts_dir=tmp_path,
        )

        assert result == "Exit: 1\nTail: <session>...</session>"

    def test_with_template_unknown_exit_code(self, tmp_path: Path) -> None:
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        template = prompts_dir / "impl-failure-summarize.md"
        template.write_text(
            "Exit: {{ EXIT_CODE }}",
            encoding="utf-8",
        )

        tail = SessionTail(total_events=5, last_entries_xml="<session/>", has_result_event=False)
        result = _build_failure_prompt(
            session_tail=tail,
            exit_code=None,
            prompts_dir=tmp_path,
        )

        assert "unknown" in result

    def test_fallback_when_template_missing(self, tmp_path: Path) -> None:
        tail = SessionTail(
            total_events=5,
            last_entries_xml="<session>data</session>",
            has_result_event=False,
        )
        result = _build_failure_prompt(
            session_tail=tail,
            exit_code=1,
            prompts_dir=tmp_path,
        )

        assert "exit code 1" in result
        assert "<session>data</session>" in result


class TestBuildCommentBody:
    """Tests for _build_comment_body."""

    def test_basic_comment(self) -> None:
        result = _build_comment_body(
            summary="- Agent failed while editing foo.py",
            exit_code=1,
            total_events=42,
        )
        assert "## Implementation Failure Summary" in result
        assert "**Exit code:** 1" in result
        assert "**Session events:** 42" in result
        assert "- Agent failed while editing foo.py" in result

    def test_unknown_exit_code(self) -> None:
        result = _build_comment_body(
            summary="- Something went wrong",
            exit_code=None,
            total_events=10,
        )
        assert "**Exit code:** unknown" in result

    def test_zero_events(self) -> None:
        result = _build_comment_body(
            summary="Session file is empty",
            exit_code=1,
            total_events=0,
        )
        assert "**Session events:** 0" in result
