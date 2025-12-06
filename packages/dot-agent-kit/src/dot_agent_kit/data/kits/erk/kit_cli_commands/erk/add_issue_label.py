"""Add a label to a GitHub issue.

Usage:
    dot-agent run erk add-issue-label --issue-number 123 --label "extraction-failed"

Output:
    JSON with success status, issue_number, and label
"""

import json

import click

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


@click.command(name="add-issue-label")
@click.option(
    "--issue-number",
    type=int,
    required=True,
    help="GitHub issue number",
)
@click.option(
    "--label",
    type=str,
    required=True,
    help="Label to add to the issue",
)
@click.pass_context
def add_issue_label(
    ctx: click.Context,
    issue_number: int,
    label: str,
) -> None:
    """Add a label to a GitHub issue.

    Adds the specified label to the issue. If the label already exists
    on the issue, this is a no-op.
    """
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    try:
        github.ensure_label_on_issue(repo_root, issue_number, label)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to add label: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "label": label,
            }
        )
    )


if __name__ == "__main__":
    add_issue_label()
