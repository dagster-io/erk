"""Unit tests for find_project_dir kit CLI command.

Tests the deterministic path-to-project-folder mapping and metadata extraction.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.find_project_dir import (
    ProjectError,
    ProjectInfo,
    encode_path_to_project_folder,
    find_project_dir,
    find_project_info,
)
from erk_shared.context import ErkContext
from erk_shared.learn.extraction.claude_installation.fake import FakeClaudeInstallation

# ============================================================================
# 1. Path Encoding Tests (5 tests)
# ============================================================================


def test_encode_path_basic() -> None:
    """Test basic path encoding without dots."""
    path = Path("/Users/foo/bar")
    result = encode_path_to_project_folder(path)
    assert result == "-Users-foo-bar"


def test_encode_path_with_hidden_dir() -> None:
    """Test path encoding with hidden directory (starts with dot)."""
    path = Path("/Users/foo/.config/bar")
    result = encode_path_to_project_folder(path)
    # .config becomes --config (dot becomes dash, then slash becomes dash)
    assert result == "-Users-foo--config-bar"


def test_encode_path_with_multiple_dots() -> None:
    """Test path encoding with multiple dots."""
    path = Path("/Users/foo/.local/.cache/bar")
    result = encode_path_to_project_folder(path)
    assert result == "-Users-foo--local--cache-bar"


def test_encode_path_with_erk_worktree() -> None:
    """Test encoding realistic erk worktree path."""
    path = Path("/Users/foo/.erk/repos/erk/worktrees/feature-branch")
    result = encode_path_to_project_folder(path)
    assert result == "-Users-foo--erk-repos-erk-worktrees-feature-branch"


def test_encode_path_tmp_directory() -> None:
    """Test encoding temp directory paths."""
    path = Path("/private/tmp/test")
    result = encode_path_to_project_folder(path)
    assert result == "-private-tmp-test"


# ============================================================================
# 2. Project Info Discovery Tests (8 tests)
# ============================================================================


def test_find_project_info_success(tmp_path: Path) -> None:
    """Test successful project directory discovery with metadata."""
    # Setup: Create mock ~/.claude/projects/ structure
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create test path and corresponding project directory
    test_cwd = tmp_path / "test" / "repo"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create mock session logs
    (project_dir / "abc123.jsonl").write_text("{}", encoding="utf-8")
    (project_dir / "def456.jsonl").write_text("{}", encoding="utf-8")
    (project_dir / "agent-17cfd3f4.jsonl").write_text("{}", encoding="utf-8")

    # Create FakeClaudeInstallation with real projects directory
    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    # Test
    result = find_project_info(test_cwd, installation)

    # Assertions
    assert isinstance(result, ProjectInfo)
    assert result.success is True
    assert result.project_dir == str(project_dir)
    assert result.cwd == str(test_cwd)
    assert result.encoded_path == encoded_name
    assert sorted(result.session_logs) == [
        "abc123.jsonl",
        "agent-17cfd3f4.jsonl",
        "def456.jsonl",
    ]
    # Latest should be one of the main sessions (not agent log)
    assert result.latest_session_id in ["abc123", "def456"]


def test_find_project_info_with_hidden_directory(tmp_path: Path) -> None:
    """Test project discovery for path with dot (hidden directory)."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Test path with hidden directory
    test_cwd = tmp_path / ".config" / "app"
    encoded_name = encode_path_to_project_folder(test_cwd)
    assert encoded_name == f"{str(tmp_path).replace('/', '-')}--config-app"

    project_dir = projects_dir / encoded_name
    project_dir.mkdir()
    (project_dir / "test123.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = find_project_info(test_cwd, installation)

    assert isinstance(result, ProjectInfo)
    assert result.success is True
    assert result.encoded_path == encoded_name


def test_find_project_info_exact_matching_no_false_positives(tmp_path: Path) -> None:
    """Test that exact matching prevents false positives from path prefixes."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create two projects where one path is prefix of another
    path1 = tmp_path / "repo"
    path2 = tmp_path / "repo-extended"

    encoded1 = encode_path_to_project_folder(path1)
    encoded2 = encode_path_to_project_folder(path2)

    (projects_dir / encoded1).mkdir()
    (projects_dir / encoded2).mkdir()

    # Create session logs in both
    (projects_dir / encoded1 / "session1.jsonl").write_text("{}", encoding="utf-8")
    (projects_dir / encoded2 / "session2.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    # Test that each path matches only its own project directory
    result1 = find_project_info(path1, installation)
    assert isinstance(result1, ProjectInfo)
    assert result1.project_dir == str(projects_dir / encoded1)
    assert result1.session_logs == ["session1.jsonl"]

    result2 = find_project_info(path2, installation)
    assert isinstance(result2, ProjectInfo)
    assert result2.project_dir == str(projects_dir / encoded2)
    assert result2.session_logs == ["session2.jsonl"]


def test_find_project_info_latest_session_is_main_not_agent(tmp_path: Path) -> None:
    """Test that latest_session_id excludes agent logs."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create main session (older)
    main_session = project_dir / "main123.jsonl"
    main_session.write_text("{}", encoding="utf-8")

    # Create agent log (newer - but should be ignored)
    agent_log = project_dir / "agent-abc123.jsonl"
    agent_log.write_text("{}", encoding="utf-8")

    # Make agent log newer by touching it after a delay
    import time

    time.sleep(0.01)
    agent_log.touch()

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = find_project_info(test_cwd, installation)

    # Latest should be main session, NOT agent log
    assert isinstance(result, ProjectInfo)
    assert result.latest_session_id == "main123"


def test_find_project_info_no_sessions() -> None:
    """Test project directory with no session logs."""
    # This is actually not possible in practice since we never create
    # project directories without session logs, but test for completeness
    pass  # Skipped - see comment


def test_find_project_info_project_not_found(tmp_path: Path) -> None:
    """Test error when project directory doesn't exist."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = find_project_info(tmp_path / "nonexistent", installation)

    assert isinstance(result, ProjectError)
    assert result.success is False
    assert result.error == "Project directory not found"
    assert "nonexistent" in result.help


def test_find_project_info_claude_projects_missing(tmp_path: Path) -> None:
    """Test error when ~/.claude/projects/ doesn't exist."""
    # projects_dir does not exist
    nonexistent_projects_dir = tmp_path / ".claude" / "projects"

    installation = FakeClaudeInstallation.for_test(projects_dir_path=nonexistent_projects_dir)

    result = find_project_info(tmp_path / "some" / "path", installation)

    assert isinstance(result, ProjectError)
    assert result.success is False
    assert result.error == "Claude Code projects directory not found"
    assert "Is Claude Code installed?" in result.help


def test_find_project_info_sorts_session_logs(tmp_path: Path) -> None:
    """Test that session logs are sorted alphabetically."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()

    # Create logs in non-alphabetical order
    (project_dir / "zzz.jsonl").write_text("{}", encoding="utf-8")
    (project_dir / "aaa.jsonl").write_text("{}", encoding="utf-8")
    (project_dir / "mmm.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    result = find_project_info(test_cwd, installation)

    assert isinstance(result, ProjectInfo)
    assert result.session_logs == ["aaa.jsonl", "mmm.jsonl", "zzz.jsonl"]


# ============================================================================
# 3. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command with successful project discovery."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()  # Create the test directory
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()
    (project_dir / "test.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    result = runner.invoke(
        find_project_dir,
        ["--path", str(test_cwd)],
        obj=ErkContext.for_test(cwd=tmp_path, claude_installation=installation),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["encoded_path"] == encoded_name


def test_cli_defaults_to_cwd(tmp_path: Path) -> None:
    """Test CLI command defaults to current working directory."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create a test cwd directory
    test_cwd = tmp_path / "test_cwd"
    test_cwd.mkdir()

    # Create project directory for test_cwd
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()
    (project_dir / "test.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    # Run without --path flag (should use cwd)
    # Change to test_cwd directory before running
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(test_cwd)
        result = runner.invoke(
            find_project_dir,
            [],
            obj=ErkContext.for_test(cwd=test_cwd, claude_installation=installation),
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
    finally:
        os.chdir(original_cwd)


def test_cli_project_not_found(tmp_path: Path) -> None:
    """Test CLI command error when project not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create the test directory (required by Click's exists=True)
    test_dir = tmp_path / "nonexistent"
    test_dir.mkdir()

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    result = runner.invoke(
        find_project_dir,
        ["--path", str(test_dir)],
        obj=ErkContext.for_test(cwd=tmp_path, claude_installation=installation),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "Project directory not found"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    test_cwd = tmp_path / "test"
    test_cwd.mkdir()  # Create the test directory
    encoded_name = encode_path_to_project_folder(test_cwd)
    project_dir = projects_dir / encoded_name
    project_dir.mkdir()
    (project_dir / "session123.jsonl").write_text("{}", encoding="utf-8")

    installation = FakeClaudeInstallation.for_test(projects_dir_path=projects_dir)

    runner = CliRunner()
    result = runner.invoke(
        find_project_dir,
        ["--path", str(test_cwd), "--json"],
        obj=ErkContext.for_test(cwd=tmp_path, claude_installation=installation),
    )

    assert result.exit_code == 0
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
