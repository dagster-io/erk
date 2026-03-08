"""Base error class for agent-optimized CLI commands."""

import click


class AgentCliError(click.ClickException):
    """Exception with error_type for JSON serialization by @json_command."""

    def __init__(self, message: str, *, error_type: str) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
