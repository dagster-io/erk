#!/usr/bin/env python3
"""Set GitHub Actions output variable from JSON input.

This command parses JSON from stdin or argument and writes key=value
to `$GITHUB_OUTPUT`. Replaces manual jq parsing in workflow files.

Usage:
    echo '{"trunk_branch": "main"}' | \\
        erk kit exec erk set-gha-output --key trunk_branch --jq-path '.trunk_branch'
    erk kit exec erk set-gha-output --key trunk_branch --value "main"

Output:
    JSON object with success status

Exit Codes:
    0: Success (output written)
    1: Error (JSON parse error, missing key, or GITHUB_OUTPUT not set)

Examples:
    $ echo '{"trunk_branch": "main"}' | \\
        erk kit exec erk set-gha-output --key trunk_branch --jq-path '.trunk_branch'
    {
      "success": true,
      "key": "trunk_branch",
      "value": "main"
    }
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click


@dataclass
class SetOutputSuccess:
    """Success result when output is written."""

    success: bool
    key: str
    value: str


@dataclass
class SetOutputError:
    """Error result when output cannot be written."""

    success: bool
    error: Literal["json_parse_error", "key_not_found", "github_output_not_set", "invalid_jq_path"]
    message: str


def _extract_value_from_json(data: dict, jq_path: str) -> str | None:
    """Extract value from JSON data using simple jq-style path.

    Supports basic paths like '.key', '.nested.key', '.array[0]'.

    Args:
        data: Parsed JSON data as dict
        jq_path: Path to extract (e.g., '.trunk_branch', '.data.value')

    Returns:
        Extracted value as string, or None if not found
    """
    # Remove leading dot
    path = jq_path.lstrip(".")
    if not path:
        return json.dumps(data) if isinstance(data, dict | list) else str(data)

    current = data
    for part in path.split("."):
        if not part:
            continue

        # Handle array index notation like 'items[0]'
        if "[" in part and part.endswith("]"):
            bracket_idx = part.index("[")
            key = part[:bracket_idx]
            idx_str = part[bracket_idx + 1 : -1]

            if key:
                if not isinstance(current, dict) or key not in current:
                    return None
                current = current[key]

            if not isinstance(current, list):
                return None
            try:
                idx = int(idx_str)
                if idx < 0 or idx >= len(current):
                    return None
                current = current[idx]
            except ValueError:
                return None
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]

    # Convert to string
    if isinstance(current, str):
        return current
    if isinstance(current, bool):
        return "true" if current else "false"
    if isinstance(current, int | float):
        return str(current)
    if current is None:
        return ""
    # For complex types, return JSON representation
    return json.dumps(current)


def _set_gha_output_impl(
    key: str,
    value: str | None,
    jq_path: str | None,
    json_input: str | None,
    github_output_path: str | None,
) -> SetOutputSuccess | SetOutputError:
    """Set GitHub Actions output variable.

    Args:
        key: Output variable name
        value: Direct value to set (mutually exclusive with jq_path)
        jq_path: Path to extract from JSON input
        json_input: JSON string to parse (required if jq_path is set)
        github_output_path: Path to GITHUB_OUTPUT file (from env)

    Returns:
        SetOutputSuccess on success, SetOutputError on failure
    """
    # Determine the value to write
    output_value: str

    if value is not None:
        # Direct value provided
        output_value = value
    elif jq_path is not None:
        # Extract from JSON
        if json_input is None:
            return SetOutputError(
                success=False,
                error="json_parse_error",
                message="No JSON input provided (expected stdin)",
            )

        try:
            data = json.loads(json_input)
        except json.JSONDecodeError as e:
            return SetOutputError(
                success=False,
                error="json_parse_error",
                message=f"Failed to parse JSON: {e}",
            )

        extracted = _extract_value_from_json(data, jq_path)
        if extracted is None:
            return SetOutputError(
                success=False,
                error="key_not_found",
                message=f"Path '{jq_path}' not found in JSON",
            )
        output_value = extracted
    else:
        return SetOutputError(
            success=False,
            error="invalid_jq_path",
            message="Either --value or --jq-path must be provided",
        )

    # Write to GITHUB_OUTPUT
    if github_output_path is None:
        return SetOutputError(
            success=False,
            error="github_output_not_set",
            message="GITHUB_OUTPUT environment variable not set",
        )

    output_file = Path(github_output_path)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{key}={output_value}\n")

    return SetOutputSuccess(
        success=True,
        key=key,
        value=output_value,
    )


@click.command(name="set-gha-output")
@click.option("--key", required=True, help="Output variable name")
@click.option("--value", default=None, help="Direct value to set")
@click.option("--jq-path", default=None, help="Path to extract from JSON (e.g., '.trunk_branch')")
@click.pass_context
def set_gha_output(ctx: click.Context, key: str, value: str | None, jq_path: str | None) -> None:
    """Set GitHub Actions output variable from JSON or direct value.

    Reads JSON from stdin when using --jq-path, or uses --value directly.
    Writes to $GITHUB_OUTPUT in the format: key=value
    """
    # Read from stdin if jq_path is provided
    json_input = None
    if jq_path is not None:
        if not sys.stdin.isatty():
            json_input = sys.stdin.read()

    github_output_path = os.environ.get("GITHUB_OUTPUT")

    result = _set_gha_output_impl(
        key=key,
        value=value,
        jq_path=jq_path,
        json_input=json_input,
        github_output_path=github_output_path,
    )

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, SetOutputError):
        raise SystemExit(1)
