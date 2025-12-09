"""Query progress information from progress.md.

This kit CLI command reads the YAML frontmatter from .impl/progress.md and
returns progress information including completion status and steps array.

Usage:
    dot-agent run erk get-progress
    dot-agent run erk get-progress --json

Output:
    JSON format: {"completed_steps": X, "total_steps": Y, "percentage": Z, "steps": [...]}
    Human format: Progress summary with checkbox list

Exit Codes:
    0: Success
    1: Error (missing file, malformed YAML)

Examples:
    $ dot-agent run erk get-progress
    Progress: 5/10 (50%)

    - [x] 1. Implement feature A
    - [x] 2. Add tests for A
    - [ ] 3. Implement feature B
    ...

    $ dot-agent run erk get-progress --json
    {
      "completed_steps": 5,
      "total_steps": 10,
      "percentage": 50,
      "steps": [
        {"text": "1. Implement feature A", "completed": true},
        {"text": "2. Add tests for A", "completed": true},
        {"text": "3. Implement feature B", "completed": false},
        ...
      ]
    }
"""

import json
from pathlib import Path
from typing import Any, NoReturn

import click
import frontmatter


def _error(msg: str) -> NoReturn:
    """Output error message and exit with code 1."""
    click.echo(f"❌ Error: {msg}", err=True)
    raise SystemExit(1)


def _validate_progress_file() -> Path:
    """Validate .impl/progress.md exists.

    Returns:
        Path to progress.md

    Raises:
        SystemExit: If validation fails
    """
    progress_file = Path.cwd() / ".impl" / "progress.md"

    if not progress_file.exists():
        _error("No progress.md found in .impl/ folder")

    return progress_file


def _parse_progress_file(progress_file: Path) -> dict[str, Any]:
    """Parse progress.md file and extract metadata.

    Args:
        progress_file: Path to progress.md

    Returns:
        Metadata dict with completed_steps, total_steps, and steps array

    Raises:
        SystemExit: If YAML is malformed or missing required fields
    """
    content = progress_file.read_text(encoding="utf-8")

    # Gracefully handle YAML parsing errors (third-party API exception handling)
    try:
        post = frontmatter.loads(content)
    except Exception as e:
        _error(f"Failed to parse YAML frontmatter: {e}")

    metadata = post.metadata

    # Validate required fields
    if "steps" not in metadata:
        _error("Progress file missing 'steps' array in frontmatter")

    if "total_steps" not in metadata:
        _error("Progress file missing 'total_steps' in frontmatter")

    if "completed_steps" not in metadata:
        _error("Progress file missing 'completed_steps' in frontmatter")

    if not isinstance(metadata["steps"], list):
        _error("'steps' field must be an array")

    return metadata


def _calculate_percentage(completed: int, total: int) -> int:
    """Calculate completion percentage.

    Args:
        completed: Number of completed steps
        total: Total number of steps

    Returns:
        Percentage as integer (0-100)
    """
    if total == 0:
        return 0
    return int((completed / total) * 100)


def _render_human_output(metadata: dict[str, Any]) -> str:
    """Render human-readable progress output.

    Args:
        metadata: Progress metadata dict

    Returns:
        Formatted progress string
    """
    completed = metadata["completed_steps"]
    total = metadata["total_steps"]
    percentage = _calculate_percentage(completed, total)
    steps = metadata["steps"]

    lines = [f"Progress: {completed}/{total} ({percentage}%)\n"]

    for step in steps:
        checkbox = "[x]" if step["completed"] else "[ ]"
        lines.append(f"- {checkbox} {step['text']}")

    return "\n".join(lines)


@click.command(name="get-progress")
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
def get_progress(output_json: bool) -> None:
    """Query progress information from progress.md.

    Reads the YAML frontmatter and returns progress data including
    completed steps count, total steps, percentage, and steps array.
    """
    progress_file = _validate_progress_file()
    metadata = _parse_progress_file(progress_file)

    if output_json:
        completed = metadata["completed_steps"]
        total = metadata["total_steps"]
        percentage = _calculate_percentage(completed, total)

        result = {
            "completed_steps": completed,
            "total_steps": total,
            "percentage": percentage,
            "steps": metadata["steps"],
        }
        click.echo(json.dumps(result, indent=2))
    else:
        output = _render_human_output(metadata)
        click.echo(output)
