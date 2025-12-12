#!/usr/bin/env python3
"""Create .impl/run-info.json with workflow run metadata.

This command writes workflow run information to a JSON file that can be
used by other tools to track the current GitHub Actions run context.

This replaces bash-based JSON creation in GitHub Actions workflows:
```bash
echo "{\"run_id\": \"$RUN_ID\", \"run_url\": \"$RUN_URL\"}" > .impl/run-info.json
```

Usage:
    dot-agent run erk create-impl-run-info \\
        --run-id 12345 \\
        --run-url https://github.com/owner/repo/actions/runs/12345

Output:
    JSON object with success status

Exit Codes:
    0: Success (run-info.json created)
    1: Error (directory doesn't exist or write failed)

Examples:
    $ dot-agent run erk create-impl-run-info --run-id 12345 --run-url https://github.com/owner/repo/actions/runs/12345
    {
      "success": true,
      "path": "/path/to/repo/.impl/run-info.json"
    }

    $ dot-agent run erk create-impl-run-info --run-id 12345 --run-url https://...
    # when .impl/ doesn't exist
    {
      "success": false,
      "error": "directory_not_found",
      "message": "Directory .impl does not exist. Create it first with 'mkdir -p .impl'"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import require_cwd


@dataclass
class RunInfoCreated:
    """Success result with path to created file."""

    success: bool
    path: str


@dataclass
class RunInfoError:
    """Error result when run-info.json cannot be created."""

    success: bool
    error: Literal["directory_not_found", "write_failed"]
    message: str


def _create_impl_run_info_impl(
    cwd: Path, run_id: str, run_url: str
) -> RunInfoCreated | RunInfoError:
    """Create .impl/run-info.json with workflow metadata.

    Args:
        cwd: Current working directory
        run_id: GitHub Actions run ID
        run_url: Full URL to the workflow run

    Returns:
        RunInfoCreated on success, RunInfoError if directory doesn't exist or write fails
    """
    impl_dir = cwd / ".impl"

    # LBYL: Check if .impl directory exists
    if not impl_dir.exists():
        return RunInfoError(
            success=False,
            error="directory_not_found",
            message="Directory .impl does not exist. Create it first with 'mkdir -p .impl'",
        )

    run_info_path = impl_dir / "run-info.json"

    # Write the run info JSON
    run_info = {"run_id": run_id, "run_url": run_url}
    run_info_path.write_text(json.dumps(run_info, indent=2), encoding="utf-8")

    return RunInfoCreated(success=True, path=str(run_info_path))


@click.command(name="create-impl-run-info")
@click.option(
    "--run-id",
    required=True,
    help="GitHub Actions run ID",
)
@click.option(
    "--run-url",
    required=True,
    help="Full URL to the workflow run",
)
@click.pass_context
def create_impl_run_info(ctx: click.Context, run_id: str, run_url: str) -> None:
    """Create .impl/run-info.json with workflow run metadata.

    Writes run ID and URL to a JSON file for tracking the current workflow context.
    Requires the .impl directory to already exist.
    """
    cwd = require_cwd(ctx)

    result = _create_impl_run_info_impl(cwd, run_id, run_url)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if creation failed
    if isinstance(result, RunInfoError):
        raise SystemExit(1)
