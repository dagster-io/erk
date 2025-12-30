"""Convert plan title to filename.

Usage:
    erk exec issue-title-to-filename "Plan Title"

Single source of truth for filename transformation for /erk:save-plan.

Output:
    Filename on stdout (e.g., "my-feature-plan.md")
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success
    1: Error (empty title)
"""

import click

from erk_shared.naming import generate_filename_from_title


@click.command(name="issue-title-to-filename")
@click.argument("title")
def issue_title_to_filename(title: str) -> None:
    """Convert plan title to filename.

    TITLE: Plan title to convert
    """
    if not title or not title.strip():
        click.echo(click.style("Error: ", fg="red") + "Plan title cannot be empty", err=True)
        raise SystemExit(1)

    filename = generate_filename_from_title(title)
    click.echo(filename)
