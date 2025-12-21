"""Tests for the erk cc session xml command."""

import json
from pathlib import Path
from typing import Any

import pytest

from erk.cli.commands.cc.session.xml_cmd import (
    SessionIdResolutionError,
    _session_xml_impl,
    resolve_session_id,
)
from erk_shared.extraction.claude_code_session_store.abc import Session
from erk_shared.extraction.claude_code_session_store.fake import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)


def make_session(session_id: str, modified_at: float = 1000.0) -> Session:
    """Create a Session object for testing."""
    return Session(
        session_id=session_id,
        size_bytes=100,
        modified_at=modified_at,
        is_current=False,
    )


def make_session_content(user_message: str = "Hello") -> str:
    """Create minimal JSONL session content."""
    entry = {
        "type": "user",
        "message": {"content": user_message},
    }
    return json.dumps(entry)


class TestResolveSessionId:
    """Tests for session ID resolution logic."""

    def test_exact_match_full_guid(self) -> None:
        """Full GUID matches exactly."""
        sessions = [
            make_session("abc12345-1234-1234-1234-123456789012"),
            make_session("def67890-1234-1234-1234-123456789012"),
        ]

        result = resolve_session_id(sessions, "abc12345-1234-1234-1234-123456789012")

        assert result == "abc12345-1234-1234-1234-123456789012"

    def test_prefix_match_8_chars(self) -> None:
        """8-character prefix resolves correctly."""
        sessions = [
            make_session("abc12345-1234-1234-1234-123456789012"),
            make_session("def67890-1234-1234-1234-123456789012"),
        ]

        result = resolve_session_id(sessions, "abc12345")

        assert result == "abc12345-1234-1234-1234-123456789012"

    def test_prefix_match_shorter_prefix(self) -> None:
        """Prefix shorter than 8 chars still works if unique."""
        sessions = [
            make_session("abc12345-1234-1234-1234-123456789012"),
            make_session("def67890-1234-1234-1234-123456789012"),
        ]

        result = resolve_session_id(sessions, "abc")

        assert result == "abc12345-1234-1234-1234-123456789012"

    def test_no_match_raises_error(self) -> None:
        """No matching session raises error."""
        sessions = [
            make_session("abc12345-1234-1234-1234-123456789012"),
        ]

        with pytest.raises(SessionIdResolutionError) as exc_info:
            resolve_session_id(sessions, "xyz")

        assert "No session found" in str(exc_info.value)

    def test_multiple_matches_raises_error(self) -> None:
        """Multiple matching sessions raise error."""
        sessions = [
            make_session("abc12345-1234-1234-1234-123456789012"),
            make_session("abc12346-1234-1234-1234-123456789012"),
        ]

        with pytest.raises(SessionIdResolutionError) as exc_info:
            resolve_session_id(sessions, "abc1234")

        assert "Multiple sessions match" in str(exc_info.value)


class TestSessionXmlImpl:
    """Tests for the session XML implementation."""

    def test_full_session_id_outputs_xml(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[Any],
    ) -> None:
        """Full session ID produces XML output."""
        session_id = "abc12345-1234-1234-1234-123456789012"
        content = make_session_content("Test user message")

        store = FakeClaudeCodeSessionStore(
            projects={
                tmp_path: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=content,
                            size_bytes=len(content),
                            modified_at=1000.0,
                        )
                    }
                )
            }
        )

        _session_xml_impl(store, tmp_path, session_id)

        captured = capsys.readouterr()
        assert "<session>" in captured.out
        assert "Test user message" in captured.out
        assert "</session>" in captured.out

    def test_prefix_session_id_outputs_xml(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[Any],
    ) -> None:
        """8-char prefix produces XML output."""
        session_id = "abc12345-1234-1234-1234-123456789012"
        content = make_session_content("Prefix test")

        store = FakeClaudeCodeSessionStore(
            projects={
                tmp_path: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=content,
                            size_bytes=len(content),
                            modified_at=1000.0,
                        )
                    }
                )
            }
        )

        _session_xml_impl(store, tmp_path, "abc12345")

        captured = capsys.readouterr()
        assert "<session>" in captured.out
        assert "Prefix test" in captured.out

    def test_includes_agent_logs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[Any],
    ) -> None:
        """Agent logs are included in XML output."""
        session_id = "abc12345-1234-1234-1234-123456789012"
        main_content = make_session_content("Main session")
        agent_content = make_session_content("Agent message")

        store = FakeClaudeCodeSessionStore(
            projects={
                tmp_path: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=main_content,
                            size_bytes=len(main_content),
                            modified_at=1000.0,
                            agent_logs={"agent-001": agent_content},
                        )
                    }
                )
            }
        )

        _session_xml_impl(store, tmp_path, session_id)

        captured = capsys.readouterr()
        # Should have two <session> blocks (main + agent)
        assert captured.out.count("<session>") == 2
        assert "Main session" in captured.out
        assert "Agent message" in captured.out

    def test_no_project_exits_with_error(self, tmp_path: Path) -> None:
        """Missing project raises SystemExit."""
        store = FakeClaudeCodeSessionStore()

        with pytest.raises(SystemExit) as exc_info:
            _session_xml_impl(store, tmp_path, "abc12345")

        assert exc_info.value.code == 1

    def test_no_sessions_exits_with_error(self, tmp_path: Path) -> None:
        """Project with no sessions raises SystemExit."""
        store = FakeClaudeCodeSessionStore(projects={tmp_path: FakeProject(sessions={})})

        with pytest.raises(SystemExit) as exc_info:
            _session_xml_impl(store, tmp_path, "abc12345")

        assert exc_info.value.code == 1

    def test_invalid_session_id_exits_with_error(self, tmp_path: Path) -> None:
        """Non-matching session ID raises SystemExit."""
        session_id = "abc12345-1234-1234-1234-123456789012"
        content = make_session_content("Hello")

        store = FakeClaudeCodeSessionStore(
            projects={
                tmp_path: FakeProject(
                    sessions={
                        session_id: FakeSessionData(
                            content=content,
                            size_bytes=len(content),
                            modified_at=1000.0,
                        )
                    }
                )
            }
        )

        with pytest.raises(SystemExit) as exc_info:
            _session_xml_impl(store, tmp_path, "xyz99999")

        assert exc_info.value.code == 1
