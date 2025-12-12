"""Tests for hook logging types."""

from erk_shared.hooks.types import HookExitStatus, classify_exit_code


class TestClassifyExitCode:
    """Tests for classify_exit_code function."""

    def test_exit_code_zero_is_success(self) -> None:
        assert classify_exit_code(0) == HookExitStatus.SUCCESS

    def test_exit_code_two_is_blocked(self) -> None:
        assert classify_exit_code(2) == HookExitStatus.BLOCKED

    def test_exit_code_one_is_error(self) -> None:
        assert classify_exit_code(1) == HookExitStatus.ERROR

    def test_exit_code_negative_is_error(self) -> None:
        assert classify_exit_code(-1) == HookExitStatus.ERROR

    def test_exit_code_other_positive_is_error(self) -> None:
        assert classify_exit_code(127) == HookExitStatus.ERROR
