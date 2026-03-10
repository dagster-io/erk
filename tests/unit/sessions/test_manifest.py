"""Tests for shared manifest reader."""

import json
from pathlib import Path

from erk_shared.sessions.manifest import read_session_manifest
from tests.fakes.gateway.git import FakeGit


def test_returns_none_when_ref_not_found(tmp_path: Path) -> None:
    """Returns None when read_file_from_ref returns None (file not on ref)."""
    fake_git = FakeGit()

    result = read_session_manifest(
        fake_git,
        repo_root=tmp_path,
        session_branch="planned-pr-context/100",
    )

    assert result is None


def test_returns_none_for_empty_content(tmp_path: Path) -> None:
    """Returns None when manifest file exists but is empty."""
    fake_git = FakeGit(
        ref_file_contents={
            ("origin/planned-pr-context/100", ".erk/sessions/manifest.json"): b"   ",
        },
    )

    result = read_session_manifest(
        fake_git,
        repo_root=tmp_path,
        session_branch="planned-pr-context/100",
    )

    assert result is None


def test_returns_parsed_dict_for_valid_json(tmp_path: Path) -> None:
    """Returns parsed manifest dict for valid JSON content."""
    manifest = {
        "version": 1,
        "plan_id": 100,
        "sessions": [
            {
                "session_id": "test-session-1",
                "stage": "impl",
                "files": ["impl-test-session-1.xml"],
            }
        ],
    }
    fake_git = FakeGit(
        ref_file_contents={
            ("origin/planned-pr-context/100", ".erk/sessions/manifest.json"): json.dumps(
                manifest
            ).encode("utf-8"),
        },
    )

    result = read_session_manifest(
        fake_git,
        repo_root=tmp_path,
        session_branch="planned-pr-context/100",
    )

    assert result is not None
    assert result["version"] == 1
    assert result["plan_id"] == 100
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["session_id"] == "test-session-1"
