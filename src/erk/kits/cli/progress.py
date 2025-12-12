"""Progress indicators and status displays for CLI operations."""

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.status import Status

# Console instance for user-facing progress indicators
# Uses stderr to match user_output() behavior and avoid polluting stdout
_console = Console(stderr=True)


@contextmanager
def command_status(command_name: str) -> Iterator[Status]:
    """Display animated status spinner during command execution.

    Args:
        command_name: Name of the command being executed (without / prefix)

    Yields:
        Status object that can be updated during execution

    Example:
        with command_status("ensure-ci"):
            # Long-running operation
            run_command()
    """
    status_message = f"Executing command: /{command_name}..."
    with _console.status(status_message, spinner="dots") as status:
        yield status
