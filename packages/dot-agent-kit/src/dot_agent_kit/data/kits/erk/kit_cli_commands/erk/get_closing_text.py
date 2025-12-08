"""Get issue closing text from .impl/issue.json.

This kit CLI command extracts the issue closing text (e.g., "Closes #123")
from the .impl/issue.json file if it exists. This is used by git-only
PR workflows to auto-close linked issues.

Usage:
    dot-agent run erk get-closing-text

Output:
    If issue.json exists: "Closes #N" (no newline)
    If no issue reference: Empty output

Exit Codes:
    0: Always (command succeeds even without issue reference)

Examples:
    $ dot-agent run erk get-closing-text
    Closes #123

    $ # No output if no issue reference exists
"""

from pathlib import Path

import click
from erk_shared.impl_folder import has_issue_reference, read_issue_reference


@click.command(name="get-closing-text")
def get_closing_text() -> None:
    """Get issue closing text from .impl/issue.json.

    Returns the closing text for GitHub PR bodies if an issue reference exists
    in the current directory's .impl/issue.json file. Returns empty output if
    no issue reference is found, allowing the command to be used unconditionally
    in shell scripts.
    """
    impl_dir = Path.cwd() / ".impl"

    if not has_issue_reference(impl_dir):
        return  # Empty output

    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is not None:
        click.echo(f"Closes #{issue_ref.issue_number}", nl=False)
