"""Validate plan content structure and quality.

This kit CLI command validates that plan content meets minimum requirements
for structure and length. It accepts plan content via stdin.

Usage:
    echo "$plan" | dot-agent kit-command erk validate-plan-content

Output:
    JSON with validation status and details

Exit Codes:
    0: Success (always - check JSON for validation result)

Examples:
    $ echo "# My Plan\n\n- Step 1\n- Step 2" | dot-agent kit-command erk validate-plan-content
    {"valid": true, "error": null, "details": {"length": 29, "has_headers": true,
    "has_lists": true}}

    $ echo "too short" | dot-agent kit-command erk validate-plan-content
    {"valid": false, "error": "Plan too short (9 characters, minimum 100)",
    "details": {"length": 9, "has_headers": false, "has_lists": false}}
"""

import json
import sys

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
def validate_plan_content() -> None:
    """Validate plan content from stdin.

    Reads plan content from stdin and validates:
    - Minimum 100 characters
    - Contains structural elements (headers OR lists)
    - Not empty/whitespace only

    Outputs JSON with validation result and details.
    """
    content = sys.stdin.read()
    valid, error, details = _validate_plan_content(content)

    result = {
        "valid": valid,
        "error": error,
        "details": details,
    }

    click.echo(json.dumps(result))
