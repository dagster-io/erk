"""Integration tests for plan extraction from ~/.claude/plans/.

Layer 4: Business logic tests using realistic file fixtures.
Tests the workflow of reading the most recent plan file and session-scoped
plan extraction using realistic JSONL session logs.

Note: The plan-extractor agent (not this module) is responsible for
semantic validation that the plan matches conversation context.
"""

import shutil
import time
from pathlib import Path

import pytest

from erk_kits.data.kits.erk.session_plan_extractor import (
    extract_slugs_from_session,
    find_project_dir_for_session,
    get_latest_plan,
)
from tests.unit.kits.kits.erk.fixtures import (
    SAMPLE_PLAN_CONTENT,
)

# Path to fixture session logs
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "session_logs"

# ===============================================
# Helpers
# ===============================================


def create_plan_file(mock_home: Path, slug: str, content: str) -> Path:
    """Create a plan file in the mock Claude plans directory.

    Args:
        mock_home: Mock home directory path
        slug: Plan slug (filename without .md)
        content: Plan content to write

    Returns:
        Path to created plan file
    """
    plans_dir = mock_home / ".claude" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plans_dir / f"{slug}.md"
    plan_file.write_text(content, encoding="utf-8")
    return plan_file


# ===============================================
# Integration Tests
# ===============================================


