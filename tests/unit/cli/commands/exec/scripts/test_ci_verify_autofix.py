"""Tests for ci-verify-autofix exec command.

Tests the CI verification command that runs after autofix pushes a new commit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.ci_verify_autofix import (
    CheckResult,
    VerifySuccess,
    _verify_autofix_impl,
    ci_verify_autofix,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.time.fake import FakeTime

if TYPE_CHECKING:
    from collections.abc import Callable


# Type alias for the status reporting function used in tests
StatusReportCallArgs = dict[str, str | Path]


def make_tracking_report_fn() -> tuple[Callable[..., bool], list[StatusReportCallArgs]]:
    """Create a tracking status report function that records calls.

    Returns:
        Tuple of (report function, list of call records)
    """
    calls: list[StatusReportCallArgs] = []

    def report_fn(
        *,
        repo: str,
        sha: str,
        name: str,
        state: str,
        description: str,
        cwd: Path,
    ) -> bool:
        calls.append(
            {
                "repo": repo,
                "sha": sha,
                "name": name,
                "state": state,
                "description": description,
                "cwd": cwd,
            }
        )
        return True

    return report_fn, calls


def make_failing_report_fn() -> Callable[..., bool]:
    """Create a status report function that always returns False (failed)."""

    def report_fn(
        *,
        repo: str,
        sha: str,
        name: str,
        state: str,
        description: str,
        cwd: Path,
    ) -> bool:
        return False

    return report_fn


class TestVerifyAutofixImpl:
    """Tests for the _verify_autofix_impl function."""

    def test_no_new_commit_returns_early(self, tmp_path: Path) -> None:
        """When current SHA matches original, return immediately without running checks."""
        report_fn, calls = make_tracking_report_fn()

        result = _verify_autofix_impl(
            original_sha="abc123",
            repo="owner/repo",
            cwd=tmp_path,
            current_sha="abc123",  # Same as original
            report_status_fn=report_fn,
        )

        assert isinstance(result, VerifySuccess)
        assert result.success is True
        assert result.new_commit_pushed is False
        assert result.current_sha == "abc123"
        assert result.checks == []
        assert calls == []  # No status reports made

    def test_new_commit_runs_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When SHA changes, run all checks."""
        report_fn, calls = make_tracking_report_fn()

        # Mock subprocess.run to simulate all checks passing
        run_calls: list[list[str]] = []

        def mock_run(cmd: list[str], **kwargs: object) -> object:
            run_calls.append(cmd)

            class MockResult:
                returncode = 0

            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)

        result = _verify_autofix_impl(
            original_sha="abc123",
            repo="owner/repo",
            cwd=tmp_path,
            current_sha="def456",  # Different from original
            report_status_fn=report_fn,
        )

        assert isinstance(result, VerifySuccess)
        assert result.success is True
        assert result.new_commit_pushed is True
        assert result.current_sha == "def456"
        assert len(result.checks) == 7  # All 7 CI checks
        assert all(check.passed for check in result.checks)

        # Verify status reports were made for all checks
        assert len(calls) == 7
        assert all(call["state"] == "success" for call in calls)

    def test_failed_check_reports_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a check fails, report failure status."""
        import subprocess

        report_fn, calls = make_tracking_report_fn()

        # Mock subprocess.run to fail on lint check
        def mock_run(cmd: list[str], **kwargs: object) -> object:
            if "lint" in cmd:
                raise subprocess.CalledProcessError(1, cmd)

            class MockResult:
                returncode = 0

            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)

        result = _verify_autofix_impl(
            original_sha="abc123",
            repo="owner/repo",
            cwd=tmp_path,
            current_sha="def456",
            report_status_fn=report_fn,
        )

        assert isinstance(result, VerifySuccess)
        assert result.success is True
        assert result.new_commit_pushed is True

        # Find the lint check result
        lint_check = next(c for c in result.checks if c.name == "lint")
        assert lint_check.passed is False

        # Verify failure status was reported
        lint_call = next(c for c in calls if c["name"] == "lint")
        assert lint_call["state"] == "failure"

    def test_status_report_failure_tracked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When status report fails, track in result."""
        report_fn = make_failing_report_fn()

        # Mock subprocess.run to pass all checks
        def mock_run(cmd: list[str], **kwargs: object) -> object:
            class MockResult:
                returncode = 0

            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)

        result = _verify_autofix_impl(
            original_sha="abc123",
            repo="owner/repo",
            cwd=tmp_path,
            current_sha="def456",
            report_status_fn=report_fn,
        )

        assert isinstance(result, VerifySuccess)
        # All checks passed but status reports failed
        assert all(check.passed for check in result.checks)
        assert all(not check.status_reported for check in result.checks)


