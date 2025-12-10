#!/usr/bin/env python3
"""Safely remove .worker-impl directory.

This command removes the .worker-impl directory if it exists, with validation.
Replaces duplicated rm -rf .worker-impl patterns in workflows.

Usage:
    erk kit exec erk clean-worker-impl

Output:
    JSON object with success status and whether directory was removed

Exit Codes:
    0: Success (directory removed or did not exist)
    1: Error (removal failed)

Examples:
    $ erk kit exec erk clean-worker-impl
    {
      "success": true,
      "removed": true
    }

    $ erk kit exec erk clean-worker-impl  # When directory doesn't exist
    {
      "success": true,
      "removed": false,
      "message": "Directory did not exist"
    }
"""

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from dot_agent_kit.context_helpers import require_cwd


@dataclass
class CleanSuccess:
    """Success result when directory was removed."""

    success: bool
    removed: bool


@dataclass
class CleanSkipped:
    """Success result when directory did not exist."""

    success: bool
    removed: bool
    message: str


@dataclass
class CleanError:
    """Error result when removal fails."""

    success: bool
    error: Literal["removal_failed", "permission_denied"]
    message: str


def _clean_worker_impl_impl(cwd: Path) -> CleanSuccess | CleanSkipped | CleanError:
    """Remove .worker-impl directory if it exists.

    Args:
        cwd: Current working directory (directory containing .worker-impl)

    Returns:
        CleanSuccess if removed, CleanSkipped if didn't exist, CleanError on failure
    """
    worker_impl_dir = cwd / ".worker-impl"

    # Check if directory exists (LBYL)
    if not worker_impl_dir.exists():
        return CleanSkipped(
            success=True,
            removed=False,
            message="Directory did not exist",
        )

    # Remove the directory
    shutil.rmtree(worker_impl_dir)

    return CleanSuccess(
        success=True,
        removed=True,
    )


@click.command(name="clean-worker-impl")
@click.pass_context
def clean_worker_impl(ctx: click.Context) -> None:
    """Remove .worker-impl directory if it exists.

    Safely removes the .worker-impl directory from the current working
    directory. Returns success even if directory doesn't exist.
    """
    cwd = require_cwd(ctx)

    result = _clean_worker_impl_impl(cwd)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, CleanError):
        raise SystemExit(1)
