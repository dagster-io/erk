"""Mark one or more steps as completed or incomplete in progress.md.

This kit CLI command updates the YAML frontmatter in .impl/progress.md to mark
steps as completed or incomplete, then regenerates the checkboxes.

Supports marking multiple steps in a single invocation to avoid race conditions
when Claude runs parallel commands.

Usage:
    dot-agent run erk mark-step STEP_NUM [STEP_NUM ...]
    dot-agent run erk mark-step STEP_NUM --incomplete
    dot-agent run erk mark-step STEP_NUM --json

Output:
    JSON format: {"success": true, "step_nums": [N, ...], "completed": true,
                  "total_completed": X, "total_steps": Y}
    Human format: ✓ Step N: <description>\n              Progress: X/Y

Exit Codes:
    0: Success
    1: Error (missing file, invalid step number, malformed YAML)

Examples:
    $ dot-agent run erk mark-step 5
    ✓ Step 5: Implement feature X
    Progress: 5/10

    $ dot-agent run erk mark-step 1 2 3
    ✓ Step 1: First step
    ✓ Step 2: Second step
    ✓ Step 3: Third step
    Progress: 3/10

    $ dot-agent run erk mark-step 5 --json
    {"success": true, "step_nums": [5], "completed": true, "total_completed": 5, "total_steps": 10}

    $ dot-agent run erk mark-step 5 --incomplete
    ○ Step 5: Implement feature X
    Progress: 4/10
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


def _parse_progress_file(progress_file: Path) -> tuple[dict[str, Any], str]:
    """Parse progress.md file and extract metadata and body.

    Args:
        progress_file: Path to progress.md

    Returns:
        Tuple of (metadata dict, body content)

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

    if not isinstance(metadata["steps"], list):
        _error("'steps' field must be an array")

    return metadata, post.content


def _validate_step_nums(
    step_nums: tuple[int, ...],
    total_steps: int,
) -> None:
    """Validate all step numbers are in range.

    Args:
        step_nums: Tuple of step numbers (1-indexed)
        total_steps: Total number of steps in the plan

    Raises:
        SystemExit: If any step_num is out of range
    """
    if len(step_nums) == 0:
        _error("At least one step number is required")

    for step_num in step_nums:
        if step_num < 1 or step_num > total_steps:
            _error(f"Step number {step_num} out of range (1-{total_steps})")


def _update_step_status(
    metadata: dict[str, Any],
    step_num: int,
    completed: bool,
) -> None:
    """Update step status in metadata.

    Args:
        metadata: Progress metadata dict (modified in place)
        step_num: Step number (1-indexed), must be pre-validated
        completed: True to mark complete, False for incomplete

    Note:
        Does NOT validate step_num - caller must validate first.
        Does NOT recalculate completed_steps - caller must do this after all updates.
    """
    steps = metadata["steps"]

    # Update step status (convert to 0-indexed)
    steps[step_num - 1]["completed"] = completed


def _recalculate_completed_steps(metadata: dict[str, Any]) -> None:
    """Recalculate completed_steps count from steps array.

    Args:
        metadata: Progress metadata dict (modified in place)
    """
    steps = metadata["steps"]
    completed_count = sum(1 for step in steps if step["completed"])
    metadata["completed_steps"] = completed_count


def _regenerate_checkboxes(steps: list[dict[str, Any]]) -> str:
    """Regenerate checkbox markdown from steps array.

    Args:
        steps: List of step dicts with 'text' and 'completed' fields

    Returns:
        Markdown body with checkboxes
    """
    lines = ["# Progress Tracking\n"]

    for step in steps:
        checkbox = "[x]" if step["completed"] else "[ ]"
        lines.append(f"- {checkbox} {step['text']}")

    lines.append("")  # Trailing newline
    return "\n".join(lines)


def _write_progress_file(
    progress_file: Path,
    metadata: dict[str, Any],
) -> None:
    """Write updated progress.md file with new metadata and regenerated checkboxes.

    Args:
        progress_file: Path to progress.md
        metadata: Updated metadata dict
    """
    # Regenerate body from steps array
    body = _regenerate_checkboxes(metadata["steps"])

    # Create frontmatter post and write atomically
    post = frontmatter.Post(body, **metadata)
    content = frontmatter.dumps(post)
    progress_file.write_text(content, encoding="utf-8")


@click.command(name="mark-step")
@click.argument("step_nums", type=int, nargs=-1)
@click.option(
    "--completed/--incomplete",
    default=True,
    help="Mark as completed (default) or incomplete",
)
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
def mark_step(step_nums: tuple[int, ...], completed: bool, output_json: bool) -> None:
    """Mark one or more steps as completed or incomplete in progress.md.

    Updates the YAML frontmatter to mark STEP_NUMS as completed/incomplete,
    recalculates the completed_steps count, and regenerates checkboxes.

    Supports multiple step numbers to avoid race conditions from parallel execution.

    STEP_NUMS: One or more step numbers to mark (1-indexed)
    """
    progress_file = _validate_progress_file()
    metadata, _ = _parse_progress_file(progress_file)

    # Validate all steps first (fail fast before any modifications)
    _validate_step_nums(step_nums, metadata["total_steps"])

    # Update all steps in a single read-modify-write cycle
    for step_num in step_nums:
        _update_step_status(metadata, step_num, completed)

    # Recalculate completed count once after all updates
    _recalculate_completed_steps(metadata)

    _write_progress_file(progress_file, metadata)

    # Output result
    if output_json:
        result = {
            "success": True,
            "step_nums": list(step_nums),
            "completed": completed,
            "total_completed": metadata["completed_steps"],
            "total_steps": metadata["total_steps"],
        }
        click.echo(json.dumps(result))
    else:
        # Output each marked step
        status_icon = "✓" if completed else "○"
        for step_num in step_nums:
            step_text = metadata["steps"][step_num - 1]["text"]
            click.echo(f"{status_icon} Step {step_num}: {step_text}")
        click.echo(f"Progress: {metadata['completed_steps']}/{metadata['total_steps']}")