def _extract_json_from_output(output: str) -> dict[str, Any]:
    """Extract JSON object from mixed stdout/stderr output.

    The command writes diagnostic messages to stderr and JSON to stdout,
    but CliRunner mixes them by default. This function finds and parses
    the JSON portion.

    Args:
        output: Combined stdout/stderr output from CliRunner

    Returns:
        Parsed JSON dict
    """
    # Find the last line that looks like JSON (starts with {)
    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"No JSON found in output: {output}")


class TestCiVerifyAutofixCommand:
    """Tests for the CI verify autofix Click command."""

    def test_command_no_new_commit(self, tmp_path: Path) -> None:
        """Test command when no new commit was pushed."""
        git = FakeGit(
            branch_heads={"HEAD": "abc123"},
        )
        time_impl = FakeTime()
        ctx = ErkContext.for_test(git=git, cwd=tmp_path)
        # Inject time into context
        ctx = _inject_time(ctx, time_impl)

        runner = CliRunner()
        result = runner.invoke(
            ci_verify_autofix,
            ["--original-sha", "abc123", "--repo", "owner/repo"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = _extract_json_from_output(result.output)
        assert data["success"] is True
        assert data["new_commit_pushed"] is False

    def test_command_outputs_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test command outputs valid JSON with check results."""
        git = FakeGit(
            branch_heads={"HEAD": "def456"},
        )
        time_impl = FakeTime()
        ctx = ErkContext.for_test(git=git, cwd=tmp_path)
        ctx = _inject_time(ctx, time_impl)

        # Mock subprocess.run to pass all checks and skip gh status reports
        def mock_run(cmd: list[str], **kwargs: object) -> object:
            # For gh api calls, just succeed silently
            if cmd[0] == "gh":

                class MockResult:
                    returncode = 0
                    stdout = b""
                    stderr = b""

                return MockResult()

            class MockResult:
                returncode = 0

            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)

        runner = CliRunner()
        result = runner.invoke(
            ci_verify_autofix,
            ["--original-sha", "abc123", "--repo", "owner/repo"],
            obj=ctx,
        )

        assert result.exit_code == 0
        data = _extract_json_from_output(result.output)
        assert data["success"] is True
        assert data["new_commit_pushed"] is True
        assert data["current_sha"] == "def456"
        checks = data["checks"]
        assert isinstance(checks, list)
        assert len(checks) == 7

    def test_command_exits_with_error_on_check_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test command exits with code 1 when any check fails."""
        import subprocess

        git = FakeGit(
            branch_heads={"HEAD": "def456"},
        )
        time_impl = FakeTime()
        ctx = ErkContext.for_test(git=git, cwd=tmp_path)
        ctx = _inject_time(ctx, time_impl)

        # Mock subprocess.run to fail on format check
        def mock_run(cmd: list[str], **kwargs: object) -> object:
            if "format-check" in cmd:
                raise subprocess.CalledProcessError(1, cmd)

            class MockResult:
                returncode = 0
                stdout = b""
                stderr = b""

            return MockResult()

        monkeypatch.setattr("subprocess.run", mock_run)

        runner = CliRunner()
        result = runner.invoke(
            ci_verify_autofix,
            ["--original-sha", "abc123", "--repo", "owner/repo"],
            obj=ctx,
        )

        assert result.exit_code == 1
        data = _extract_json_from_output(result.output)
        assert data["success"] is True  # Command succeeded
        # But at least one check failed
        checks: list[dict[str, Any]] = data["checks"]
        format_check = next(c for c in checks if c["name"] == "format")
        assert format_check["passed"] is False


def _inject_time(ctx: ErkContext, time_impl: FakeTime) -> ErkContext:
    """Inject a FakeTime into an ErkContext.

    This is a helper to work around the frozen dataclass.
    """
    from dataclasses import replace

    return replace(ctx, time=time_impl)


class TestCheckResult:
    """Tests for the CheckResult dataclass."""

    def test_check_result_frozen(self) -> None:
        """Verify CheckResult is immutable."""
        result = CheckResult(name="test", passed=True, status_reported=True)
        with pytest.raises(AttributeError):
            result.name = "changed"  # type: ignore[misc]


class TestVerifySuccess:
    """Tests for the VerifySuccess dataclass."""

    def test_verify_success_frozen(self) -> None:
        """Verify VerifySuccess is immutable."""
        result = VerifySuccess(
            success=True,
            new_commit_pushed=False,
            current_sha="abc123",
            checks=[],
        )
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]
