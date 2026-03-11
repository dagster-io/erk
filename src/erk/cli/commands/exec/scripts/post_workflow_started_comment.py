#!/usr/bin/env python3
"""Post a "workflow started" comment to a GitHub issue with YAML metadata block.

This command posts a structured comment to a GitHub issue indicating that a
GitHub Actions workflow has started. The comment includes a YAML metadata block
that can be parsed programmatically.

This replaces ~40 lines of bash heredoc template assembly in GitHub Actions workflows.

Usage:
    erk exec post-workflow-started-comment \\
        --pr-number 123 \\
        --branch-name my-feature-branch \\
        --impl-pr-number 456 \\
        --run-id 12345678 \\
        --run-url https://github.com/owner/repo/actions/runs/12345678 \\
        --repository owner/repo

Output:
    JSON object with success status

Exit Codes:
    0: Success (comment posted)
    1: Error (GitHub API failed)

Examples:
    $ erk exec post-workflow-started-comment \\
        --pr-number 123 \\
        --branch-name feat-auth \\
        --impl-pr-number 456 \\
        --run-id 99999 \\
        --run-url https://github.com/acme/app/actions/runs/99999 \\
        --repository acme/app
    {
      "success": true,
      "pr_number": 123
    }
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root, require_time
from erk_shared.gateway.github.metadata.core import (
    create_workflow_started_block,
    render_erk_issue_event,
)


@dataclass(frozen=True)
class PostSuccess:
    """Success result when comment is posted."""

    success: bool
    pr_number: int


@dataclass(frozen=True)
class PostError:
    """Error result when comment posting fails."""

    success: bool
    error: str
    message: str


def _build_workflow_started_comment(
    *,
    pr_number: int,
    branch_name: str,
    impl_pr_number: int,
    run_id: str,
    run_url: str,
    repository: str,
    now_iso: str,
) -> str:
    """Build the workflow started comment body using the canonical metadata API.

    Uses the standard metadata block API so the comment can be parsed
    by ``parse_metadata_blocks`` during ``erk land``.

    Args:
        pr_number: PR identifier
        branch_name: Git branch name
        impl_pr_number: Implementation pull request number
        run_id: GitHub Actions workflow run ID
        run_url: Full URL to the workflow run
        repository: Repository in owner/repo format
        now_iso: ISO-format UTC timestamp for testability

    Returns:
        Formatted markdown comment body
    """
    started_at = now_iso

    block = create_workflow_started_block(
        started_at=started_at,
        workflow_run_id=run_id,
        workflow_run_url=run_url,
        plan_number=pr_number,
        branch_name=branch_name,
    )

    description = (
        f"Setup completed successfully.\n"
        f"\n"
        f"**Branch:** `{branch_name}`\n"
        f"**PR:** [#{impl_pr_number}](https://github.com/{repository}/pull/{impl_pr_number})\n"
        f"**Status:** Ready for implementation\n"
        f"\n"
        f"[View workflow run]({run_url})"
    )

    return render_erk_issue_event(
        title="⚙️ GitHub Action Started",
        metadata=block,
        description=description,
    )


@click.command(name="post-workflow-started-comment")
@click.option("--pr-number", type=int, required=True, help="PR identifier")
@click.option("--branch-name", type=str, required=True, help="Git branch name")
@click.option("--impl-pr-number", type=int, required=True, help="Pull request number")
@click.option("--run-id", type=str, required=True, help="GitHub Actions workflow run ID")
@click.option("--run-url", type=str, required=True, help="Full URL to workflow run")
@click.option("--repository", type=str, required=True, help="Repository in owner/repo format")
@click.pass_context
def post_workflow_started_comment(
    ctx: click.Context,
    *,
    pr_number: int,
    branch_name: str,
    impl_pr_number: int,
    run_id: str,
    run_url: str,
    repository: str,
) -> None:
    """Post a workflow started comment to a GitHub issue.

    Posts a structured comment with YAML metadata block indicating that a
    GitHub Actions workflow has started processing the plan.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    time = require_time(ctx)

    # Build comment body
    now_iso = time.now().replace(tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    comment_body = _build_workflow_started_comment(
        pr_number=pr_number,
        branch_name=branch_name,
        impl_pr_number=impl_pr_number,
        run_id=run_id,
        run_url=run_url,
        repository=repository,
        now_iso=now_iso,
    )

    # Post comment via ManagedPrBackend (handles both issue and planned-PR plans)
    try:
        backend.add_comment(repo_root, str(pr_number), comment_body)
        result = PostSuccess(success=True, pr_number=pr_number)
        click.echo(json.dumps(asdict(result), indent=2))
    except RuntimeError as e:
        result = PostError(
            success=False,
            error="github-api-failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from e
