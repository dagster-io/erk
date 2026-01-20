"""Tests for FakeCodespace implementation."""

import pytest

from erk_shared.gateway.codespace.fake import FakeCodespace, SSHCall


class TestFakeCodespaceRunSSHCommand:
    """Tests for FakeCodespace run_ssh_command tracking functionality."""

    def test_run_tracks_calls(self) -> None:
        """run_ssh_command() calls are tracked in ssh_calls property."""
        codespace = FakeCodespace()
        codespace.run_ssh_command("cs-abc123", "echo hello")
        codespace.run_ssh_command("cs-def456", "pwd")

        assert len(codespace.ssh_calls) == 2
        assert codespace.ssh_calls[0] == SSHCall(
            gh_name="cs-abc123", remote_command="echo hello", interactive=False
        )
        assert codespace.ssh_calls[1] == SSHCall(
            gh_name="cs-def456", remote_command="pwd", interactive=False
        )

    def test_last_call_returns_most_recent(self) -> None:
        """last_call returns most recent SSH call."""
        codespace = FakeCodespace()
        codespace.run_ssh_command("cs-first", "cmd1")
        codespace.run_ssh_command("cs-second", "cmd2")

        assert codespace.last_call == SSHCall(
            gh_name="cs-second", remote_command="cmd2", interactive=False
        )

    def test_last_call_returns_none_when_empty(self) -> None:
        """last_call returns None when no SSH calls made."""
        codespace = FakeCodespace()

        assert codespace.last_call is None

    def test_ssh_calls_empty_initially(self) -> None:
        """ssh_calls is empty list initially."""
        codespace = FakeCodespace()

        assert codespace.ssh_calls == []


class TestFakeCodespaceExitCodeMode:
    """Tests for FakeCodespace exit code configuration."""

    def test_default_exit_code_returns_zero(self) -> None:
        """Default codespace returns 0 from run_ssh_command()."""
        codespace = FakeCodespace()

        result = codespace.run_ssh_command("cs-test", "command")

        assert result == 0

    def test_run_exit_code_configurable(self) -> None:
        """run_exit_code parameter controls return value."""
        codespace = FakeCodespace(run_exit_code=42)

        result = codespace.run_ssh_command("cs-test", "failing-command")

        assert result == 42

    def test_failure_mode_still_tracks_calls(self) -> None:
        """Failure mode still tracks SSH calls."""
        codespace = FakeCodespace(run_exit_code=1)
        codespace.run_ssh_command("cs-test", "command")

        assert len(codespace.ssh_calls) == 1
        assert codespace.ssh_calls[0].gh_name == "cs-test"


class TestFakeCodespaceExecInteractive:
    """Tests for FakeCodespace exec_ssh_interactive functionality."""

    def test_exec_sets_exec_called_flag(self) -> None:
        """exec_ssh_interactive() sets exec_called flag."""
        codespace = FakeCodespace()

        with pytest.raises(SystemExit):
            codespace.exec_ssh_interactive("cs-test", "command")

        assert codespace.exec_called is True

    def test_exec_tracks_call(self) -> None:
        """exec_ssh_interactive() tracks the call as interactive."""
        codespace = FakeCodespace()

        with pytest.raises(SystemExit):
            codespace.exec_ssh_interactive("cs-test", "command")

        assert len(codespace.ssh_calls) == 1
        assert codespace.ssh_calls[0] == SSHCall(
            gh_name="cs-test", remote_command="command", interactive=True
        )

    def test_exec_raises_system_exit(self) -> None:
        """exec_ssh_interactive() raises SystemExit to simulate process replacement."""
        codespace = FakeCodespace()

        with pytest.raises(SystemExit) as exc_info:
            codespace.exec_ssh_interactive("cs-test", "command")

        assert exc_info.value.code == 0

    def test_exec_called_initially_false(self) -> None:
        """exec_called is False initially."""
        codespace = FakeCodespace()

        assert codespace.exec_called is False


class TestFakeCodespaceDefensiveCopying:
    """Tests for FakeCodespace defensive copying behavior."""

    def test_ssh_calls_returns_copy_of_list(self) -> None:
        """ssh_calls returns a copy to prevent external mutation."""
        codespace = FakeCodespace()
        codespace.run_ssh_command("cs-test", "command")

        # Modify the returned list
        returned_list = codespace.ssh_calls
        returned_list.append(
            SSHCall(gh_name="mutated", remote_command="mutated", interactive=False)
        )

        # Original should be unchanged
        assert len(codespace.ssh_calls) == 1
        assert codespace.ssh_calls[0].gh_name == "cs-test"
