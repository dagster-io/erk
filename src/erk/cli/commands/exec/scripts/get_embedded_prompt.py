#!/usr/bin/env python3
"""Get embedded prompt content from bundled prompts.

This command reads prompt files bundled with the erk package and outputs
their content. Useful for GitHub Actions workflows that need prompt content.

Usage:
    erk exec get-embedded-prompt <prompt-name>
    erk exec get-embedded-prompt <prompt-name> --var "key=value" --var-file "key=path"

Output:
    The prompt content (markdown) with variables substituted

Exit Codes:
    0: Success
    1: Prompt not found or substitution error

Examples:
    $ erk exec get-embedded-prompt dignified-python-review
    # Dignified Python Review Prompt
    ...

    $ erk exec get-embedded-prompt ci-autofix \\
        --var "format=failure" \\
        --var "lint=success" \\
        --var-file "ERRORS=/tmp/errors.txt"
"""

import re
from pathlib import Path

import click

from erk.artifacts.sync import get_bundled_github_dir

# Available prompts that can be retrieved
AVAILABLE_PROMPTS = frozenset(
    {
        "ci-autofix",
        "dignified-python-review",
    }
)

# Pattern for {{ KEY }} placeholders
_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*(\w[\w-]*)\s*\}\}")


def _parse_var_assignment(assignment: str) -> tuple[str, str] | None:
    """Parse a KEY=VALUE assignment string.

    Returns (key, value) tuple if valid, None if invalid format.
    """
    if "=" not in assignment:
        return None
    key, _, value = assignment.partition("=")
    key = key.strip()
    if not key:
        return None
    return (key, value)


def _substitute_variables(content: str, variables: dict[str, str]) -> str:
    """Substitute {{ KEY }} placeholders with variable values.

    Raises SystemExit if any placeholder has no matching variable.
    """
    # Find all placeholders in the content
    placeholders = set(_PLACEHOLDER_PATTERN.findall(content))

    # Check for missing variables
    missing = placeholders - set(variables.keys())
    if missing:
        missing_list = ", ".join(sorted(missing))
        click.echo(f"Error: Missing variables for placeholders: {missing_list}", err=True)
        click.echo("Use --var KEY=VALUE or --var-file KEY=PATH to provide values", err=True)
        raise SystemExit(1)

    # Perform substitution
    def replace_placeholder(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return _PLACEHOLDER_PATTERN.sub(replace_placeholder, content)


@click.command(name="get-embedded-prompt")
@click.argument("prompt_name")
@click.option(
    "--var",
    "variables",
    multiple=True,
    help="Variable substitution as KEY=VALUE (can be repeated)",
)
@click.option(
    "--var-file",
    "var_files",
    multiple=True,
    help="Variable from file as KEY=PATH (can be repeated)",
)
def get_embedded_prompt(
    prompt_name: str,
    variables: tuple[str, ...],
    var_files: tuple[str, ...],
) -> None:
    """Get embedded prompt content from bundled prompts.

    Reads the specified prompt from the erk package's bundled prompts
    and outputs its content to stdout.

    PROMPT_NAME is the name of the prompt (without .md extension).

    Use --var to substitute {{ KEY }} placeholders with values.
    Use --var-file to substitute placeholders with file contents.
    """
    if prompt_name not in AVAILABLE_PROMPTS:
        available = ", ".join(sorted(AVAILABLE_PROMPTS))
        click.echo(f"Unknown prompt: {prompt_name}", err=True)
        click.echo(f"Available prompts: {available}", err=True)
        raise SystemExit(1)

    bundled_github_dir = get_bundled_github_dir()
    prompt_path = bundled_github_dir / "prompts" / f"{prompt_name}.md"

    if not prompt_path.exists():
        click.echo(f"Prompt file not found: {prompt_path}", err=True)
        raise SystemExit(1)

    # Build variables dict from --var options
    var_dict: dict[str, str] = {}
    for var_str in variables:
        parsed = _parse_var_assignment(var_str)
        if parsed is None:
            click.echo(f"Error: Invalid --var format: {var_str!r}", err=True)
            click.echo("Expected format: KEY=VALUE", err=True)
            raise SystemExit(1)
        key, value = parsed
        var_dict[key] = value

    # Build variables from --var-file options
    for var_file_str in var_files:
        parsed = _parse_var_assignment(var_file_str)
        if parsed is None:
            click.echo(f"Error: Invalid --var-file format: {var_file_str!r}", err=True)
            click.echo("Expected format: KEY=PATH", err=True)
            raise SystemExit(1)
        key, file_path_str = parsed
        file_path = Path(file_path_str)
        if not file_path.exists():
            click.echo(f"Error: File not found for --var-file {key}: {file_path}", err=True)
            raise SystemExit(1)
        var_dict[key] = file_path.read_text(encoding="utf-8")

    content = prompt_path.read_text(encoding="utf-8")

    # Only perform substitution if variables were provided or template has placeholders
    if var_dict or _PLACEHOLDER_PATTERN.search(content):
        content = _substitute_variables(content, var_dict)

    click.echo(content, nl=False)
