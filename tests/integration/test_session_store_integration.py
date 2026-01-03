"""Integration tests for ClaudeCodeSessionStore with real JSONL fixtures.

Layer 5: Integration tests using realistic persisted .jsonl files.
Tests the RealClaudeInstallation against fixture files that represent
actual Claude Code session log structure.

Fixture layout:
  tests/integration/fixtures/session_logs/
    project_alpha/     <- contents of a single ~/.claude/projects/<encoded-path>/ folder
      session-aaa....jsonl
    project_beta/
      session-bbb....jsonl
      session-ccc....jsonl
    ...

Each fixture folder represents what would exist inside ONE project directory.
"""

import shutil
from pathlib import Path

import pytest

from erk_shared.extraction.claude_installation.real import (
    RealClaudeInstallation,
)

# Path to fixture session logs
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "session_logs"


@pytest.fixture
def mock_claude_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up mock home directory and patch Path.home().

    Returns:
        Path to tmp_path (mock home directory)
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def install_fixture(mock_home: Path, fixture_name: str, project_path: str) -> Path:
    """Install a fixture as a Claude project.

    Args:
        mock_home: Mock home directory (tmp_path)
        fixture_name: Name of fixture folder (e.g., "project_epsilon")
        project_path: Logical project path (e.g., "/test/myproject")

    Returns:
        Path to the installed project directory
    """
    # Encode path the way Claude Code does: /foo/bar -> -foo-bar
    encoded = project_path.replace("/", "-").replace(".", "-")

    projects_dir = mock_home / ".claude" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    src = FIXTURES_DIR / fixture_name
    dst = projects_dir / encoded
    shutil.copytree(src, dst)
    return dst


class TestFindSessionsSingleProject:
    """Tests for find_sessions with single project scenarios."""

    def test_finds_single_session_in_project(self, mock_claude_home: Path) -> None:
        """Test finding a single session in project_alpha."""
        install_fixture(mock_claude_home, "project_alpha", "/test/alpha")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/alpha"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=False,
        )

        assert len(sessions) == 1
        assert sessions[0].session_id == "session-aaa11111-2222-3333-4444-555555555555"
        assert sessions[0].parent_session_id is None

    def test_finds_multiple_sessions_in_project(self, mock_claude_home: Path) -> None:
        """Test finding multiple sessions in project_beta."""
        install_fixture(mock_claude_home, "project_beta", "/test/beta")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/beta"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=False,
        )

        session_ids = [s.session_id for s in sessions]
        assert "session-bbb11111-2222-3333-4444-555555555555" in session_ids
        assert "session-ccc11111-2222-3333-4444-555555555555" in session_ids
        assert len(sessions) == 2


class TestFindSessionsAgentFiltering:
    """Tests for agent file filtering in find_sessions."""

    def test_excludes_agents_by_default(self, mock_claude_home: Path) -> None:
        """Test that agent sessions are excluded by default."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=False,
        )

        session_ids = [s.session_id for s in sessions]

        # Main session should be present
        assert "session-fff11111-2222-3333-4444-555555555555" in session_ids

        # Agent files should NOT be present
        assert "agent-12345678" not in session_ids
        assert "agent-warmup01" not in session_ids

    def test_includes_agents_when_flag_set(self, mock_claude_home: Path) -> None:
        """Test that agent sessions are included when include_agents=True."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=True,
        )

        session_ids = [s.session_id for s in sessions]

        # Main session should be present
        assert "session-fff11111-2222-3333-4444-555555555555" in session_ids

        # Agent files should also be present
        assert "agent-12345678" in session_ids
        assert "agent-warmup01" in session_ids

    def test_agent_sessions_have_parent_session_id(self, mock_claude_home: Path) -> None:
        """Test that agent sessions have parent_session_id extracted from JSONL."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=True,
        )

        # Find agent sessions
        agent_sessions = {s.session_id: s for s in sessions if s.session_id.startswith("agent-")}

        # Both agents should have parent_session_id pointing to main session
        assert (
            agent_sessions["agent-12345678"].parent_session_id
            == "fff11111-2222-3333-4444-555555555555"
        )
        assert (
            agent_sessions["agent-warmup01"].parent_session_id
            == "fff11111-2222-3333-4444-555555555555"
        )

    def test_main_sessions_have_no_parent_session_id(self, mock_claude_home: Path) -> None:
        """Test that main sessions have parent_session_id=None."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=True,
        )

        main_session = next(
            s for s in sessions if s.session_id == "session-fff11111-2222-3333-4444-555555555555"
        )

        assert main_session.parent_session_id is None


