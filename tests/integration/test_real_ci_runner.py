"""Integration tests for RealCIRunner gateway operations.

These tests verify that RealCIRunner correctly handles subprocess calls.
Integration tests use actual subprocess calls to validate the abstractions.

Tests use simple shell commands (echo, false) that are available on all systems.
"""

from pathlib import Path

from erk_shared.gateway.ci_runner.real import RealCIRunner


def test_run_check_passes_on_successful_command(tmp_path: Path) -> None:
    """Test that run_check returns passed=True for successful commands."""
    runner = RealCIRunner()

    result = runner.run_check(
        name="echo-test",
        cmd=["echo", "hello"],
        cwd=tmp_path,
    )

    assert result.passed is True
    assert result.error_type is None


def test_run_check_fails_on_failed_command(tmp_path: Path) -> None:
    """Test that run_check returns passed=False for failed commands."""
    runner = RealCIRunner()

    result = runner.run_check(
        name="false-test",
        cmd=["false"],  # Always exits with code 1
        cwd=tmp_path,
    )

    assert result.passed is False
    assert result.error_type == "command_failed"


def test_run_check_handles_command_not_found(tmp_path: Path) -> None:
    """Test that run_check handles missing commands."""
    runner = RealCIRunner()

    result = runner.run_check(
        name="missing-test",
        cmd=["nonexistent_command_that_does_not_exist_12345"],
        cwd=tmp_path,
    )

    assert result.passed is False
    assert result.error_type == "command_not_found"
