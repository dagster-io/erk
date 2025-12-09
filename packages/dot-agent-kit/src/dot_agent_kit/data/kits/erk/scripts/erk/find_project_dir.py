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
    dot-agent run erk find-project-dir

    # Find project directory for specific path
    dot-agent run erk find-project-dir --path /some/path

    # JSON output for scripting
    dot-agent run erk find-project-dir --json

Output:
    JSON object with success status and project information

Exit Codes:
    0: Success (project directory found)
    1: Error (project directory not found or other error)

Examples:
    $ dot-agent run erk find-project-dir
    {
      "success": true,
      "project_dir": "/Users/foo/.claude/projects/-Users-foo-code-erk",
      "cwd": "/Users/foo/code/erk",
      "encoded_path": "-Users-foo-code-erk",
      "session_logs": ["abc123.jsonl", "agent-17cfd3f4.jsonl"],
      "latest_session_id": "abc123"
    }

    $ dot-agent run erk find-project-dir --path /nonexistent
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


@dataclass
class ProjectInfo:
    """Success result with project information."""

    success: bool
    project_dir: str
    cwd: str
    encoded_path: str
    session_logs: list[str]
    latest_session_id: str | None


@dataclass
class ProjectError:
    """Error result when project directory not found."""

    success: bool
    error: str
    help: str
    context: dict[str, str]


def encode_path_to_project_folder(path: Path) -> str:
    """Encode filesystem path to Claude Code project folder name.

    Claude Code uses a simple encoding scheme:
    - Replace "/" with "-"
    - Replace "." with "-"

    This creates deterministic folder names in ~/.claude/projects/.

    Args:
        path: Filesystem path to encode

    Returns:
        Encoded path suitable for project folder name

    Examples:
        >>> encode_path_to_project_folder(Path("/Users/foo/bar"))
        '-Users-foo-bar'
        >>> encode_path_to_project_folder(Path("/Users/foo/.config"))
        '-Users-foo--config'
    """
    return str(path).replace("/", "-").replace(".", "-")


def find_project_info(path: Path) -> ProjectInfo | ProjectError:
    """Find Claude Code project directory and metadata for given path.

    Args:
        path: Filesystem path to find project for

    Returns:
        ProjectInfo on success, ProjectError if not found
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return ProjectError(
            success=False,
            error="Claude Code projects directory not found",
            help="~/.claude/projects/ does not exist. Is Claude Code installed?",
            context={
                "path": str(path),
                "projects_dir": str(projects_dir),
            },
        )

    # Encode path and find project directory
    encoded_path = encode_path_to_project_folder(path)
    project_dir = projects_dir / encoded_path

    if not project_dir.exists():
        return ProjectError(
            success=False,
            error="Project directory not found",
            help=f"No Claude Code project found for {path}",
            context={
                "path": str(path),
                "encoded_path": encoded_path,
                "expected_dir": str(project_dir),
            },
        )

    # Find all session logs (main sessions and agent logs)
    session_logs = []
    latest_session: tuple[str, float] | None = None

    for log_file in project_dir.iterdir():
        if log_file.is_file() and log_file.suffix == ".jsonl":
            session_logs.append(log_file.name)

            # Track latest main session (not agent logs)
            if not log_file.name.startswith("agent-"):
                mtime = log_file.stat().st_mtime
                if latest_session is None or mtime > latest_session[1]:
                    # Extract session ID (filename without .jsonl)
                    session_id = log_file.stem
                    latest_session = (session_id, mtime)

    # Sort logs for consistent output
    session_logs.sort()

    return ProjectInfo(
        success=True,
        project_dir=str(project_dir),
        cwd=str(path),
        encoded_path=encoded_path,
        session_logs=session_logs,
        latest_session_id=latest_session[0] if latest_session else None,
    )


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
def find_project_dir(path: Path | None, json_output: bool) -> None:
    """Find Claude Code project directory for a filesystem path.

    This command maps filesystem paths to Claude Code project directories
    in ~/.claude/projects/ using deterministic encoding rules.
    """
    # Default to current directory if no path specified
    if path is None:
        path = Path(os.getcwd())

    # Find project information
    result = find_project_info(path)

    # Always output JSON (the --json flag is for future extensibility)
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if not found
    if isinstance(result, ProjectError):
        raise SystemExit(1)
