#!/usr/bin/env python3
"""Create .impl/run-info.json with workflow run metadata.

This command creates a validated JSON file with run metadata.
Replaces heredoc JSON creation patterns in workflows.

Usage:
    erk kit exec erk create-impl-run-info \\
        --run-id "12345" --run-url "https://..." --output-dir .impl

Output:
    JSON object with success status

Exit Codes:
    0: Success (file created)
    1: Error (directory doesn't exist or write failed)

Examples:
    $ erk kit exec erk create-impl-run-info \\
        --run-id "12345" --run-url "https://github.com/..." --output-dir .impl
    {
      "success": true,
      "file": ".impl/run-info.json"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from dot_agent_kit.context_helpers import require_cwd


@dataclass
class CreateSuccess:
    """Success result when file was created."""

    success: bool
    file: str


@dataclass
class CreateError:
    """Error result when creation fails."""

    success: bool
    error: Literal["directory_not_found", "write_failed"]
    message: str


def _create_impl_run_info_impl(
    cwd: Path,
    run_id: str,
    run_url: str,
    output_dir: str,
) -> CreateSuccess | CreateError:
    """Create run-info.json file with workflow metadata.

    Args:
        cwd: Current working directory
        run_id: GitHub Actions run ID
        run_url: GitHub Actions run URL
        output_dir: Directory to create file in (relative to cwd)

    Returns:
        CreateSuccess on success, CreateError on failure
    """
    output_path = cwd / output_dir

    # Check if directory exists (LBYL)
    if not output_path.exists():
        return CreateError(
            success=False,
            error="directory_not_found",
            message=f"Directory '{output_dir}' does not exist",
        )

    # Create run-info.json
    run_info = {
        "run_id": run_id,
        "run_url": run_url,
    }

    output_file = output_path / "run-info.json"
    output_file.write_text(json.dumps(run_info, indent=2), encoding="utf-8")

    return CreateSuccess(
        success=True,
        file=str(output_dir) + "/run-info.json",
    )


@click.command(name="create-impl-run-info")
@click.option("--run-id", required=True, help="GitHub Actions run ID")
@click.option("--run-url", required=True, help="GitHub Actions run URL")
@click.option("--output-dir", required=True, help="Directory to create file in")
@click.pass_context
def create_impl_run_info(
    ctx: click.Context,
    run_id: str,
    run_url: str,
    output_dir: str,
) -> None:
    """Create run-info.json with workflow run metadata.

    Creates a JSON file containing the GitHub Actions run ID and URL
    for tracking implementation workflow runs.
    """
    cwd = require_cwd(ctx)

    result = _create_impl_run_info_impl(cwd, run_id, run_url, output_dir)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, CreateError):
        raise SystemExit(1)
