"""Unit tests for marker kit CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from erk_shared.scratch.markers import create_marker, marker_exists

from dot_agent_kit.data.kits.erk.scripts.erk.check_marker import check_marker
from dot_agent_kit.data.kits.erk.scripts.erk.marker_delete import marker_delete


def test_marker_delete_removes_existing_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test marker-delete removes an existing marker."""
    create_marker(tmp_path, "test-marker")
    assert marker_exists(tmp_path, "test-marker")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(marker_delete, ["test-marker"])

    assert result.exit_code == 0
    assert "Deleted marker: test-marker" in result.output
    assert not marker_exists(tmp_path, "test-marker")


def test_marker_delete_succeeds_when_marker_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test marker-delete succeeds (is idempotent) when marker doesn't exist."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(marker_delete, ["nonexistent-marker"])

    assert result.exit_code == 0
    assert "Marker did not exist: nonexistent-marker" in result.output


def test_marker_delete_json_output_when_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test marker-delete JSON output when marker was deleted."""
    create_marker(tmp_path, "test-marker")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(marker_delete, ["test-marker", "--json"])

    assert result.exit_code == 0
    assert '"deleted": true' in result.output
    assert '"marker": "test-marker"' in result.output


def test_marker_delete_json_output_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test marker-delete JSON output when marker didn't exist."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(marker_delete, ["nonexistent-marker", "--json"])

    assert result.exit_code == 0
    assert '"deleted": false' in result.output
    assert '"marker": "nonexistent-marker"' in result.output


def test_check_marker_returns_zero_when_marker_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check-marker returns exit code 0 when marker exists."""
    create_marker(tmp_path, "test-marker")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(check_marker, ["test-marker"])

    assert result.exit_code == 0
    assert "Marker exists: test-marker" in result.output


def test_check_marker_returns_one_when_marker_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check-marker returns exit code 1 when marker doesn't exist."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(check_marker, ["nonexistent-marker"])

    assert result.exit_code == 1
    assert "Marker does not exist: nonexistent-marker" in result.output


def test_check_marker_json_output_when_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check-marker JSON output when marker exists."""
    create_marker(tmp_path, "test-marker")

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(check_marker, ["test-marker", "--json"])

    assert result.exit_code == 0
    assert '"exists": true' in result.output
    assert '"marker": "test-marker"' in result.output


def test_check_marker_json_output_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test check-marker JSON output when marker doesn't exist.

    Note: With --json flag, exit code is still 0 (JSON output is for scripting).
    """
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(check_marker, ["nonexistent-marker", "--json"])

    assert result.exit_code == 0
    assert '"exists": false' in result.output
    assert '"marker": "nonexistent-marker"' in result.output
