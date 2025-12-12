"""Unit tests for session plan extraction functions.

Layer 3: Pure unit tests for isolated functions in session_plan_extractor.py
"""

import time
from pathlib import Path

import pytest

from erk_kits.data.kits.erk.session_plan_extractor import (
    extract_slugs_from_session,
    find_project_dir_for_session,
    get_latest_plan,
    get_plans_dir,
)
from tests.unit.kits.kits.erk.fixtures import (
    SAMPLE_PLAN_CONTENT,
    create_session_entry,
    create_session_file,
)

# ===============================================
# Tests for get_plans_dir()
# ===============================================


def test_get_plans_dir_returns_path() -> None:
    """Test that get_plans_dir returns a Path object."""
    result = get_plans_dir()
    assert isinstance(result, Path)


def test_get_plans_dir_has_correct_structure() -> None:
    """Test that get_plans_dir returns correct path structure."""
    result = get_plans_dir()
    assert result.parts[-2:] == (".claude", "plans")


def test_get_plans_dir_starts_with_home() -> None:
    """Test that plans dir starts with home directory."""
    result = get_plans_dir()
    assert str(result).startswith(str(Path.home()))


# ===============================================
# Tests for get_latest_plan()
# ===============================================


def test_get_latest_plan_returns_most_recent(monkeypatch, tmp_path: Path) -> None:
    """Test returns content of most recently modified plan file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create older plan
    older_plan = plans_dir / "older-plan.md"
    older_plan.write_text("# Older Plan\nOld content", encoding="utf-8")

    # Ensure time difference
    time.sleep(0.01)

    # Create newer plan
    newer_plan = plans_dir / "newer-plan.md"
    newer_plan.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_nonexistent_plans_dir(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when plans directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create plans directory
    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_get_latest_plan_empty_plans_dir(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when plans directory is empty."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create empty plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_get_latest_plan_single_plan(monkeypatch, tmp_path: Path) -> None:
    """Test returns content when only one plan exists."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory and single plan
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "only-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_ignores_non_md_files(monkeypatch, tmp_path: Path) -> None:
    """Test ignores non-.md files in plans directory."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create non-.md file (should be ignored)
    non_md = plans_dir / "notes.txt"
    non_md.write_text("This is not a plan", encoding="utf-8")

    # Ensure time difference
    time.sleep(0.01)

    # Create .md plan file
    plan_file = plans_dir / "real-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_ignores_directories(monkeypatch, tmp_path: Path) -> None:
    """Test ignores subdirectories in plans directory."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a subdirectory (should be ignored)
    subdir = plans_dir / "archive"
    subdir.mkdir()

    # Create plan file
    plan_file = plans_dir / "current-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_working_dir_unused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that working_dir parameter doesn't affect result."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory and plan
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "test-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    # Different working_dir should return same result
    result1 = get_latest_plan("/path/one")
    result2 = get_latest_plan("/path/two")

    assert result1 == SAMPLE_PLAN_CONTENT
    assert result2 == SAMPLE_PLAN_CONTENT


# ===============================================
# Tests for find_project_dir_for_session()
# ===============================================


def test_find_project_dir_for_session_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test finding project directory when session exists."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create session file with matching session ID
    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(session_file, [create_session_entry("session-abc123")])

    result = find_project_dir_for_session("session-abc123")

    assert result == project_dir


def test_find_project_dir_for_session_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test returns None when session ID doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create session file with different session ID
    session_file = project_dir / "session-other.jsonl"
    create_session_file(session_file, [create_session_entry("session-other")])

    result = find_project_dir_for_session("session-not-found")

    assert result is None


def test_find_project_dir_for_session_no_projects_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test returns None when projects directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create projects directory
    result = find_project_dir_for_session("session-abc123")

    assert result is None


