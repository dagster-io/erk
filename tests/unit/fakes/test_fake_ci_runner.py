"""Unit tests for FakeCIRunner.

These tests verify the fake implementation behaves correctly for testing purposes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from erk_shared.gateway.ci_runner.fake import FakeCIRunner


class TestFakeCIRunner:
    """Tests for FakeCIRunner behavior."""

    def test_default_behavior_all_pass(self, tmp_path: Path) -> None:
        """By default, all checks pass."""
        runner = FakeCIRunner()

        result = runner.run_check(name="test", cmd=["echo", "test"], cwd=tmp_path)

        assert result.passed is True
        assert result.error_type is None

    def test_failing_checks_configuration(self, tmp_path: Path) -> None:
        """Checks in failing_checks set fail with command_failed error."""
        runner = FakeCIRunner(failing_checks={"lint", "format"})

        lint_result = runner.run_check(name="lint", cmd=["make", "lint"], cwd=tmp_path)
        assert lint_result.passed is False
        assert lint_result.error_type == "command_failed"

        format_result = runner.run_check(name="format", cmd=["make", "format"], cwd=tmp_path)
        assert format_result.passed is False
        assert format_result.error_type == "command_failed"

        # Other checks pass
        test_result = runner.run_check(name="test", cmd=["make", "test"], cwd=tmp_path)
        assert test_result.passed is True
        assert test_result.error_type is None

    def test_missing_commands_configuration(self, tmp_path: Path) -> None:
        """Checks in missing_commands set fail with command_not_found error."""
        runner = FakeCIRunner(missing_commands={"prettier"})

        result = runner.run_check(name="prettier", cmd=["prettier", "--check", "."], cwd=tmp_path)

        assert result.passed is False
        assert result.error_type == "command_not_found"

    def test_run_calls_tracking(self, tmp_path: Path) -> None:
        """run_calls property tracks all invocations."""
        runner = FakeCIRunner()

        runner.run_check(name="lint", cmd=["make", "lint"], cwd=tmp_path)
        runner.run_check(name="test", cmd=["make", "test"], cwd=tmp_path)

        calls = runner.run_calls
        assert len(calls) == 2
        assert calls[0].name == "lint"
        assert calls[0].cmd == ["make", "lint"]
        assert calls[0].cwd == tmp_path
        assert calls[1].name == "test"
        assert calls[1].cmd == ["make", "test"]
        assert calls[1].cwd == tmp_path

    def test_check_names_run_property(self, tmp_path: Path) -> None:
        """check_names_run property returns list of check names."""
        runner = FakeCIRunner()

        runner.run_check(name="lint", cmd=["make", "lint"], cwd=tmp_path)
        runner.run_check(name="format", cmd=["make", "format"], cwd=tmp_path)
        runner.run_check(name="test", cmd=["make", "test"], cwd=tmp_path)

        assert runner.check_names_run == ["lint", "format", "test"]

    def test_run_calls_returns_copy(self, tmp_path: Path) -> None:
        """run_calls returns a copy, not the internal list."""
        runner = FakeCIRunner()
        runner.run_check(name="test", cmd=["echo", "test"], cwd=tmp_path)

        calls1 = runner.run_calls
        calls2 = runner.run_calls

        assert calls1 == calls2
        assert calls1 is not calls2  # Different list instances

    def test_both_failing_and_missing_checks(self, tmp_path: Path) -> None:
        """Can configure both failing checks and missing commands."""
        runner = FakeCIRunner(failing_checks={"lint"}, missing_commands={"prettier"})

        lint_result = runner.run_check(name="lint", cmd=["make", "lint"], cwd=tmp_path)
        assert lint_result.passed is False
        assert lint_result.error_type == "command_failed"

        prettier_result = runner.run_check(
            name="prettier", cmd=["prettier", "--check", "."], cwd=tmp_path
        )
        assert prettier_result.passed is False
        assert prettier_result.error_type == "command_not_found"

        test_result = runner.run_check(name="test", cmd=["make", "test"], cwd=tmp_path)
        assert test_result.passed is True
        assert test_result.error_type is None

    def test_empty_run_calls_initially(self, tmp_path: Path) -> None:
        """run_calls is empty before any checks run."""
        runner = FakeCIRunner()

        assert runner.run_calls == []
        assert runner.check_names_run == []


class TestRunCallDataclass:
    """Tests for the RunCall dataclass."""

    def test_run_call_frozen(self, tmp_path: Path) -> None:
        """Verify RunCall is immutable."""
        runner = FakeCIRunner()
        runner.run_check(name="test", cmd=["echo", "test"], cwd=tmp_path)

        call = runner.run_calls[0]
        with pytest.raises(AttributeError):
            call.name = "changed"  # type: ignore[misc]
