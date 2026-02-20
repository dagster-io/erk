#!/usr/bin/env python3
"""Post a "workflow started" comment to a GitHub issue with YAML metadata block.

This command posts a structured comment to a GitHub issue indicating that a
GitHub Actions workflow has started. The comment includes a YAML metadata block
that can be parsed programmatically.

This replaces ~40 lines of bash heredoc template assembly in GitHub Actions workflows.

Usage:
    erk exec post-workflow-started-comment \\
        --plan-id 123 \\
        --branch-name my-feature-branch \\
        --pr-number 456 \\
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
        --plan-id 123 \\
        --branch-name feat-auth \\
        --pr-number 456 \\
        --run-id 99999 \\
        --run-url https://github.com/acme/app/actions/runs/99999 \\
        --repository acme/app
    {
      "success": true,
      "plan_id": 123
    }
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root


@dataclass(frozen=True)
class PostSuccess:
    """Success result when comment is posted."""

    success: bool
    plan_id: int


@dataclass(frozen=True)
class PostError:
    """Error result when comment posting fails."""

    success: bool
    error: str
    message: str


def _build_workflow_started_comment(
    *,
    plan_id: int,
    branch_name: str,
    pr_number: int,
    run_id: str,
    run_url: str,
    repository: str,
) -> str:
    """Build the workflow started comment body.

    Args:
        plan_id: Plan identifier
        branch_name: Git branch name
        pr_number: Pull request number
        run_id: GitHub Actions workflow run ID
        run_url: Full URL to the workflow run
        repository: Repository in owner/repo format

    Returns:
        Formatted markdown comment body
    """
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return f"""⚙️ GitHub Action Started

<details>
<summary>📋 Metadata</summary>

<!-- erk:metadata-block:workflow-started -->
```yaml
schema: workflow-started
status: started
started_at: {started_at}
workflow_run_id: "{run_id}"
workflow_run_url: {run_url}
branch_name: {branch_name}
plan_id: {plan_id}
```
<!-- /erk:metadata-block:workflow-started -->

</details>

---

Setup completed successfully.

**Branch:** `{branch_name}`
**PR:** [#{pr_number}](https://github.com/{repository}/pull/{pr_number})
**Status:** Ready for implementation

[View workflow run]({run_url})
"""


@click.command(name="post-workflow-started-comment")
@click.option("--plan-id", type=int, required=True, help="Plan identifier")
@click.option("--branch-name", type=str, required=True, help="Git branch name")
@click.option("--pr-number", type=int, required=True, help="Pull request number")
@click.option("--run-id", type=str, required=True, help="GitHub Actions workflow run ID")
@click.option("--run-url", type=str, required=True, help="Full URL to workflow run")
@click.option("--repository", type=str, required=True, help="Repository in owner/repo format")
@click.pass_context
def post_workflow_started_comment(
    ctx: click.Context,
    *,
    plan_id: int,
    branch_name: str,
    pr_number: int,
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

    # Build comment body
    comment_body = _build_workflow_started_comment(
        plan_id=plan_id,
        branch_name=branch_name,
        pr_number=pr_number,
        run_id=run_id,
        run_url=run_url,
        repository=repository,
    )

    # Post comment via PlanBackend (handles both issue and draft-PR plans)
    try:
        backend.add_comment(repo_root, str(plan_id), comment_body)
        result = PostSuccess(success=True, plan_id=plan_id)
        click.echo(json.dumps(asdict(result), indent=2))
    except RuntimeError as e:
        result = PostError(
            success=False,
            error="github-api-failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from e
