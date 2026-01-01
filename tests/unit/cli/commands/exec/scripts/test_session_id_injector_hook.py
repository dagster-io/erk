"""Unit tests for session_id_injector_hook command.

These tests use ErkContext.for_test() injection. The .erk/ directory
is created in tmp_path to mark it as a managed project.
"""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.session_id_injector_hook import (
    session_id_injector_hook,
)
from erk_shared.context.context import ErkContext


def test_session_id_injector_hook_writes_session_id_to_file(tmp_path: Path) -> None:
    """Test that hook writes session ID to .erk/scratch/current-session-id file."""
    runner = CliRunner()
    session_id = "test-session-abc123"
    stdin_data = json.dumps({"session_id": session_id})

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    # Inject via ErkContext - NO mocking needed
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(session_id_injector_hook, input=stdin_data, obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"

    # Verify file was created with correct content at repo root
    session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
    assert session_file.exists(), f"Session file not found: {list(tmp_path.rglob('*'))}"
    assert session_file.read_text(encoding="utf-8") == session_id

    # Verify LLM reminder is still output (compressed format)
    assert f"📌 session: {session_id}" in result.output


def test_session_id_injector_hook_creates_parent_directories(tmp_path: Path) -> None:
    """Test that hook creates .erk/scratch/ directory if it doesn't exist."""
    runner = CliRunner()
    session_id = "test-session-xyz789"
    stdin_data = json.dumps({"session_id": session_id})

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    # Verify scratch doesn't exist initially
    scratch_dir = tmp_path / ".erk" / "scratch"
    assert not scratch_dir.exists()

    # Inject via ErkContext
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(session_id_injector_hook, input=stdin_data, obj=ctx)

    assert result.exit_code == 0
    assert scratch_dir.exists()


def test_session_id_injector_hook_no_session_id_no_file_created(tmp_path: Path) -> None:
    """Test that no file is created when no session ID is provided."""
    runner = CliRunner()

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
    result = runner.invoke(session_id_injector_hook, input="", obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""

    # No file should be created
    session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
    assert not session_file.exists()


def test_session_id_injector_hook_github_planning_disabled(tmp_path: Path) -> None:
    """Test that nothing is output or written when github_planning is disabled."""
    runner = CliRunner()
    session_id = "test-session-should-not-appear"
    stdin_data = json.dumps({"session_id": session_id})

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

    with patch(
        "erk.cli.commands.exec.scripts.session_id_injector_hook._is_github_planning_enabled",
        return_value=False,
    ):
        result = runner.invoke(session_id_injector_hook, input=stdin_data, obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""

    # No file should be created
    session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
    assert not session_file.exists()


def test_session_id_injector_hook_overwrites_existing_file(tmp_path: Path) -> None:
    """Test that hook overwrites existing session ID file."""
    runner = CliRunner()
    old_session_id = "old-session-id"
    new_session_id = "new-session-id"

    # Create .erk/ to mark as managed project
    (tmp_path / ".erk").mkdir()

    # Create existing file with old session ID
    session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
    session_file.parent.mkdir(parents=True)
    session_file.write_text(old_session_id, encoding="utf-8")

    # Inject via ErkContext
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

    # Run hook with new session ID
    stdin_data = json.dumps({"session_id": new_session_id})
    result = runner.invoke(session_id_injector_hook, input=stdin_data, obj=ctx)

    assert result.exit_code == 0
    assert session_file.read_text(encoding="utf-8") == new_session_id


def test_session_id_injector_hook_silent_when_not_in_managed_project(
    tmp_path: Path,
) -> None:
    """Test that hook produces no output when not in a managed project."""
    runner = CliRunner()
    session_id = "test-session-abc123"
    stdin_data = json.dumps({"session_id": session_id})

    # No .erk/ directory - NOT a managed project
    ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

    result = runner.invoke(session_id_injector_hook, input=stdin_data, obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""

    # No file should be created
    session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
    assert not session_file.exists()