def test_full_workflow_returns_most_recent_plan(tmp_path: Path, monkeypatch) -> None:
    """Test complete workflow: read most recently modified plan file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create older plan
    create_plan_file(tmp_path, "older-plan", "Old plan content")

    # Ensure time difference
    time.sleep(0.01)

    # Create newer plan
    create_plan_file(tmp_path, "newer-plan", SAMPLE_PLAN_CONTENT)

    # Should return newest plan
    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_empty_plans_directory_returns_none(tmp_path: Path, monkeypatch) -> None:
    """Test that empty plans directory returns None."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create empty plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_no_plans_directory_returns_none(tmp_path: Path, monkeypatch) -> None:
    """Test when plans directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create any directories
    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_single_plan_file(tmp_path: Path, monkeypatch) -> None:
    """Test with a single plan file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create single plan
    create_plan_file(tmp_path, "only-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_multiple_plans_returns_most_recent(tmp_path: Path, monkeypatch) -> None:
    """Test that most recently modified plan is returned among many."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create several plans with time gaps
    for i in range(5):
        create_plan_file(tmp_path, f"plan-{i}", f"Plan {i} content")
        time.sleep(0.01)

    # Create the expected newest plan
    create_plan_file(tmp_path, "newest-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_ignores_non_markdown_files(tmp_path: Path, monkeypatch) -> None:
    """Test that non-.md files are ignored."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create various non-.md files
    (plans_dir / "notes.txt").write_text("Not a plan", encoding="utf-8")
    (plans_dir / "backup.json").write_text("{}", encoding="utf-8")
    (plans_dir / "README").write_text("Read me", encoding="utf-8")

    time.sleep(0.01)

    # Create actual plan file
    create_plan_file(tmp_path, "real-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_ignores_subdirectories(tmp_path: Path, monkeypatch) -> None:
    """Test that subdirectories are ignored even if named .md."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a directory (not a file) with .md name
    fake_md_dir = plans_dir / "fake.md"
    fake_md_dir.mkdir()

    # Create actual plan file
    create_plan_file(tmp_path, "real-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_working_dir_parameter_ignored(tmp_path: Path, monkeypatch) -> None:
    """Test that working_dir parameter doesn't affect result."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    create_plan_file(tmp_path, "test-plan", SAMPLE_PLAN_CONTENT)

    # All different working dirs should return same result
    result1 = get_latest_plan("/path/one")
    result2 = get_latest_plan("/completely/different/path")
    result3 = get_latest_plan("/Users/someone/.erk/repos/project")

    assert result1 == SAMPLE_PLAN_CONTENT
    assert result2 == SAMPLE_PLAN_CONTENT
    assert result3 == SAMPLE_PLAN_CONTENT


def test_session_id_parameter_ignored(tmp_path: Path, monkeypatch) -> None:
    """Test that session_id parameter doesn't affect result."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    create_plan_file(tmp_path, "test-plan", SAMPLE_PLAN_CONTENT)

    # Different session IDs should return same result
    result1 = get_latest_plan("/path", session_id=None)
    result2 = get_latest_plan("/path", session_id="abc123")
    result3 = get_latest_plan("/path", session_id="different-session")

    assert result1 == SAMPLE_PLAN_CONTENT
    assert result2 == SAMPLE_PLAN_CONTENT
    assert result3 == SAMPLE_PLAN_CONTENT


def test_plan_with_unicode_content(tmp_path: Path, monkeypatch) -> None:
    """Test reading plan with unicode content."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    unicode_content = """# Plan with Unicode

- Emoji: 🚀 ✅ ❌
- Japanese: こんにちは
- Chinese: 你好
- Arabic: مرحبا
- Special: ñ ü ö ä
"""
    create_plan_file(tmp_path, "unicode-plan", unicode_content)

    result = get_latest_plan("/any/path")

    assert result == unicode_content


def test_plan_selection_by_mtime_not_name(tmp_path: Path, monkeypatch) -> None:
    """Test that selection is by modification time, not alphabetical order."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans with names that would sort differently than mtime
    create_plan_file(tmp_path, "zzz-oldest", "Oldest plan")
    time.sleep(0.01)
    create_plan_file(tmp_path, "aaa-newest", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/path")

    # Should return "aaa-newest" because it's most recent, not "zzz-oldest"
    assert result == SAMPLE_PLAN_CONTENT


# ===============================================
# Session-Scoped Plan Extraction Integration Tests
# Using realistic JSONL fixtures from fixtures/session_logs/
# ===============================================


@pytest.fixture
def mock_claude_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up mock ~/.claude/projects/ with fixture session logs.

    Copies fixture directories to tmp_path/.claude/projects/ and
    patches Path.home() to return tmp_path.

    Returns:
        Path to tmp_path (mock home directory)
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create .claude/projects directory
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Copy fixture directories to mock projects
    for fixture_project in FIXTURES_DIR.iterdir():
        if fixture_project.is_dir() and fixture_project.name != "__pycache__":
            dest = projects_dir / fixture_project.name
            shutil.copytree(fixture_project, dest)

    return tmp_path


class TestFindProjectDirForSession:
    """Integration tests for find_project_dir_for_session with real fixtures."""

    def test_finds_project_for_session_in_single_file(self, mock_claude_projects: Path) -> None:
        """Test finding project when session is in a single file."""
        session_id = "aaa11111-2222-3333-4444-555555555555"

        result = find_project_dir_for_session(session_id)

        assert result is not None
        assert result.name == "project_alpha"

    def test_finds_correct_project_among_multiple(self, mock_claude_projects: Path) -> None:
        """Test finding correct project when multiple projects exist."""
        # Session bbb is in project_beta
        result = find_project_dir_for_session("bbb11111-2222-3333-4444-555555555555")
        assert result is not None
        assert result.name == "project_beta"

        # Session ccc is also in project_beta (different session file)
        result = find_project_dir_for_session("ccc11111-2222-3333-4444-555555555555")
        assert result is not None
        assert result.name == "project_beta"

        # Session ddd is in project_gamma
        result = find_project_dir_for_session("ddd11111-2222-3333-4444-555555555555")
        assert result is not None
        assert result.name == "project_gamma"

    def test_returns_none_for_nonexistent_session(self, mock_claude_projects: Path) -> None:
        """Test returns None when session ID doesn't exist anywhere."""
        result = find_project_dir_for_session("nonexistent-session-id")
        assert result is None

    def test_cwd_hint_accelerates_lookup(self, mock_claude_projects: Path) -> None:
        """Test that cwd_hint provides faster lookup when correct."""
        session_id = "aaa11111-2222-3333-4444-555555555555"

        # With correct hint - should find it
        result = find_project_dir_for_session(session_id, cwd_hint="/projects/alpha")
        assert result is not None
        assert result.name == "project_alpha"

    def test_cwd_hint_falls_back_when_wrong(self, mock_claude_projects: Path) -> None:
        """Test fallback to full scan when cwd_hint doesn't match."""
        session_id = "aaa11111-2222-3333-4444-555555555555"

        # With wrong hint - should still find via fallback
        result = find_project_dir_for_session(session_id, cwd_hint="/wrong/path")
        assert result is not None
        assert result.name == "project_alpha"


class TestExtractSlugsFromSession:
    """Integration tests for extract_slugs_from_session with real fixtures."""

    def test_extracts_single_slug(self, mock_claude_projects: Path) -> None:
        """Test extracting single slug from session."""
        session_id = "aaa11111-2222-3333-4444-555555555555"

        slugs = extract_slugs_from_session(session_id)

        assert slugs == ["alpha-feature-plan"]

    def test_extracts_multiple_slugs_in_order(self, mock_claude_projects: Path) -> None:
        """Test extracting multiple slugs preserves order."""
        session_id = "ddd11111-2222-3333-4444-555555555555"

        slugs = extract_slugs_from_session(session_id)

        # Should be in occurrence order
        assert slugs == ["gamma-first", "gamma-second"]

    def test_returns_empty_for_session_without_slugs(self, mock_claude_projects: Path) -> None:
        """Test returns empty list when session has no plan mode entries."""
        session_id = "eee11111-2222-3333-4444-555555555555"

        slugs = extract_slugs_from_session(session_id)

        assert slugs == []

    def test_ignores_agent_files(self, mock_claude_projects: Path) -> None:
        """Test that agent-*.jsonl files are ignored."""
        session_id = "fff11111-2222-3333-4444-555555555555"

        slugs = extract_slugs_from_session(session_id)

        # Should only find slug from main session, not from agent file
        assert slugs == ["epsilon-main-plan"]
        assert "agent-should-be-ignored" not in slugs

    def test_different_sessions_return_different_slugs(self, mock_claude_projects: Path) -> None:
        """Test that different sessions in same project return their own slugs."""
        # Session bbb has beta-plan-one
        slugs_bbb = extract_slugs_from_session("bbb11111-2222-3333-4444-555555555555")
        assert slugs_bbb == ["beta-plan-one"]

        # Session ccc has beta-plan-two
        slugs_ccc = extract_slugs_from_session("ccc11111-2222-3333-4444-555555555555")
        assert slugs_ccc == ["beta-plan-two"]

    def test_cwd_hint_used_for_faster_lookup(self, mock_claude_projects: Path) -> None:
        """Test that cwd_hint is passed through for performance."""
        session_id = "aaa11111-2222-3333-4444-555555555555"

        # With hint
        slugs = extract_slugs_from_session(session_id, cwd_hint="/projects/alpha")

        assert slugs == ["alpha-feature-plan"]


class TestGetLatestPlanWithSessionId:
    """Integration tests for get_latest_plan with session_id parameter."""

    def test_session_scoped_lookup_finds_correct_plan(self, mock_claude_projects: Path) -> None:
        """Test that session_id finds plan via slug, not mtime."""
        # Create plans directory with multiple plans
        plans_dir = mock_claude_projects / ".claude" / "plans"
        plans_dir.mkdir(parents=True)

        # Create plan matching alpha session's slug
        alpha_plan = plans_dir / "alpha-feature-plan.md"
        alpha_plan.write_text("# Alpha Plan\nAlpha content", encoding="utf-8")

        # Create a newer plan (by mtime)
        time.sleep(0.01)
        newer_plan = plans_dir / "newer-plan.md"
        newer_plan.write_text("# Newer Plan\nNewer content", encoding="utf-8")

        # Session-scoped lookup should return alpha plan, not newer
        result = get_latest_plan("/any", session_id="aaa11111-2222-3333-4444-555555555555")

        assert result == "# Alpha Plan\nAlpha content"

    def test_session_with_multiple_slugs_uses_most_recent(self, mock_claude_projects: Path) -> None:
        """Test that most recent slug is used when session has multiple."""
        plans_dir = mock_claude_projects / ".claude" / "plans"
        plans_dir.mkdir(parents=True)

        # Create both plans for gamma session
        (plans_dir / "gamma-first.md").write_text("# First Plan", encoding="utf-8")
        (plans_dir / "gamma-second.md").write_text("# Second Plan", encoding="utf-8")

        # Should return second (most recent slug)
        result = get_latest_plan("/any", session_id="ddd11111-2222-3333-4444-555555555555")

        assert result == "# Second Plan"

    def test_falls_back_to_mtime_when_no_slug(self, mock_claude_projects: Path) -> None:
        """Test fallback to mtime when session has no slug."""
        plans_dir = mock_claude_projects / ".claude" / "plans"
        plans_dir.mkdir(parents=True)

        # Create a plan (session eee has no slugs)
        only_plan = plans_dir / "fallback-plan.md"
        only_plan.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

        # Should fall back to mtime selection
        result = get_latest_plan("/any", session_id="eee11111-2222-3333-4444-555555555555")

        assert result == SAMPLE_PLAN_CONTENT

    def test_falls_back_when_slug_plan_file_missing(self, mock_claude_projects: Path) -> None:
        """Test fallback when slug exists but plan file doesn't."""
        plans_dir = mock_claude_projects / ".claude" / "plans"
        plans_dir.mkdir(parents=True)

        # Create a different plan (not matching alpha's slug)
        fallback = plans_dir / "different-plan.md"
        fallback.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

        # alpha-feature-plan.md doesn't exist, should fall back
        result = get_latest_plan("/any", session_id="aaa11111-2222-3333-4444-555555555555")

        assert result == SAMPLE_PLAN_CONTENT
