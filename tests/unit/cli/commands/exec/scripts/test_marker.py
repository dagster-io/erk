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
        """Test creating a marker file succeeds with --session-id flag."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "--session-id", session_id, "my-marker"],
            obj=ctx,
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

    def test_create_marker_requires_session_id_flag(self, tmp_path: Path) -> None:
        """Test that --session-id flag is required (env var is NOT read)."""
        runner = CliRunner()
        env_session_id = "env-session-789"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        # Even with env var set, should fail without --session-id flag
        result = runner.invoke(
            marker,
            ["create", "my-marker"],
            obj=ctx,
            env={"CLAUDE_CODE_SESSION_ID": env_session_id},
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "session ID" in data["message"]

        # Verify marker file was NOT created
        marker_file = (
            tmp_path / ".erk" / "scratch" / "sessions" / env_session_id / "my-marker.marker"
        )
        assert not marker_file.exists()

    def test_create_marker_missing_session_id(self, tmp_path: Path) -> None:
        """Test creating marker fails without session ID."""
        runner = CliRunner()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "my-marker"],
            obj=ctx,
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "session ID" in data["message"]

    def test_create_marker_with_associated_objective(self, tmp_path: Path) -> None:
        """Test creating marker with --associated-objective stores the issue number."""
        runner = CliRunner()
        session_id = "test-session-123"
        objective_issue = 3679

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            [
                "create",
                "--session-id",
                session_id,
                "--associated-objective",
                str(objective_issue),
                "objective-context",
            ],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "objective-context" in data["message"]

        # Verify marker file was created with correct content
        marker_file = (
            tmp_path / ".erk" / "scratch" / "sessions" / session_id / "objective-context.marker"
        )
        assert marker_file.exists()
        assert marker_file.read_text(encoding="utf-8") == "3679"

    def test_create_marker_without_associated_objective_creates_empty_file(
        self, tmp_path: Path
    ) -> None:
        """Test creating marker without --associated-objective creates empty file."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "--session-id", session_id, "some-marker"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify marker file was created and is empty
        marker_file = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "some-marker.marker"
        assert marker_file.exists()
        assert marker_file.read_text(encoding="utf-8") == ""

    def test_create_marker_with_content_stores_string(self, tmp_path: Path) -> None:
        """Test creating marker with --content stores the string content."""
        runner = CliRunner()
        session_id = "test-session-123"
        content_value = "4386"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["create", "--session-id", session_id, "--content", content_value, "plan-saved-issue"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "plan-saved-issue" in data["message"]

        # Verify marker file was created with correct content
        marker_file = (
            tmp_path / ".erk" / "scratch" / "sessions" / session_id / "plan-saved-issue.marker"
        )
        assert marker_file.exists()
        assert marker_file.read_text(encoding="utf-8") == "4386"

    def test_create_marker_associated_objective_takes_precedence_over_content(
        self, tmp_path: Path
    ) -> None:
        """Test that --associated-objective takes precedence over --content."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            [
                "create",
                "--session-id",
                session_id,
                "--associated-objective",
                "100",
                "--content",
                "should-be-ignored",
                "test-marker",
            ],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify marker file has the objective number, not the content string
        marker_file = tmp_path / ".erk" / "scratch" / "sessions" / session_id / "test-marker.marker"
        assert marker_file.exists()
        assert marker_file.read_text(encoding="utf-8") == "100"


class TestMarkerRead:
    """Tests for 'erk exec marker read' subcommand."""

    def test_read_returns_content_when_marker_exists(self, tmp_path: Path) -> None:
        """Test read returns marker content and exit code 0."""
        runner = CliRunner()
        session_id = "test-session-123"
        marker_content = "4386"

        # Pre-create the marker file with content
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "plan-saved-issue.marker"
        marker_file.write_text(marker_content, encoding="utf-8")

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["read", "--session-id", session_id, "plan-saved-issue"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert result.output.strip() == "4386"

    def test_read_with_explicit_session_id(self, tmp_path: Path) -> None:
        """Test read with --session-id flag."""
        runner = CliRunner()
        session_id = "explicit-session-456"
        marker_content = "1234"

        # Pre-create the marker file
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "my-marker.marker"
        marker_file.write_text(marker_content, encoding="utf-8")

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["read", "--session-id", session_id, "my-marker"],
            obj=ctx,
            env={},  # No env var, should use --session-id flag
        )

        assert result.exit_code == 0
        assert result.output.strip() == "1234"

    def test_read_returns_failure_when_marker_missing(self, tmp_path: Path) -> None:
        """Test read returns exit code 1 when marker does not exist."""
        runner = CliRunner()
        session_id = "test-session-123"

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["read", "--session-id", session_id, "missing-marker"],
            obj=ctx,
        )

        assert result.exit_code == 1
        # No JSON output for read command on failure (silent exit)
        assert result.output.strip() == ""

    def test_read_missing_session_id(self, tmp_path: Path) -> None:
        """Test read fails without session ID."""
        runner = CliRunner()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["read", "my-marker"],
            obj=ctx,
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "session ID" in data["message"]

    def test_read_strips_whitespace(self, tmp_path: Path) -> None:
        """Test read strips leading/trailing whitespace from content."""
        runner = CliRunner()
        session_id = "test-session-123"
        marker_content = "  4386\n  "  # Content with whitespace

        # Pre-create the marker file with whitespace
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "plan-saved-issue.marker"
        marker_file.write_text(marker_content, encoding="utf-8")

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["read", "--session-id", session_id, "plan-saved-issue"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert result.output.strip() == "4386"

    def test_read_empty_marker_returns_empty_string(self, tmp_path: Path) -> None:
        """Test read returns empty string for empty marker file."""
        runner = CliRunner()
        session_id = "test-session-123"

        # Pre-create an empty marker file
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        marker_file = marker_dir / "empty-marker.marker"
        marker_file.touch()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(
            marker,
            ["read", "--session-id", session_id, "empty-marker"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert result.output.strip() == ""


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
            ["exists", "--session-id", session_id, "my-marker"],
            obj=ctx,
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
            ["exists", "--session-id", session_id, "missing-marker"],
            obj=ctx,
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
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "session ID" in data["message"]


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
            ["delete", "--session-id", session_id, "my-marker"],
            obj=ctx,
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
            ["delete", "--session-id", session_id, "missing-marker"],
            obj=ctx,
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
        )

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "session ID" in data["message"]
