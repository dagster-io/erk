"""Unit tests for ClaudeCodeSessionStore implementations."""

from pathlib import Path

from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
    Session,
    SessionContent,
)


class TestFakeClaudeCodeSessionStore:
    """Tests for FakeClaudeCodeSessionStore - Layer 1: Fake Infrastructure Tests."""

    def test_has_project_returns_true_for_existing_project(self) -> None:
        """Test has_project returns True for configured project."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={project_path: FakeProject()},
        )
        assert store.has_project(project_path) is True

    def test_has_project_returns_false_for_missing_project(self) -> None:
        """Test has_project returns False for unconfigured project."""
        store = FakeClaudeCodeSessionStore()
        assert store.has_project(Path("/nonexistent")) is False

    def test_has_project_finds_parent_project(self) -> None:
        """Walk-up finds project in parent directory."""
        parent = Path("/code/repo")
        child = Path("/code/repo/packages/foo")

        store = FakeClaudeCodeSessionStore(projects={parent: FakeProject(sessions={})})

        assert store.has_project(parent) is True
        assert store.has_project(child) is True  # Finds parent

    def test_has_project_returns_false_when_no_ancestor_project(self) -> None:
        """Returns False when no project at or above path."""
        store = FakeClaudeCodeSessionStore(projects={Path("/other/repo"): FakeProject(sessions={})})

        assert store.has_project(Path("/code/repo")) is False

    def test_find_sessions_returns_empty_for_missing_project(self) -> None:
        """Test find_sessions returns empty list for unconfigured project."""
        store = FakeClaudeCodeSessionStore()
        sessions = store.find_sessions(Path("/nonexistent"))
        assert sessions == []

    def test_find_sessions_from_subdirectory(self) -> None:
        """Sessions found when querying from subdirectory."""
        parent = Path("/code/repo")
        child = Path("/code/repo/src/lib")

        store = FakeClaudeCodeSessionStore(
            projects={
                parent: FakeProject(
                    sessions={
                        "abc123": FakeSessionData(content="...", size_bytes=100, modified_at=1000.0)
                    }
                )
            }
        )

        sessions = store.find_sessions(child)
        assert len(sessions) == 1
        assert sessions[0].session_id == "abc123"

    def test_find_sessions_returns_sessions_sorted_by_modified_at(self) -> None:
        """Test sessions are sorted newest first."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "session-1": FakeSessionData(
                            content="older",
                            size_bytes=100,
                            modified_at=1000.0,
                        ),
                        "session-2": FakeSessionData(
                            content="newer",
                            size_bytes=200,
                            modified_at=2000.0,
                        ),
                    }
                )
            },
        )

        sessions = store.find_sessions(project_path, current_session_id="session-2")

        assert len(sessions) == 2
        assert sessions[0].session_id == "session-2"  # Newer first
        assert sessions[1].session_id == "session-1"
        assert sessions[0].is_current is True
        assert sessions[1].is_current is False

    def test_find_sessions_filters_by_min_size(self) -> None:
        """Test min_size filter excludes small sessions."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "small": FakeSessionData(
                            content="x",
                            size_bytes=50,
                            modified_at=1000.0,
                        ),
                        "large": FakeSessionData(
                            content="x" * 200,
                            size_bytes=200,
                            modified_at=2000.0,
                        ),
                    }
                )
            },
        )

        sessions = store.find_sessions(project_path, min_size=100)

        assert len(sessions) == 1
        assert sessions[0].session_id == "large"

    def test_find_sessions_respects_limit(self) -> None:
        """Test limit parameter caps number of sessions returned."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        f"session-{i}": FakeSessionData(
                            content="x",
                            size_bytes=100,
                            modified_at=float(i),
                        )
                        for i in range(10)
                    }
                )
            },
        )

        sessions = store.find_sessions(project_path, limit=3)

        assert len(sessions) == 3
        # Should be the 3 newest (highest modified_at)
        assert sessions[0].session_id == "session-9"
        assert sessions[1].session_id == "session-8"
        assert sessions[2].session_id == "session-7"

    def test_find_sessions_marks_current_session(self) -> None:
        """Test is_current is set correctly based on current_session_id."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "current-one": FakeSessionData(
                            content="x",
                            size_bytes=100,
                            modified_at=2000.0,
                        ),
                        "other-one": FakeSessionData(
                            content="x",
                            size_bytes=100,
                            modified_at=1000.0,
                        ),
                    }
                )
            },
        )

        sessions = store.find_sessions(project_path, current_session_id="current-one")

        current_sessions = [s for s in sessions if s.is_current]
        assert len(current_sessions) == 1
        assert current_sessions[0].session_id == "current-one"

    def test_read_session_returns_none_for_missing_project(self) -> None:
        """Test read_session returns None for unconfigured project."""
        store = FakeClaudeCodeSessionStore()
        result = store.read_session(Path("/nonexistent"), "any-id")
        assert result is None

    def test_read_session_from_subdirectory(self) -> None:
        """Session read when querying from subdirectory."""
        parent = Path("/code/repo")
        child = Path("/code/repo/src/lib")
        main_content = '{"type": "user", "message": "Hello"}\n'

        store = FakeClaudeCodeSessionStore(
            projects={
                parent: FakeProject(
                    sessions={
                        "test-session": FakeSessionData(
                            content=main_content,
                            size_bytes=100,
                            modified_at=1000.0,
                        )
                    }
                )
            }
        )

        result = store.read_session(child, "test-session")
        assert result is not None
        assert result.main_content == main_content

    def test_read_session_returns_none_for_missing_session(self) -> None:
        """Test read_session returns None for unconfigured session."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={project_path: FakeProject()},
        )
        result = store.read_session(project_path, "nonexistent-id")
        assert result is None

    def test_read_session_returns_content_without_agents(self) -> None:
        """Test read_session returns main content."""
        project_path = Path("/my/project")
        main_content = '{"type": "user", "message": "Hello"}\n'
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "test-session": FakeSessionData(
                            content=main_content,
                            size_bytes=100,
                            modified_at=1000.0,
                        ),
                    }
                )
            },
        )

        result = store.read_session(project_path, "test-session")

        assert result is not None
        assert isinstance(result, SessionContent)
        assert result.main_content == main_content
        assert result.agent_logs == []

    def test_read_session_includes_agent_logs(self) -> None:
        """Test read_session includes agent logs when requested."""
        project_path = Path("/my/project")
        main_content = '{"type": "user", "message": "Hello"}\n'
        agent_content = '{"type": "agent", "message": "Working"}\n'
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "test-session": FakeSessionData(
                            content=main_content,
                            size_bytes=100,
                            modified_at=1000.0,
                            agent_logs={"agent-abc": agent_content},
                        ),
                    }
                )
            },
        )

        result = store.read_session(project_path, "test-session", include_agents=True)

        assert result is not None
        assert len(result.agent_logs) == 1
        assert result.agent_logs[0] == ("agent-abc", agent_content)

    def test_read_session_excludes_agent_logs_when_disabled(self) -> None:
        """Test read_session excludes agent logs when include_agents=False."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "test-session": FakeSessionData(
                            content="main",
                            size_bytes=100,
                            modified_at=1000.0,
                            agent_logs={"agent-abc": "agent content"},
                        ),
                    }
                )
            },
        )

        result = store.read_session(project_path, "test-session", include_agents=False)

        assert result is not None
        assert result.agent_logs == []

    def test_read_session_sorts_agent_logs_by_id(self) -> None:
        """Test agent logs are returned in sorted order."""
        project_path = Path("/my/project")
        store = FakeClaudeCodeSessionStore(
            projects={
                project_path: FakeProject(
                    sessions={
                        "test-session": FakeSessionData(
                            content="main",
                            size_bytes=100,
                            modified_at=1000.0,
                            agent_logs={
                                "agent-zzz": "last",
                                "agent-aaa": "first",
                                "agent-mmm": "middle",
                            },
                        ),
                    }
                )
            },
        )

        result = store.read_session(project_path, "test-session")

        assert result is not None
        assert len(result.agent_logs) == 3
        assert result.agent_logs[0][0] == "agent-aaa"
        assert result.agent_logs[1][0] == "agent-mmm"
        assert result.agent_logs[2][0] == "agent-zzz"


class TestFakeClaudeCodeSessionStorePlans:
    """Tests for get_latest_plan in FakeClaudeCodeSessionStore.

    Layer 1: Fake Infrastructure Tests.
    """

    def test_get_latest_plan_returns_plan_content(self) -> None:
        """Test get_latest_plan returns plan content when plans are configured."""
        plan_content = "# My Feature\n\n- Step 1\n- Step 2"
        store = FakeClaudeCodeSessionStore(
            plans={"my-feature": plan_content},
        )
        result = store.get_latest_plan(Path("/my/project"))
        assert result == plan_content

    def test_get_latest_plan_returns_none_when_empty(self) -> None:
        """Test get_latest_plan returns None when no plans configured."""
        store = FakeClaudeCodeSessionStore()
        result = store.get_latest_plan(Path("/my/project"))
        assert result is None

    def test_get_latest_plan_with_session_id_match(self) -> None:
        """Test get_latest_plan returns matching plan when session_id matches key."""
        plan_a = "# Plan A"
        plan_b = "# Plan B"
        store = FakeClaudeCodeSessionStore(
            plans={
                "session-a": plan_a,
                "session-b": plan_b,
            },
        )

        # Session ID matches a plan key
        result = store.get_latest_plan(Path("/my/project"), session_id="session-b")
        assert result == plan_b

    def test_get_latest_plan_fallback_to_first(self) -> None:
        """Test get_latest_plan falls back to first plan when session_id doesn't match."""
        plan_a = "# Plan A"
        plan_b = "# Plan B"
        store = FakeClaudeCodeSessionStore(
            plans={
                "slug-a": plan_a,
                "slug-b": plan_b,
            },
        )

        # Session ID doesn't match any plan key - falls back to first
        result = store.get_latest_plan(Path("/my/project"), session_id="unknown-session")
        # First plan in dict iteration order
        assert result == plan_a

    def test_get_latest_plan_no_session_id_returns_first(self) -> None:
        """Test get_latest_plan returns first plan when no session_id provided."""
        plan_a = "# Plan A"
        plan_b = "# Plan B"
        store = FakeClaudeCodeSessionStore(
            plans={
                "slug-a": plan_a,
                "slug-b": plan_b,
            },
        )

        result = store.get_latest_plan(Path("/my/project"))
        assert result == plan_a

    def test_get_latest_plan_ignores_project_cwd(self) -> None:
        """Test get_latest_plan returns same plan regardless of project_cwd."""
        plan_content = "# My Feature"
        store = FakeClaudeCodeSessionStore(
            plans={"my-feature": plan_content},
        )

        # Same result for different project paths
        result1 = store.get_latest_plan(Path("/project/a"))
        result2 = store.get_latest_plan(Path("/project/b"))
        assert result1 == result2 == plan_content


class TestSessionDomainTypes:
    """Tests for Session and SessionContent domain types."""

    def test_session_is_frozen(self) -> None:
        """Test Session is immutable."""
        session = Session(
            session_id="test",
            size_bytes=100,
            modified_at=1000.0,
            is_current=False,
        )
        # Should raise FrozenInstanceError
        try:
            session.session_id = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected - dataclass is frozen

    def test_session_content_is_frozen(self) -> None:
        """Test SessionContent is immutable."""
        content = SessionContent(
            main_content="test",
            agent_logs=[],
        )
        try:
            content.main_content = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected - dataclass is frozen