class TestFindSessionsLimitAndSize:
    """Tests for limit and min_size filtering."""

    def test_respects_limit_parameter(self, mock_claude_home: Path) -> None:
        """Test that limit parameter restricts number of results."""
        install_fixture(mock_claude_home, "project_beta", "/test/beta")

        store = RealClaudeInstallation()

        sessions_limited = store.find_sessions(
            Path("/test/beta"),
            current_session_id=None,
            min_size=0,
            limit=1,
            include_agents=False,
        )
        sessions_unlimited = store.find_sessions(
            Path("/test/beta"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=False,
        )

        assert len(sessions_limited) == 1
        assert len(sessions_unlimited) == 2

    def test_respects_min_size_parameter(self, mock_claude_home: Path) -> None:
        """Test that min_size parameter filters small sessions."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()

        all_sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=True,
        )

        # Warmup agent is tiny, filter it out with min_size
        large_only = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=200,
            limit=100,
            include_agents=True,
        )

        assert len(large_only) < len(all_sessions)


class TestReadSessionContent:
    """Tests for read_session content retrieval."""

    def test_reads_main_session_content(self, mock_claude_home: Path) -> None:
        """Test reading main session JSONL content."""
        install_fixture(mock_claude_home, "project_alpha", "/test/alpha")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/alpha"),
            "session-aaa11111-2222-3333-4444-555555555555",
            include_agents=False,
        )

        assert content is not None
        assert "aaa11111-2222-3333-4444-555555555555" in content.main_content
        assert "alpha-feature-plan" in content.main_content

    def test_reads_session_with_multiple_slugs(self, mock_claude_home: Path) -> None:
        """Test reading session that has multiple plan slugs."""
        install_fixture(mock_claude_home, "project_gamma", "/test/gamma")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/gamma"),
            "session-ddd11111-2222-3333-4444-555555555555",
            include_agents=False,
        )

        assert content is not None
        assert "gamma-first" in content.main_content
        assert "gamma-second" in content.main_content

    def test_reads_session_without_slugs(self, mock_claude_home: Path) -> None:
        """Test reading session that has no plan mode (no slugs)."""
        install_fixture(mock_claude_home, "project_delta", "/test/delta")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/delta"),
            "session-eee11111-2222-3333-4444-555555555555",
            include_agents=False,
        )

        assert content is not None
        assert "slug" not in content.main_content

    def test_includes_agent_logs_when_requested(self, mock_claude_home: Path) -> None:
        """Test that agent logs are included when include_agents=True."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/epsilon"),
            "session-fff11111-2222-3333-4444-555555555555",
            include_agents=True,
        )

        assert content is not None
        assert len(content.agent_logs) >= 2

        agent_ids = [agent_id for agent_id, _ in content.agent_logs]
        assert "12345678" in agent_ids
        assert "warmup01" in agent_ids

    def test_excludes_agent_logs_when_not_requested(self, mock_claude_home: Path) -> None:
        """Test that agent logs are excluded when include_agents=False."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/epsilon"),
            "session-fff11111-2222-3333-4444-555555555555",
            include_agents=False,
        )

        assert content is not None
        assert len(content.agent_logs) == 0

    def test_returns_none_for_nonexistent_session(self, mock_claude_home: Path) -> None:
        """Test that nonexistent session returns None."""
        install_fixture(mock_claude_home, "project_alpha", "/test/alpha")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/alpha"),
            "nonexistent-session-id",
            include_agents=False,
        )

        assert content is None


class TestWarmupAgentCharacteristics:
    """Tests for warmup agent detection and characteristics."""

    def test_warmup_agent_has_small_file_size(self, mock_claude_home: Path) -> None:
        """Test that warmup agents have characteristically small file sizes."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=True,
        )

        warmup = next(
            (s for s in sessions if s.session_id == "agent-warmup01"),
            None,
        )

        assert warmup is not None
        assert warmup.size_bytes < 500

    def test_warmup_agent_content_contains_warmup_message(self, mock_claude_home: Path) -> None:
        """Test that warmup agent content contains 'Warmup' in first user message."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        content = store.read_session(
            Path("/test/epsilon"),
            "session-fff11111-2222-3333-4444-555555555555",
            include_agents=True,
        )

        assert content is not None

        warmup_content = next(
            (log_content for agent_id, log_content in content.agent_logs if agent_id == "warmup01"),
            None,
        )

        assert warmup_content is not None
        assert "Warmup" in warmup_content

    def test_real_agent_has_larger_file_size_than_warmup(self, mock_claude_home: Path) -> None:
        """Test that real work agents are larger than warmup agents."""
        install_fixture(mock_claude_home, "project_epsilon", "/test/epsilon")

        store = RealClaudeInstallation()
        sessions = store.find_sessions(
            Path("/test/epsilon"),
            current_session_id=None,
            min_size=0,
            limit=100,
            include_agents=True,
        )

        warmup = next(s for s in sessions if s.session_id == "agent-warmup01")
        real_agent = next(s for s in sessions if s.session_id == "agent-12345678")

        assert real_agent.size_bytes > warmup.size_bytes


class TestHasProject:
    """Tests for has_project method."""

    def test_returns_true_for_existing_project(self, mock_claude_home: Path) -> None:
        """Test that has_project returns True for existing project."""
        install_fixture(mock_claude_home, "project_alpha", "/test/alpha")

        store = RealClaudeInstallation()
        assert store.has_project(Path("/test/alpha")) is True

    def test_returns_false_for_nonexistent_project(self, mock_claude_home: Path) -> None:
        """Test that has_project returns False for nonexistent project."""
        store = RealClaudeInstallation()
        assert store.has_project(Path("/nonexistent/path")) is False

    def test_walks_up_directory_tree(self, mock_claude_home: Path) -> None:
        """Test that has_project walks up to find parent projects."""
        install_fixture(mock_claude_home, "project_alpha", "/test/alpha")

        store = RealClaudeInstallation()

        # /test/alpha/subdir should find /test/alpha project
        assert store.has_project(Path("/test/alpha/subdir/deep")) is True
