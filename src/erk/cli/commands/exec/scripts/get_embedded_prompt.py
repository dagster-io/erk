#!/usr/bin/env python3
"""Get embedded prompt content from bundled prompts.

This command reads prompt files bundled with the erk package and outputs
their content. Useful for GitHub Actions workflows that need prompt content.

Usage:
    erk exec get-embedded-prompt <prompt-name>

Output:
    The prompt content (markdown)

Exit Codes:
    0: Success
    1: Prompt not found

Examples:
    $ erk exec get-embedded-prompt dignified-python-review
    # Dignified Python Review Prompt
    ...

    $ erk exec get-embedded-prompt dignified-python-review > /tmp/prompt.md
"""

import click

from erk.artifacts.sync import get_bundled_github_dir

# Available prompts that can be retrieved
AVAILABLE_PROMPTS = frozenset(
    {
        "ci-autofix",
        "dignified-python-review",
    }
)


@click.command(name="get-embedded-prompt")
@click.argument("prompt_name")
def get_embedded_prompt(prompt_name: str) -> None:
    """Get embedded prompt content from bundled prompts.

    Reads the specified prompt from the erk package's bundled prompts
    and outputs its content to stdout.

    PROMPT_NAME is the name of the prompt (without .md extension).
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

    content = prompt_path.read_text(encoding="utf-8")
    click.echo(content, nl=False)
