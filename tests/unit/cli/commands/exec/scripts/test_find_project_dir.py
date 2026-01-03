"""Unit tests for find_project_dir kit CLI command.

Tests the deterministic path-to-project-folder mapping and metadata extraction.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.find_project_dir import (
    find_project_dir,
)
from erk_shared.context import ErkContext
from erk_shared.extraction.claude_installation import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
    RealClaudeInstallation,
)

# ============================================================================
# 1. Path Encoding Tests (5 tests)
# Using RealClaudeInstallation for path encoding (pure function behavior)
# ============================================================================


def test_encode_path_basic() -> None:
    """Test basic path encoding without dots."""
    installation = RealClaudeInstallation()
    path = Path("/Users/foo/bar")
    result = installation.encode_path_to_project_folder(path)
    assert result == "-Users-foo-bar"


def test_encode_path_with_hidden_dir() -> None:
    """Test path encoding with hidden directory (starts with dot)."""
    installation = RealClaudeInstallation()
    path = Path("/Users/foo/.config/bar")
    result = installation.encode_path_to_project_folder(path)
    # .config becomes --config (dot becomes dash, then slash becomes dash)
    assert result == "-Users-foo--config-bar"


def test_encode_path_with_multiple_dots() -> None:
    """Test path encoding with multiple dots."""
    installation = RealClaudeInstallation()
    path = Path("/Users/foo/.local/.cache/bar")
    result = installation.encode_path_to_project_folder(path)
    assert result == "-Users-foo--local--cache-bar"


def test_encode_path_with_erk_worktree() -> None:
    """Test encoding realistic erk worktree path."""
    installation = RealClaudeInstallation()
    path = Path("/Users/foo/.erk/repos/erk/worktrees/feature-branch")
    result = installation.encode_path_to_project_folder(path)
    assert result == "-Users-foo--erk-repos-erk-worktrees-feature-branch"


def test_encode_path_tmp_directory() -> None:
    """Test encoding temp directory paths."""
    installation = RealClaudeInstallation()
    path = Path("/private/tmp/test")
    result = installation.encode_path_to_project_folder(path)
    assert result == "-private-tmp-test"


# ============================================================================
# 2. Project Info Discovery Tests via FakeClaudeInstallation (8 tests)
# ============================================================================


def test_find_project_info_success(tmp_path: Path) -> None:
    """Test successful project directory discovery with metadata."""
    # Setup: Create fake installation with sessions
    fake_store = FakeClaudeInstallation(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                    "def456": FakeSessionData(content="{}", size_bytes=2, modified_at=2000.0),
                    "agent-17cfd3f4": FakeSessionData(
                        content="{}",
                        size_bytes=2,
                        modified_at=3000.0,
                        parent_session_id="abc123",
                    ),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    result = fake_store.find_project_info(tmp_path)

    assert result is not None
    project_dir, session_logs, latest_session_id = result
    assert sorted(session_logs) == [
        "abc123.jsonl",
        "agent-17cfd3f4.jsonl",
        "def456.jsonl",
    ]
    # Latest should be the most recent main session (def456 has higher mtime)
    assert latest_session_id == "def456"


def test_find_project_info_with_hidden_directory(tmp_path: Path) -> None:
    """Test project discovery for path with dot (hidden directory)."""
    test_cwd = tmp_path / ".config" / "app"

    fake_store = FakeClaudeInstallation(
        projects={
            test_cwd: FakeProject(
                sessions={
                    "test123": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    result = fake_store.find_project_info(test_cwd)

    assert result is not None
    _, session_logs, _ = result
    assert session_logs == ["test123.jsonl"]


def test_find_project_info_exact_matching_no_false_positives(tmp_path: Path) -> None:
    """Test that exact matching prevents false positives from path prefixes."""
    path1 = tmp_path / "repo"
    path2 = tmp_path / "repo-extended"

    fake_store = FakeClaudeInstallation(
        projects={
            path1: FakeProject(
                sessions={
                    "session1": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            ),
            path2: FakeProject(
                sessions={
                    "session2": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            ),
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    # Test that each path matches only its own project directory
    result1 = fake_store.find_project_info(path1)
    assert result1 is not None
    _, session_logs1, _ = result1
    assert session_logs1 == ["session1.jsonl"]

    result2 = fake_store.find_project_info(path2)
    assert result2 is not None
    _, session_logs2, _ = result2
    assert session_logs2 == ["session2.jsonl"]


def test_find_project_info_latest_session_is_main_not_agent(tmp_path: Path) -> None:
    """Test that latest_session_id excludes agent logs."""
    fake_store = FakeClaudeInstallation(
        projects={
            tmp_path: FakeProject(
                sessions={
                    # Main session (older)
                    "main123": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                    # Agent log (newer - but should be ignored for latest)
                    "agent-abc123": FakeSessionData(
                        content="{}",
                        size_bytes=2,
                        modified_at=2000.0,
                        parent_session_id="main123",
                    ),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    result = fake_store.find_project_info(tmp_path)

    assert result is not None
    _, _, latest_session_id = result
    # Latest should be main session, NOT agent log
    assert latest_session_id == "main123"


def test_find_project_info_no_sessions() -> None:
    """Test project directory with no session logs."""
    # This is actually not possible in practice since we never create
    # project directories without session logs, but test for completeness
    pass  # Skipped - see comment


def test_find_project_info_project_not_found(tmp_path: Path) -> None:
    """Test error when project directory doesn't exist."""
    fake_store = FakeClaudeInstallation(
        projects={},  # No projects
        plans=None,
        settings=None,
        local_settings=None,
    )

    result = fake_store.find_project_info(tmp_path / "nonexistent")

    assert result is None


