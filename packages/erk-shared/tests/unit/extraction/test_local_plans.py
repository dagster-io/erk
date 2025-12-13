"""Tests for local plan extraction module."""

import json
import time
from pathlib import Path

import pytest

from erk_shared.extraction.local_plans import (
    extract_slugs_from_session,
    find_project_dir_for_session,
    get_latest_plan_content,
)


class TestExtractSlugsFromSession:
    """Tests for extract_slugs_from_session function."""

    def test_extracts_slugs_from_session_log(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Extracts plan slugs from session log entries."""
        # Set up fake ~/.claude directory structure
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        # Create session log with slug entries
        session_id = "test-session-123"
        session_log = project_dir / f"{session_id}.jsonl"
        entries = [
            {"sessionId": session_id, "type": "start"},
            {"sessionId": session_id, "slug": "agile-pondering-llama"},
            {"sessionId": session_id, "type": "end"},
        ]
        session_log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        slugs = extract_slugs_from_session(session_id)

        assert slugs == ["agile-pondering-llama"]

    def test_returns_empty_when_no_slugs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns empty list when session has no slug entries."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        session_id = "test-session-456"
        session_log = project_dir / f"{session_id}.jsonl"
        entries = [
            {"sessionId": session_id, "type": "start"},
            {"sessionId": session_id, "type": "end"},
        ]
        session_log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        slugs = extract_slugs_from_session(session_id)

        assert slugs == []

    def test_returns_empty_when_session_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns empty list when session ID not found."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        projects_dir.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        slugs = extract_slugs_from_session("nonexistent-session")

        assert slugs == []

    def test_collects_multiple_slugs_in_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Collects multiple slugs preserving order (last = most recent)."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        session_id = "test-session-789"
        session_log = project_dir / f"{session_id}.jsonl"
        entries = [
            {"sessionId": session_id, "slug": "first-plan"},
            {"sessionId": session_id, "slug": "second-plan"},
            {"sessionId": session_id, "slug": "third-plan"},
        ]
        session_log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        slugs = extract_slugs_from_session(session_id)

        assert slugs == ["first-plan", "second-plan", "third-plan"]


class TestFindProjectDirForSession:
    """Tests for find_project_dir_for_session function."""

    def test_finds_project_with_cwd_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uses cwd hint for fast O(1) lookup."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        # Encode /test/project -> -test-project
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        session_id = "target-session"
        session_log = project_dir / f"{session_id}.jsonl"
        session_log.write_text(json.dumps({"sessionId": session_id}), encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = find_project_dir_for_session(session_id, cwd_hint="/test/project")

        assert result == project_dir

    def test_falls_back_to_scan_without_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to scanning all projects when no hint provided."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-some-project"
        project_dir.mkdir(parents=True)

        session_id = "scan-session"
        session_log = project_dir / f"{session_id}.jsonl"
        session_log.write_text(json.dumps({"sessionId": session_id}), encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = find_project_dir_for_session(session_id)

        assert result == project_dir

    def test_returns_none_when_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns None when session not found in any project."""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        projects_dir.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = find_project_dir_for_session("missing-session")

        assert result is None


class TestGetLatestPlanContent:
    """Tests for get_latest_plan_content function."""

    def test_returns_session_scoped_plan_by_slug(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns plan content matching session's slug."""
        claude_dir = tmp_path / ".claude"
        plans_dir = claude_dir / "plans"
        plans_dir.mkdir(parents=True)
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        # Create plan file
        plan_content = "# My Session Plan\n\nThis is the correct plan."
        (plans_dir / "session-plan-slug.md").write_text(plan_content, encoding="utf-8")

        # Create another plan with newer mtime (should NOT be selected)
        time.sleep(0.01)  # Ensure different mtime
        (plans_dir / "newer-plan.md").write_text("# Wrong Plan", encoding="utf-8")

        # Create session log with slug
        session_id = "session-with-plan"
        session_log = project_dir / f"{session_id}.jsonl"
        session_log.write_text(
            json.dumps({"sessionId": session_id, "slug": "session-plan-slug"}),
            encoding="utf-8",
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_latest_plan_content(session_id=session_id)

        assert result == plan_content

    def test_falls_back_to_mtime_when_no_slug(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to mtime-based selection when session has no slug."""
        claude_dir = tmp_path / ".claude"
        plans_dir = claude_dir / "plans"
        plans_dir.mkdir(parents=True)
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        # Create older plan
        (plans_dir / "older-plan.md").write_text("# Older Plan", encoding="utf-8")
        time.sleep(0.01)
        # Create newer plan (should be selected)
        newer_content = "# Newer Plan"
        (plans_dir / "newer-plan.md").write_text(newer_content, encoding="utf-8")

        # Create session log WITHOUT slug
        session_id = "session-no-slug"
        session_log = project_dir / f"{session_id}.jsonl"
        session_log.write_text(
            json.dumps({"sessionId": session_id, "type": "start"}), encoding="utf-8"
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_latest_plan_content(session_id=session_id)

        assert result == newer_content

    def test_falls_back_to_mtime_when_no_session_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to mtime-based selection when session_id is None."""
        claude_dir = tmp_path / ".claude"
        plans_dir = claude_dir / "plans"
        plans_dir.mkdir(parents=True)

        # Create older plan
        (plans_dir / "older-plan.md").write_text("# Older Plan", encoding="utf-8")
        time.sleep(0.01)
        # Create newer plan (should be selected)
        newer_content = "# Newer Plan"
        (plans_dir / "newer-plan.md").write_text(newer_content, encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_latest_plan_content(session_id=None)

        assert result == newer_content

    def test_returns_none_when_no_plans(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns None when no plan files exist."""
        claude_dir = tmp_path / ".claude"
        plans_dir = claude_dir / "plans"
        plans_dir.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_latest_plan_content(session_id=None)

        assert result is None

    def test_falls_back_when_slug_plan_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to mtime when slug's plan file doesn't exist."""
        claude_dir = tmp_path / ".claude"
        plans_dir = claude_dir / "plans"
        plans_dir.mkdir(parents=True)
        projects_dir = claude_dir / "projects"
        project_dir = projects_dir / "-test-project"
        project_dir.mkdir(parents=True)

        # Create only a fallback plan (slug's plan doesn't exist)
        fallback_content = "# Fallback Plan"
        (plans_dir / "fallback-plan.md").write_text(fallback_content, encoding="utf-8")

        # Create session log with slug pointing to non-existent plan
        session_id = "session-missing-plan"
        session_log = project_dir / f"{session_id}.jsonl"
        session_log.write_text(
            json.dumps({"sessionId": session_id, "slug": "nonexistent-slug"}),
            encoding="utf-8",
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = get_latest_plan_content(session_id=session_id)

        assert result == fallback_content
