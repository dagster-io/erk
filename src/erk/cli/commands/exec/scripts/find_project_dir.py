#!/usr/bin/env python3
"""Find Claude Code project directory for a given filesystem path.

This command provides deterministic mapping between filesystem paths and
Claude Code project directories in ~/.claude/projects/.

Claude Code encodes filesystem paths using a simple rule:
- Replace "/" with "-"
- Replace "." with "-"

Examples:
    /Users/foo/bar → -Users-foo-bar
    /Users/foo/.config/bar → -Users-foo--config-bar (double dash for dot)

This command returns the project directory path and metadata about session logs.

Usage:
    # Find project directory for current directory
    erk exec find-project-dir

    # Find project directory for specific path
    erk exec find-project-dir --path /some/path

    # JSON output for scripting
    erk exec find-project-dir --json

Output:
    JSON object with success status and project information

Exit Codes:
    0: Success (project directory found)
    1: Error (project directory not found or other error)

Examples:
    $ erk exec find-project-dir
    {
      "success": true,
      "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-erk",
      "cwd": "/Users/foo/code/erk",
      "encoded_path": "-Users-foo-code-erk",
      "session_logs": ["abc123.jsonl", "agent-17cfd3f4.jsonl"],
      "latest_session_id": "abc123"
    }

    $ erk exec find-project-dir --path /nonexistent
    {
      "success": false,
      "error": "Project directory not found",
      "help": "No Claude Code project found for /nonexistent",
      "context": {
        "path": "/nonexistent",
        "encoded_path": "-nonexistent"
      }
    }
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_claude_installation


@dataclass(frozen=True)
class ProjectInfo:
    """Success result with project information."""

    success: bool
    project_dir: str
    cwd: str
    encoded_path: str
    session_logs: list[str]
    latest_session_id: str | None


@dataclass(frozen=True)
class ProjectError:
    """Error result when project directory not found."""

    success: bool
    error: str
    help: str
    context: dict[str, str]


@click.command(name="find-project-dir")
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to find project for (defaults to current directory)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def find_project_dir(ctx: click.Context, path: Path | None, json_output: bool) -> None:
    """Find Claude Code project directory for a filesystem path.

    This command maps filesystem paths to Claude Code project directories
    in ~/.claude/projects/ using deterministic encoding rules.
    """
    claude_installation = require_claude_installation(ctx)

    # Default to current directory if no path specified
    if path is None:
        path = Path(os.getcwd())

    # Check if projects directory exists
    projects_dir = claude_installation.get_projects_dir_path()
    if not claude_installation.projects_dir_exists():
        result = ProjectError(
            success=False,
            error="Claude Code projects directory not found",
            help="~/.claude/projects/ does not exist. Is Claude Code installed?",
            context={
                "path": str(path),
                "projects_dir": str(projects_dir),
            },
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1)

    # Use gateway to find project info
    project_info = claude_installation.find_project_info(path)

    if project_info is None:
        encoded_path = claude_installation.encode_path_to_project_folder(path)
        result = ProjectError(
            success=False,
            error="Project directory not found",
            help=f"No Claude Code project found for {path}",
            context={
                "path": str(path),
                "encoded_path": encoded_path,
                "expected_dir": str(projects_dir / encoded_path),
            },
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1)

    project_dir, session_logs, latest_session_id = project_info
    result = ProjectInfo(
        success=True,
        project_dir=str(project_dir),
        cwd=str(path),
        encoded_path=claude_installation.encode_path_to_project_folder(path),
        session_logs=session_logs,
        latest_session_id=latest_session_id,
    )

    # Always output JSON (the --json flag is for future extensibility)
    click.echo(json.dumps(asdict(result), indent=2))
