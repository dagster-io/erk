#!/usr/bin/env python3
"""Get closing text for PR body based on .impl/issue.json reference.

This command reads the .impl/issue.json file to determine if there's an
associated GitHub issue that should be closed when the PR merges.

Usage:
    erk exec get-closing-text

Output:
    Plain text "Closes #N" (same-repo) or "Closes owner/repo#N" (cross-repo)
    Empty output if no issue reference

Exit Codes:
    0: Always (whether issue reference exists or not)

Examples:
    $ erk exec get-closing-text
    Closes #776

    $ erk exec get-closing-text  # Cross-repo plans
    Closes owner/plans-repo#776

    $ erk exec get-closing-text  # No .impl/issue.json
    (no output)
"""

from pathlib import Path

import click

from erk.cli.config import load_config
from erk_shared.impl_folder import read_issue_reference


def _find_repo_root(start: Path) -> Path | None:
    """Find repository root by looking for .git directory."""
    current = start
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


@click.command(name="get-closing-text")
def get_closing_text() -> None:
    """Get closing text for PR body based on .impl/issue.json reference.

    Reads .impl/issue.json from the current directory. If an issue reference
    exists, outputs "Closes #N" (or "Closes owner/repo#N" for cross-repo plans)
    which can be included in PR descriptions to automatically close the issue
    when the PR merges.

    Outputs nothing and exits successfully if no issue reference is found.
    """
    cwd = Path.cwd()

    # Check .impl/ first, then .worker-impl/
    impl_dir = cwd / ".impl"
    if not impl_dir.exists():
        impl_dir = cwd / ".worker-impl"

    if not impl_dir.exists():
        # No impl folder - nothing to output
        return

    issue_ref = read_issue_reference(impl_dir)

    if issue_ref is not None:
        # Load config to check for cross-repo plans
        repo_root = _find_repo_root(cwd)
        plans_repo: str | None = None
        if repo_root is not None:
            config = load_config(repo_root)
            plans_repo = config.plans_repo

        # Format issue reference
        if plans_repo is None:
            closing_text = f"Closes #{issue_ref.issue_number}"
        else:
            closing_text = f"Closes {plans_repo}#{issue_ref.issue_number}"

        click.echo(closing_text)
