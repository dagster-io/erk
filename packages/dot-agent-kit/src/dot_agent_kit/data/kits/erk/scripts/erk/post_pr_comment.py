"""Post GitHub issue comment with PR link after PR publication.

This kit CLI command posts a comment to the linked GitHub issue with the PR URL
after a PR has been created via the submit workflow.

Usage:
    dot-agent run erk post-pr-comment --pr-url "<url>" --pr-number <number>

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ dot-agent run erk post-pr-comment --pr-url "https://github.com/o/r/pull/1" --pr-number 1
    {"success": true, "issue_number": 456}

    $ dot-agent run erk post-pr-comment --pr-url "https://github.com/o/r/pull/1" --pr-number 1
    {"success": false, "error_type": "no_issue_reference", "message": "..."}
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click
from erk_shared.github.metadata import (
    MetadataBlock,
    create_metadata_block,
    render_erk_issue_event,
)
from erk_shared.impl_folder import has_issue_reference, read_issue_reference

from dot_agent_kit.context_helpers import (
    require_git,
    require_github_issues,
    require_repo_root,
)


@dataclass(frozen=True)
class PrCommentSuccess:
    """Success response for PR comment posting."""

    success: bool
    issue_number: int
    pr_number: int


@dataclass(frozen=True)
class PrCommentError:
    """Error response for PR comment posting."""

    success: bool
    error_type: str
    message: str


def create_pr_published_block(
    *,
    pr_number: int,
    pr_url: str,
    branch_name: str,
    timestamp: str,
) -> MetadataBlock:
    """Create an erk-pr-published metadata block.

    Args:
        pr_number: GitHub PR number
        pr_url: Full GitHub PR URL
        branch_name: Git branch name
        timestamp: ISO 8601 timestamp

    Returns:
        MetadataBlock with pr-published schema
    """
    data = {
        "status": "pr_published",
        "pr_number": pr_number,
        "pr_url": pr_url,
        "branch_name": branch_name,
        "timestamp": timestamp,
    }

    return create_metadata_block(key="erk-pr-published", data=data)


@click.command(name="post-pr-comment")
@click.option("--pr-url", required=True, help="GitHub PR URL")
@click.option("--pr-number", required=True, type=int, help="GitHub PR number")
@click.pass_context
def post_pr_comment(ctx: click.Context, pr_url: str, pr_number: int) -> None:
    """Post PR link comment to GitHub issue.

    Posts a comment to the linked GitHub issue (from .impl/issue.json) with
    the PR URL after PR publication. This enables users to navigate from
    the plan issue directly to the PR.

    PR_URL: Full GitHub PR URL
    PR_NUMBER: GitHub PR number
    """
    from datetime import UTC, datetime

    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    # Read issue reference
    impl_dir = Path.cwd() / ".impl"

    if not has_issue_reference(impl_dir):
        result = PrCommentError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found in .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        result = PrCommentError(
            success=False,
            error_type="invalid_issue_reference",
            message="Could not read .impl/issue.json",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Get branch name using Git abstraction
    branch_name = git.get_current_branch(Path.cwd())
    if branch_name is None:
        result = PrCommentError(
            success=False,
            error_type="branch_detection_failed",
            message="Could not determine branch name from git",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Generate timestamp
    timestamp = datetime.now(UTC).isoformat()

    # Create metadata block
    block = create_pr_published_block(
        pr_number=pr_number,
        pr_url=pr_url,
        branch_name=branch_name,
        timestamp=timestamp,
    )

    # Format description with PR link
    description = f"**PR:** [#{pr_number}]({pr_url})"

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title="🔗 PR Published",
        metadata=block,
        description=description,
    )

    # Get GitHub Issues from context (with LBYL check)
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        result = PrCommentError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Post comment to GitHub
    try:
        github.add_comment(repo_root, issue_ref.issue_number, comment_body)
        result_success = PrCommentSuccess(
            success=True,
            issue_number=issue_ref.issue_number,
            pr_number=pr_number,
        )
        click.echo(json.dumps(asdict(result_success), indent=2))
        raise SystemExit(0) from None
    except RuntimeError as e:
        result = PrCommentError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
