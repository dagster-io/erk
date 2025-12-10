#!/usr/bin/env python3
"""Write content to a file for use with gh CLI.

This command writes content to a file, avoiding heredoc issues in bash
that can occur with special characters in PR body content.

Usage:
    erk kit exec erk write-pr-body-file --content "$BODY" --output pr_body.md

Output:
    JSON object with success status

Exit Codes:
    0: Success (file written)
    1: Error (write failed)

Examples:
    $ erk kit exec erk write-pr-body-file --content "## Summary\\n\\nDetails..." --output pr_body.md
    {
      "success": true,
      "file": "pr_body.md"
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from dot_agent_kit.context_helpers import require_cwd


@dataclass
class WriteSuccess:
    """Success result when file was written."""

    success: bool
    file: str


@dataclass
class WriteError:
    """Error result when write fails."""

    success: bool
    error: Literal["write_failed"]
    message: str


def _write_pr_body_file_impl(
    cwd: Path,
    content: str,
    output: str,
) -> WriteSuccess | WriteError:
    """Write content to a file.

    Args:
        cwd: Current working directory
        content: Content to write
        output: Output file path (relative to cwd)

    Returns:
        WriteSuccess on success, WriteError on failure
    """
    output_path = cwd / output

    # Ensure parent directory exists (LBYL)
    parent = output_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    output_path.write_text(content, encoding="utf-8")

    return WriteSuccess(
        success=True,
        file=output,
    )


@click.command(name="write-pr-body-file")
@click.option("--content", required=True, help="Content to write to file")
@click.option("--output", required=True, help="Output file path")
@click.pass_context
def write_pr_body_file(
    ctx: click.Context,
    content: str,
    output: str,
) -> None:
    """Write content to a file.

    Writes the provided content to a file, handling special characters
    that can cause issues with bash heredocs. Useful for creating
    temporary files for gh pr edit --body-file.
    """
    cwd = require_cwd(ctx)

    result = _write_pr_body_file_impl(cwd, content, output)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, WriteError):
        raise SystemExit(1)
