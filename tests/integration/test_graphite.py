"""Integration tests for Graphite with real file I/O.

These tests verify RealGraphite correctly reads and parses Graphite cache
files using actual filesystem operations with tmp_path.
"""

import json
import time
from pathlib import Path

import pytest

from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.real import RealGraphite
from erk_shared.github.types import GitHubRepoId
from tests.conftest import load_fixture


def test_graphite_ops_get_prs_with_real_files(tmp_path: Path):
    """Test Graphite getting PR info with real file I/O."""
    # Set up real file structure
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    pr_info_file = git_dir / ".graphite_pr_info"

    # Write actual fixture data to real file
    fixture_data = load_fixture("graphite/graphite_pr_info.json")
    pr_info_file.write_text(fixture_data, encoding="utf-8")

    # Use FakeGit to provide git directory location
    git_ops = FakeGit(git_common_dirs={tmp_path: git_dir})

    ops = RealGraphite()
    result = ops.get_prs_from_graphite(git_ops, tmp_path)

    assert len(result) == 3
    assert "feature-stack-1" in result
    assert result["feature-stack-1"].number == 101
    assert result["feature-stack-1"].state == "OPEN"


def test_graphite_ops_get_prs_no_git_dir(tmp_path: Path):
    """Test getting PR info when git dir cannot be determined."""
    # FakeGit with no git_common_dirs configured returns None
    git_ops = FakeGit()

    ops = RealGraphite()
    result = ops.get_prs_from_graphite(git_ops, tmp_path)

    assert result == {}


def test_graphite_ops_get_prs_file_not_exists(tmp_path: Path):
    """Test getting PR info when .graphite_pr_info doesn't exist."""
    # Create git dir but no .graphite_pr_info file
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    git_ops = FakeGit(git_common_dirs={tmp_path: git_dir})

    ops = RealGraphite()
    result = ops.get_prs_from_graphite(git_ops, tmp_path)

    assert result == {}


def test_graphite_ops_get_prs_json_error(tmp_path: Path):
    """Test that malformed JSON in .graphite_pr_info raises JSONDecodeError."""
    # Set up real file with invalid JSON
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    pr_info_file = git_dir / ".graphite_pr_info"
    pr_info_file.write_text("not valid json", encoding="utf-8")

    git_ops = FakeGit(git_common_dirs={tmp_path: git_dir})

    ops = RealGraphite()
    with (
        pytest.warns(UserWarning, match="Cannot parse Graphite PR info"),
        pytest.raises(json.JSONDecodeError),
    ):
        ops.get_prs_from_graphite(git_ops, tmp_path)


def test_graphite_ops_get_all_branches(tmp_path: Path):
    """Test getting all branches from Graphite cache with real file I/O."""
    # Set up real file structure
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    cache_file = git_dir / ".graphite_cache_persist"

    # Write actual fixture data to real file
    fixture_data = load_fixture("graphite/graphite_cache_persist.json")
    cache_file.write_text(fixture_data, encoding="utf-8")

    # Configure FakeGit with branch head commits
    commit_map = {
        "main": "abc123",
        "feature-1": "def456",
        "feature-1-sub": "ghi789",
        "feature-2": "jkl012",
    }
    git_ops = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads=commit_map,
    )

    ops = RealGraphite()
    result = ops.get_all_branches(git_ops, tmp_path)

    assert len(result) == 4
    assert "main" in result
    assert result["main"].is_trunk is True
    assert result["main"].commit_sha == "abc123"
    assert result["main"].children == ["feature-1", "feature-2"]

    assert "feature-1" in result
    assert result["feature-1"].parent == "main"
    assert result["feature-1"].children == ["feature-1-sub"]


def test_graphite_ops_get_all_branches_no_cache(tmp_path: Path):
    """Test getting branches when cache file doesn't exist."""
    # Create git dir but no cache file
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    git_ops = FakeGit(git_common_dirs={tmp_path: git_dir})

    ops = RealGraphite()
    result = ops.get_all_branches(git_ops, tmp_path)

    assert result == {}


def test_graphite_ops_get_all_branches_json_error(tmp_path: Path):
    """Test that malformed JSON in .graphite_cache_persist raises JSONDecodeError."""
    # Set up real file with invalid JSON
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    cache_file = git_dir / ".graphite_cache_persist"
    cache_file.write_text("not valid json", encoding="utf-8")

    git_ops = FakeGit(git_common_dirs={tmp_path: git_dir})

    ops = RealGraphite()
    with (
        pytest.warns(UserWarning, match="Cannot parse Graphite cache"),
        pytest.raises(json.JSONDecodeError),
    ):
        ops.get_all_branches(git_ops, tmp_path)


def test_graphite_ops_get_all_branches_caches_when_mtime_unchanged(tmp_path: Path):
    """Test that get_all_branches() uses cache when file hasn't changed.

    With mtime-based caching, repeated calls without file modification
    should return the same cached result.
    """
    # Set up real file structure
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    cache_file = git_dir / ".graphite_cache_persist"

    # Write actual fixture data to real file
    fixture_data = load_fixture("graphite/graphite_cache_persist.json")
    cache_file.write_text(fixture_data, encoding="utf-8")

    # Configure FakeGit with branch head commits
    commit_map = {
        "main": "abc123",
        "feature-1": "def456",
        "feature-1-sub": "ghi789",
        "feature-2": "jkl012",
    }
    git_ops = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads=commit_map,
    )

    ops = RealGraphite()

    # Multiple calls without file change should return cached result
    result1 = ops.get_all_branches(git_ops, tmp_path)
    result2 = ops.get_all_branches(git_ops, tmp_path)

    assert result1 == result2
    assert len(result1) == 4


def test_graphite_ops_get_all_branches_invalidates_on_mtime_change(tmp_path: Path):
    """Test that get_all_branches() re-reads when file mtime changes.

    With mtime-based caching, modifying the file should invalidate the cache
    and cause a re-read on the next call.
    """
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    cache_file = git_dir / ".graphite_cache_persist"

    # Initial content with one branch
    initial_data = {"branches": [["feat-1", {"parentBranchName": "main"}]]}
    cache_file.write_text(json.dumps(initial_data), encoding="utf-8")

    git_ops = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads={"feat-1": "abc123"},
    )
    ops = RealGraphite()

    result1 = ops.get_all_branches(git_ops, tmp_path)
    assert "feat-1" in result1

    # Modify file - ensure mtime changes (sleep to ensure different mtime)
    time.sleep(0.01)
    new_data = {"branches": [["feat-2", {"parentBranchName": "main"}]]}
    cache_file.write_text(json.dumps(new_data), encoding="utf-8")

    # Update git_ops with new branch
    git_ops_updated = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads={"feat-2": "def456"},
    )

    result2 = ops.get_all_branches(git_ops_updated, tmp_path)
    assert "feat-2" in result2
    assert "feat-1" not in result2


def test_graphite_url_construction():
    """Test Graphite URL construction."""
    ops = RealGraphite()
    url = ops.get_graphite_url(GitHubRepoId("dagster-io", "erk"), 42)

    assert url == "https://app.graphite.com/github/pr/dagster-io/erk/42"