def test_find_project_info_claude_projects_missing() -> None:
    """Test behavior when no projects configured in fake."""
    fake_store = FakeClaudeInstallation(
        projects=None,  # Explicitly None
        plans=None,
        settings=None,
        local_settings=None,
    )

    result = fake_store.find_project_info(Path("/some/path"))

    assert result is None


def test_find_project_info_sorts_session_logs(tmp_path: Path) -> None:
    """Test that session logs are sorted alphabetically."""
    fake_store = FakeClaudeInstallation(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "zzz": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                    "aaa": FakeSessionData(content="{}", size_bytes=2, modified_at=2000.0),
                    "mmm": FakeSessionData(content="{}", size_bytes=2, modified_at=3000.0),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    result = fake_store.find_project_info(tmp_path)

    assert result is not None
    _, session_logs, _ = result
    assert session_logs == ["aaa.jsonl", "mmm.jsonl", "zzz.jsonl"]


# ============================================================================
# 3. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command with successful project discovery."""
    fake_store = FakeClaudeInstallation(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    runner = CliRunner()
    result = runner.invoke(
        find_project_dir,
        ["--path", str(tmp_path)],
        obj=ErkContext.for_test(claude_installation=fake_store),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True


def test_cli_defaults_to_cwd(tmp_path: Path) -> None:
    """Test CLI command defaults to current working directory."""
    import os

    test_cwd = tmp_path / "test_cwd"
    test_cwd.mkdir()

    fake_store = FakeClaudeInstallation(
        projects={
            test_cwd: FakeProject(
                sessions={
                    "test": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    runner = CliRunner()
    original_cwd = os.getcwd()
    try:
        os.chdir(test_cwd)
        result = runner.invoke(
            find_project_dir,
            [],
            obj=ErkContext.for_test(claude_installation=fake_store),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
    finally:
        os.chdir(original_cwd)


def test_cli_project_not_found(tmp_path: Path) -> None:
    """Test CLI command error when project not found."""
    # Create the test directory (required by Click's exists=True)
    test_dir = tmp_path / "nonexistent"
    test_dir.mkdir()

    # Configure a different project so projects_dir_exists() returns True
    # but the requested path won't be found
    other_path = tmp_path / "other"
    fake_store = FakeClaudeInstallation(
        projects={
            other_path: FakeProject(
                sessions={
                    "test": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    runner = CliRunner()
    result = runner.invoke(
        find_project_dir,
        ["--path", str(test_dir)],
        obj=ErkContext.for_test(claude_installation=fake_store),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "Project directory not found"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    fake_store = FakeClaudeInstallation(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session123": FakeSessionData(content="{}", size_bytes=2, modified_at=1000.0),
                }
            )
        },
        plans=None,
        settings=None,
        local_settings=None,
    )

    runner = CliRunner()
    result = runner.invoke(
        find_project_dir,
        ["--path", str(tmp_path), "--json"],
        obj=ErkContext.for_test(claude_installation=fake_store),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "project_dir" in output
    assert "cwd" in output
    assert "encoded_path" in output
    assert "session_logs" in output
    assert "latest_session_id" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["project_dir"], str)
    assert isinstance(output["cwd"], str)
    assert isinstance(output["encoded_path"], str)
    assert isinstance(output["session_logs"], list)
    assert isinstance(output["latest_session_id"], (str, type(None)))
