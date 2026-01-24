"""Validate plan content structure and quality.

This exec command validates that plan content meets minimum requirements
for structure and length. It accepts plan content via stdin or a file path.

Usage:
    echo "$plan" | erk exec validate-plan-content
    erk exec validate-plan-content --plan-file path/to/plan.md

Output:
    JSON with validation status and details

Exit Codes:
    0: Success (always - check JSON for validation result)

Examples:
    $ echo "# My Plan\n\n- Step 1\n- Step 2" | erk exec validate-plan-content
    {"valid": true, "error": null, "details": {"length": 29, "has_headers": true,
    "has_lists": true}}

    $ echo "too short" | erk exec validate-plan-content
    {"valid": false, "error": "Plan too short (9 characters, minimum 100)",
    "details": {"length": 9, "has_headers": false, "has_lists": false}}

    $ erk exec validate-plan-content --plan-file ./plan.md
    {"valid": true, "error": null, "details": {"length": 150, "has_headers": true,
    "has_lists": true}}
"""

import json
import sys
from pathlib import Path

import click


def _validate_plan_content(content: str) -> tuple[bool, str | None, dict[str, bool | int]]:
    """Validate plan content meets minimum requirements.

    Args:
        content: Plan content as string

    Returns:
        Tuple of (valid, error_message, details_dict)
        - valid: True if plan passes all checks
        - error_message: None if valid, descriptive error if invalid
        - details_dict: Dict with length, has_headers, has_lists
    """
    # Strip whitespace for validation
    content_stripped = content.strip()
    length = len(content_stripped)

    # Check for structural elements
    has_headers = any(line.startswith("#") for line in content_stripped.split("\n"))
    has_lists = any(
        line.strip().startswith(("-", "*", "+"))
        or (line.strip() and line.strip()[0].isdigit() and ". " in line)
        for line in content_stripped.split("\n")
    )

    details = {
        "length": length,
        "has_headers": has_headers,
        "has_lists": has_lists,
    }

    # Validation checks
    if not content_stripped:
        return False, "Plan is empty or contains only whitespace", details

    if length < 100:
        return False, f"Plan too short ({length} characters, minimum 100)", details

    if not has_headers and not has_lists:
        return (
            False,
            "Plan lacks structure (no headers or lists found)",
            details,
        )

    return True, None, details


@click.command(name="validate-plan-content")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to plan file. If not provided, reads from stdin.",
)
def validate_plan_content(*, plan_file: Path | None) -> None:
    """Validate plan content from file or stdin.

    Reads plan content from --plan-file or stdin and validates:
    - Minimum 100 characters
    - Contains structural elements (headers OR lists)
    - Not empty/whitespace only

    Outputs JSON with validation result and details.
    """
    if plan_file:
        content = plan_file.read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()
    valid, error, details = _validate_plan_content(content)

    result = {
        "valid": valid,
        "error": error,
        "details": details,
    }

    click.echo(json.dumps(result))
