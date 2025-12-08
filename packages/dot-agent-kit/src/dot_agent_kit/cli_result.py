"""CLI result handling: exit on error with JSON output.

This module provides exit_with_error() for kit CLI commands that need to
output JSON errors and exit gracefully.

Kit CLI commands exit with code 0 and JSON output (different from erk CLI which
uses styled output and exit code 1). This module provides the kit-specific
exit handling.

Usage:
    from dot_agent_kit.cli_result import exit_with_error
    from dot_agent_kit.non_ideal_state import GitHubChecks, BranchDetectionFailed

    # Check result and exit with JSON on error
    result = GitHubChecks.branch(get_current_branch(ctx))
    if isinstance(result, BranchDetectionFailed):
        exit_with_error(result.error_type, result.message)
    branch = result  # Type narrowed to str
"""

import json
from typing import NoReturn

import click


def exit_with_error(error_type: str, message: str) -> NoReturn:
    """Output JSON error and exit with code 0.

    Kit CLI commands exit with 0 even on error to support || true patterns
    in shell scripts. The error is communicated via JSON output.

    Args:
        error_type: Machine-readable error category (e.g., "no_pr_for_branch")
        message: Human-readable error message

    Raises:
        SystemExit: Always exits with code 0 after printing JSON
    """
    error_json = json.dumps(
        {"success": False, "error_type": error_type, "message": message},
        indent=2,
    )
    click.echo(error_json)
    raise SystemExit(0)
