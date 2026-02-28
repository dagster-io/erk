"""Fetch CI failure summaries for a PR.

Outputs JSON mapping of check name to summary text, parsed from the
ci-summarize job logs in the latest CI workflow run.

Usage:
    erk exec ci-fetch-summaries --pr-number 123

Output:
    JSON object: {"check_name": "summary", ...}

Exit Codes:
    0: Success (even if no summaries found - returns empty object)
    1: Error during execution
"""

from __future__ import annotations

import json

import click

from erk_shared.context.helpers import require_cwd, require_git, require_github
from erk_shared.gateway.github.ci_summary_parsing import parse_ci_summaries
from erk_shared.gateway.github.types import PRNotFound


@click.command(name="ci-fetch-summaries")
@click.option("--pr-number", required=True, type=int, help="PR number to fetch summaries for")
@click.pass_context
def ci_fetch_summaries(ctx: click.Context, *, pr_number: int) -> None:
    """Fetch CI failure summaries for a PR.

    Looks for the ci-summarize job in the latest CI workflow run
    for the given PR and outputs parsed summaries as JSON.
    """
    repo_root = require_cwd(ctx)
    require_git(ctx)
    github = require_github(ctx)

    # Get PR details for head branch
    pr_result = github.get_pr(repo_root, pr_number)
    if isinstance(pr_result, PRNotFound):
        click.echo(json.dumps({"error": f"PR #{pr_number} not found"}))
        raise SystemExit(1)

    # Find CI workflow runs for this PR's head branch
    runs_by_branch = github.get_workflow_runs_by_branches(
        repo_root, "ci.yml", [pr_result.head_ref_name]
    )
    run = runs_by_branch.get(pr_result.head_ref_name)
    if run is None:
        click.echo(json.dumps({}))
        return

    # Fetch ci-summarize job logs
    log_text = github.get_ci_summary_logs(repo_root, str(run.run_id))
    if log_text is None:
        click.echo(json.dumps({}))
        return

    summaries = parse_ci_summaries(log_text)
    click.echo(json.dumps(summaries, indent=2))
