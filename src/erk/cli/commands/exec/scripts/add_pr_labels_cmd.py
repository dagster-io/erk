"""Add labels to a pull request with retry and comprehensive error handling.

Usage:
    erk exec add-pr-labels <PR_NUMBER> --labels label1 --labels label2

Output:
    JSON with {success, pr_number, added_labels, failed_labels, errors}

Exit Codes:
    0: Complete (some or all labels added - check 'success' field in JSON)
    1: Critical error (PR not found, auth issues, etc.)
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

import click

from erk_shared.context.helpers import require_github, require_repo_root, require_time
from erk_shared.gateway.github.label_ops import add_labels_resilient
from erk_shared.gateway.github.types import PRNotFound

if TYPE_CHECKING:
    from pathlib import Path


@click.command(name="add-pr-labels")
@click.argument("pr_number", type=int)
@click.option(
    "--labels",
    "labels_list",
    multiple=True,
    required=True,
    help="Labels to add (can be repeated)",
)
@click.pass_context
def add_pr_labels(
    ctx: click.Context,
    pr_number: int,
    labels_list: tuple[str, ...],
) -> None:
    """Add labels to a PR with automatic retry on transient failures.

    Attempts to add each label with retry on transient errors (502, 503, etc).
    Partial success is reported: some labels may be added while others fail.
    """
    github = require_github(ctx)
    time = require_time(ctx)
    repo_root: Path = require_repo_root(ctx)

    # Validate PR exists
    pr_result = github.get_pr(repo_root, pr_number)
    if isinstance(pr_result, PRNotFound):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"PR #{pr_number} not found",
                }
            )
        )
        ctx.exit(1)

    result = add_labels_resilient(github, time=time, repo_root=repo_root, pr_number=pr_number, labels=labels_list)

    click.echo(json.dumps(asdict(result)))

    # Caller should check 'success' field in JSON to determine if retry is needed.