def test_find_project_dir_for_session_skips_agent_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that agent-* files are skipped during search."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create agent file (should be skipped)
    agent_file = project_dir / "agent-session-abc123.jsonl"
    create_session_file(agent_file, [create_session_entry("session-abc123")])

    # Create regular session file with different ID
    session_file = project_dir / "session-other.jsonl"
    create_session_file(session_file, [create_session_entry("session-other")])

    # Should NOT find session-abc123 because it's in agent-* file
    result = find_project_dir_for_session("session-abc123")

    assert result is None


# ===============================================
# Tests for extract_slugs_from_session()
# ===============================================


def test_extract_slugs_from_session_single_slug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test extracting a single slug from session."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create session file with slug
    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [
            create_session_entry("session-abc123"),
            create_session_entry("session-abc123", slug="joyful-munching-hammock"),
        ],
    )

    result = extract_slugs_from_session("session-abc123")

    assert result == ["joyful-munching-hammock"]


def test_extract_slugs_from_session_multiple_slugs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test extracting multiple slugs maintains order."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create session file with multiple slugs
    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [
            create_session_entry("session-abc123", slug="first-plan-slug"),
            create_session_entry("session-abc123"),
            create_session_entry("session-abc123", slug="second-plan-slug"),
        ],
    )

    result = extract_slugs_from_session("session-abc123")

    assert result == ["first-plan-slug", "second-plan-slug"]


def test_extract_slugs_from_session_no_slugs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test returns empty list when no slugs in session."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create session file without slugs
    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [
            create_session_entry("session-abc123"),
            create_session_entry("session-abc123"),
        ],
    )

    result = extract_slugs_from_session("session-abc123")

    assert result == []


def test_extract_slugs_from_session_session_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test returns empty list when session not found."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory but no matching session
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    result = extract_slugs_from_session("session-not-found")

    assert result == []


def test_extract_slugs_from_session_deduplicates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that duplicate slugs are deduplicated."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create projects directory structure
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    # Create session file with repeated slug
    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [
            create_session_entry("session-abc123", slug="same-slug"),
            create_session_entry("session-abc123", slug="same-slug"),
            create_session_entry("session-abc123", slug="same-slug"),
        ],
    )

    result = extract_slugs_from_session("session-abc123")

    assert result == ["same-slug"]


# ===============================================
# Tests for get_latest_plan() with session_id
# ===============================================


def test_get_latest_plan_with_session_id_uses_slug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that session_id lookup uses slug to find correct plan."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create two plan files
    older_plan = plans_dir / "joyful-munching-hammock.md"
    older_plan.write_text("# Session Plan\nThis is the session-specific plan", encoding="utf-8")

    time.sleep(0.01)

    newer_plan = plans_dir / "newer-plan.md"
    newer_plan.write_text("# Newer Plan\nThis is newer by mtime", encoding="utf-8")

    # Create projects directory with session containing slug
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [create_session_entry("session-abc123", slug="joyful-munching-hammock")],
    )

    # Should return the slug-matched plan, not the newer one
    result = get_latest_plan("/any/dir", session_id="session-abc123")

    assert result == "# Session Plan\nThis is the session-specific plan"


def test_get_latest_plan_falls_back_without_slug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test falls back to mtime when session has no slug."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create plan file
    plan = plans_dir / "only-plan.md"
    plan.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    # Create projects directory with session WITHOUT slug
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [create_session_entry("session-abc123")],  # No slug
    )

    # Should fall back to mtime selection
    result = get_latest_plan("/any/dir", session_id="session-abc123")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_falls_back_when_slug_plan_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test falls back to mtime when slug's plan file doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory with only a fallback plan
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    fallback_plan = plans_dir / "fallback-plan.md"
    fallback_plan.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    # Create projects directory with session that has a slug
    # but the corresponding plan file doesn't exist
    projects_dir = tmp_path / ".claude" / "projects"
    project_dir = projects_dir / "my-project"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-abc123.jsonl"
    create_session_file(
        session_file,
        [create_session_entry("session-abc123", slug="nonexistent-plan")],
    )

    # Should fall back to mtime selection since slug's file doesn't exist
    result = get_latest_plan("/any/dir", session_id="session-abc123")

    assert result == SAMPLE_PLAN_CONTENT
