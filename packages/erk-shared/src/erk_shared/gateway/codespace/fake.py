"""Fake Codespace implementation for testing.

FakeCodespace is an in-memory implementation that tracks SSH calls
without actually executing remote commands, enabling fast and deterministic tests.
"""

from dataclasses import dataclass
from typing import NoReturn

from erk_shared.gateway.codespace.abc import Codespace


@dataclass(frozen=True)
class SSHCall:
    """Record of an SSH call for test assertions.

    Attributes:
        gh_name: GitHub codespace name that was targeted
        remote_command: Command that was executed
        interactive: Whether this was an interactive (exec) or non-interactive (run) call
    """

    gh_name: str
    remote_command: str
    interactive: bool


class FakeCodespace(Codespace):
    """In-memory fake implementation that tracks SSH calls.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(
        self,
        *,
        run_exit_code: int = 0,
    ) -> None:
        """Create FakeCodespace with configurable behavior.

        Args:
            run_exit_code: Exit code to return from run_ssh_command.
                Defaults to 0 (success) for most tests.
        """
        self._run_exit_code = run_exit_code
        self._ssh_calls: list[SSHCall] = []
        self._exec_called = False

    @property
    def ssh_calls(self) -> list[SSHCall]:
        """Get the list of SSH calls that were made.

        Returns a copy of the list to prevent external mutation.

        This property is for test assertions only.
        """
        return list(self._ssh_calls)

    @property
    def exec_called(self) -> bool:
        """Check if exec_ssh_interactive was called.

        This property is for test assertions only.
        """
        return self._exec_called

    @property
    def last_call(self) -> SSHCall | None:
        """Get the last SSH call, or None if no calls were made.

        This property is for test assertions only.
        """
        if not self._ssh_calls:
            return None
        return self._ssh_calls[-1]

    def exec_ssh_interactive(self, gh_name: str, remote_command: str) -> NoReturn:
        """Track interactive SSH call.

        In production, this replaces the process. In tests, we record the call
        and raise SystemExit to simulate the process ending.

        Args:
            gh_name: GitHub codespace name
            remote_command: Command to execute

        Raises:
            SystemExit: Always raised to simulate process replacement
        """
        self._exec_called = True
        self._ssh_calls.append(
            SSHCall(gh_name=gh_name, remote_command=remote_command, interactive=True)
        )
        # Simulate process replacement by exiting
        raise SystemExit(0)

    def run_ssh_command(self, gh_name: str, remote_command: str) -> int:
        """Track non-interactive SSH call and return configured exit code.

        Args:
            gh_name: GitHub codespace name
            remote_command: Command to execute

        Returns:
            The configured run_exit_code value
        """
        self._ssh_calls.append(
            SSHCall(gh_name=gh_name, remote_command=remote_command, interactive=False)
        )
        return self._run_exit_code
