"""Tests for erk exec marker command.

Tests the create/exists/delete subcommands for marker file management.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.marker import marker
from erk_shared.context.context import ErkContext


class TestMarkerCreate:
    """Tests for 'erk exec marker create' subcommand."""

    def test_create_marker_success(self, tmp_path: Path) -> None:
        """Test creating a marker file succeeds."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "my-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": session_id},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "my-marker" in data["message"]

        # Verify marker file was created
        marker_file = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "my-marker.marker"
        assert marker_file.exists()

    def test_create_marker_with_explicit_session_id(self, tmp_path: Path) -> None:
        """Test creating marker with --session-id flag."""
        runner = CliRunner()
        session_id = "explicit-session-456"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "--session-id", session_id, "my-marker"],
            obj=ctx,
            env={},  # No env var, should use --session-id flag
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "my-marker" in data["message"]

        # Verify marker file was created in correct location
        marker_file = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "my-marker.marker"
        assert marker_file.exists()

    def test_create_marker_session_id_option_takes_precedence_over_env(
        self, tmp_path: Path
    ) -> None:
        """Test that --session-id flag takes precedence over environment variable."""
        runner = CliRunner()
        env_session_id = "env-session-789"
        flag_session_id = "flag-session-999"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "--session-id", flag_session_id, "my-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": env_session_id},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

        # Verify marker file was created using flag value, not env var
        marker_file_flag = (
            tmp_path / ".erk" / "scratch" / "sessions" / flag_session_id / "my-marker.marker"
        )
        marker_file_env = (
            tmp_path / ".erk" / "scratch" / "sessions" / env_session_id / "my-marker.marker"
        )
        assert marker_file_flag.exists()
        assert not marker_file_env.exists()

    def test_create_marker_missing_session_id(self, tmp_path: Path) -> None:
        """Test creating marker fails without session ID."""
        runner = CliRunner()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "my-marker"],
            obj=ctx,
            env={},  # No CLAUDE_CODE_SESSION_ID
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "CLAUDE_CODE_SESSION_ID" in data["message"] or "session ID" in data["message"]


class TestMarkerExists:
    """Tests for 'erk exec marker exists' subcommand."""

    def test_exists_returns_success_when_marker_present(self, tmp_path: Path) -> None:
        """Test exists returns exit code 0 when marker exists."""
        runner = CliRunner()
        session_id = "test-session-123"

        # Pre-create the marker file
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "my-marker.marker"
        marker_file.touch()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["exists", "my-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": session_id},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "exists" in data["message"]

    def test_exists_with_explicit_session_id(self, tmp_path: Path) -> None:
        """Test exists with --session-id flag."""
        runner = CliRunner()
        session_id = "explicit-session-456"

        # Pre-create the marker file
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "my-marker.marker"
        marker_file.touch()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["exists", "--session-id", session_id, "my-marker"],
            obj=ctx,
            env={},  # No env var, should use --session-id flag
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "exists" in data["message"]

    def test_exists_returns_failure_when_marker_missing(self, tmp_path: Path) -> None:
        """Test exists returns exit code 1 when marker does not exist."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["exists", "missing-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": session_id},
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "does not exist" in data["message"]

    def test_exists_missing_session_id(self, tmp_path: Path) -> None:
        """Test exists fails without session ID."""
        runner = CliRunner()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["exists", "my-marker"],
            obj=ctx,
            env={},  # No CLAUDE_CODE_SESSION_ID
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "CLAUDE_CODE_SESSION_ID" in data["message"] or "session ID" in data["message"]


class TestMarkerDelete:
    """Tests for 'erk exec marker delete' subcommand."""

    def test_delete_marker_success(self, tmp_path: Path) -> None:
        """Test deleting a marker file succeeds."""
        runner = CliRunner()
        session_id = "test-session-123"

        # Pre-create the marker file
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "my-marker.marker"
        marker_file.touch()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["delete", "my-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": session_id},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "Deleted" in data["message"]

        # Verify marker file was deleted
        assert not marker_file.exists()

    def test_delete_marker_with_explicit_session_id(self, tmp_path: Path) -> None:
        """Test deleting marker with --session-id flag."""
        runner = CliRunner()
        session_id = "explicit-session-456"

        # Pre-create the marker file
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "my-marker.marker"
        marker_file.touch()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["delete", "--session-id", session_id, "my-marker"],
            obj=ctx,
            env={},  # No env var, should use --session-id flag
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "Deleted" in data["message"]

        # Verify marker file was deleted
        assert not marker_file.exists()

    def test_delete_nonexistent_marker_is_idempotent(self, tmp_path: Path) -> None:
        """Test deleting a non-existent marker succeeds (idempotent)."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["delete", "missing-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": session_id},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "already deleted" in data["message"]

    def test_delete_missing_session_id(self, tmp_path: Path) -> None:
        """Test delete fails without session ID."""
        runner = CliRunner()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["delete", "my-marker"],
            obj=ctx,
            env={},  # No CLAUDE_CODE_SESSION_ID
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "CLAUDE_CODE_SESSION_ID" in data["message"] or "session ID" in data["message"]
