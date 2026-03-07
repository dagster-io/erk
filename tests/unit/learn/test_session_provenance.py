"""Tests for shared session provenance functions."""

import json
from pathlib import Path

from erk_shared.learn.extraction.session_schema import (
    SessionProvenance,
    compute_session_provenance,
    has_user_text,
)

# ---------------------------------------------------------------------------
# has_user_text
# ---------------------------------------------------------------------------


def test_has_user_text_with_string() -> None:
    """Returns True for non-empty string content."""
    assert has_user_text("hello world") is True


def test_has_user_text_with_empty_string() -> None:
    """Returns False for empty or whitespace-only string."""
    assert has_user_text("") is False
    assert has_user_text("   ") is False


def test_has_user_text_with_list_containing_text_block() -> None:
    """Returns True for list with a non-empty text block."""
    content = [{"type": "text", "text": "hello"}]
    assert has_user_text(content) is True


def test_has_user_text_with_empty_text_block() -> None:
    """Returns False for list with only empty text blocks."""
    content = [{"type": "text", "text": ""}]
    assert has_user_text(content) is False


def test_has_user_text_with_non_text_blocks() -> None:
    """Returns False for list with no text blocks."""
    content = [{"type": "tool_result", "tool_use_id": "abc"}]
    assert has_user_text(content) is False


def test_has_user_text_with_empty_list() -> None:
    """Returns False for empty list."""
    assert has_user_text([]) is False


def test_has_user_text_with_non_string_non_list() -> None:
    """Returns False for unexpected types."""
    assert has_user_text(42) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_session_provenance
# ---------------------------------------------------------------------------


def _make_session_jsonl(*, user_turns: int, duration_seconds: int) -> str:
    """Build JSONL content with user turns and timestamps."""
    base_ts = 1700000000.0
    lines: list[str] = []
    ts = base_ts
    ts_step = duration_seconds / max(user_turns * 2 - 1, 1)
    for i in range(user_turns):
        lines.append(
            json.dumps(
                {
                    "type": "user",
                    "timestamp": ts,
                    "message": {"content": [{"type": "text", "text": f"User message {i + 1}"}]},
                }
            )
        )
        ts += ts_step
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "timestamp": ts,
                    "message": {"content": [{"type": "text", "text": f"Response {i + 1}"}]},
                }
            )
        )
        ts += ts_step
    return "\n".join(lines) + "\n"


def test_compute_session_provenance_missing_file(tmp_path: Path) -> None:
    """Returns None when session file does not exist."""
    result = compute_session_provenance(tmp_path / "nonexistent.jsonl")
    assert result is None


def test_compute_session_provenance_correct_stats(tmp_path: Path) -> None:
    """Computes correct user_turns, duration_minutes, and raw_size_kb."""
    content = _make_session_jsonl(user_turns=5, duration_seconds=600)
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(content, encoding="utf-8")

    result = compute_session_provenance(session_file)

    assert result is not None
    assert isinstance(result, SessionProvenance)
    assert result.user_turns == 5
    assert result.duration_minutes == 10
    assert result.raw_size_kb == session_file.stat().st_size // 1024


def test_compute_session_provenance_single_entry(tmp_path: Path) -> None:
    """Duration is None when only one timestamp exists."""
    content = json.dumps(
        {
            "type": "user",
            "timestamp": 1700000000.0,
            "message": {"content": [{"type": "text", "text": "hello"}]},
        }
    )
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(content + "\n", encoding="utf-8")

    result = compute_session_provenance(session_file)

    assert result is not None
    assert result.user_turns == 1
    assert result.duration_minutes is None
