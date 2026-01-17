"""Fetch PRs referencing an issue via REST API timeline.

Usage:
    erk exec get-issue-timeline-prs <ISSUE_NUMBER>

Output:
    JSON with {success, issue_number, prs: [{number, state, is_draft}]}

Exit Codes:
    0: Success - PR references fetched
    1: Error - API error
"""

import json

import click

from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)


@click.command(name="get-issue-timeline-prs")
@click.argument("issue_number", type=int)
@click.pass_context
def get_issue_timeline_prs(ctx: click.Context, issue_number: int) -> None:
    """Fetch PRs referencing an issue via REST API timeline.

    Uses the GitHub issues timeline API to find cross-referenced PRs.
    Avoids jq escaping issues that occur with complex shell pipelines.
    """
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    try:
        pr_refs = github.get_prs_referencing_issue(repo_root, issue_number)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to get PR references for #{issue_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "prs": [
                    {
                        "number": pr.number,
                        "state": pr.state,
                        "is_draft": pr.is_draft,
                    }
                    for pr in pr_refs
                ],
            }
        )
    )
