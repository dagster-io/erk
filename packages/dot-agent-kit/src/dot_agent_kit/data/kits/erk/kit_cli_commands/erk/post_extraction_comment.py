"""Post extraction workflow status comments to GitHub issues.

Usage:
    dot-agent run erk post-extraction-comment \
        --issue-number 123 \
        --status started \
        --workflow-run-url "https://..."

Status options:
    - started: Extraction workflow has begun
    - failed: Extraction failed with error
    - complete: Extraction succeeded with PR
    - no-changes: No documentation changes needed

Output:
    JSON with success status and comment_url
"""

import json
from datetime import UTC, datetime

import click

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


def _format_started_comment(workflow_run_url: str | None) -> str:
    """Format the started status comment."""
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "⚙️ **Documentation extraction started**",
        "",
        "<details>",
        "<summary>📋 Metadata</summary>",
        "",
        "```yaml",
        "status: started",
        f"started_at: {started_at}",
    ]

    if workflow_run_url:
        lines.append(f"workflow_run_url: {workflow_run_url}")

    lines.extend(
        [
            "```",
            "",
            "</details>",
            "",
            "---",
            "",
            "Extracting session data from issue comments...",
        ]
    )

    if workflow_run_url:
        lines.extend(["", f"[View workflow run]({workflow_run_url})"])

    return "\n".join(lines)


def _format_failed_comment(
    workflow_run_url: str | None,
    error_message: str | None,
) -> str:
    """Format the failed status comment."""
    lines = ["❌ **Documentation extraction failed**", ""]

    if error_message:
        lines.extend([f"**Error:** {error_message}", ""])

    lines.extend(
        [
            "No session content was found in the issue comments. This may happen if:",
            "- The raw extraction issue was created without session XML",
            "- The session content blocks are malformed",
        ]
    )

    if workflow_run_url:
        lines.extend(["", f"[View workflow run]({workflow_run_url})"])

    lines.extend(
        [
            "",
            "To retry, run the extraction manually:",
            "```",
            "/erk:create-extraction-plan",
            "```",
        ]
    )

    return "\n".join(lines)


def _format_complete_comment(pr_url: str | None) -> str:
    """Format the complete status comment."""
    completed_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "✅ **Documentation extraction complete**",
        "",
    ]

    if pr_url:
        lines.extend([f"**PR:** {pr_url}", ""])

    lines.extend(
        [
            "<details>",
            "<summary>📋 Metadata</summary>",
            "",
            "```yaml",
            "status: complete",
            f"completed_at: {completed_at}",
        ]
    )

    if pr_url:
        lines.append(f"pr_url: {pr_url}")

    lines.extend(
        [
            "```",
            "",
            "</details>",
            "",
            "---",
            "",
            "The extraction has created documentation improvements. Please review the PR.",
        ]
    )

    return "\n".join(lines)


def _format_no_changes_comment() -> str:
    """Format the no-changes status comment."""
    return "\n".join(
        [
            "ℹ️ **No documentation changes needed**",
            "",
            "The extraction analysis did not produce any documentation changes.",
            "This may happen if the session did not contain extractable patterns.",
        ]
    )


@click.command(name="post-extraction-comment")
@click.option(
    "--issue-number",
    type=int,
    required=True,
    help="GitHub issue number",
)
@click.option(
    "--status",
    type=click.Choice(["started", "failed", "complete", "no-changes"]),
    required=True,
    help="Extraction status",
)
@click.option(
    "--workflow-run-url",
    type=str,
    default=None,
    help="URL to the workflow run (for started/failed)",
)
@click.option(
    "--error-message",
    type=str,
    default=None,
    help="Error message (for failed status)",
)
@click.option(
    "--pr-url",
    type=str,
    default=None,
    help="PR URL (for complete status)",
)
@click.pass_context
def post_extraction_comment(
    ctx: click.Context,
    issue_number: int,
    status: str,
    workflow_run_url: str | None,
    error_message: str | None,
    pr_url: str | None,
) -> None:
    """Post extraction workflow status comment to a GitHub issue.

    Posts a formatted status comment based on the extraction workflow stage.
    """
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Format the comment based on status
    if status == "started":
        comment_body = _format_started_comment(workflow_run_url)
    elif status == "failed":
        comment_body = _format_failed_comment(workflow_run_url, error_message)
    elif status == "complete":
        comment_body = _format_complete_comment(pr_url)
    elif status == "no-changes":
        comment_body = _format_no_changes_comment()
    else:
        click.echo(json.dumps({"success": False, "error": f"Unknown status: {status}"}))
        raise SystemExit(1)

    # Post the comment
    try:
        github.add_comment(repo_root, issue_number, comment_body)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to post comment: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "status": status,
            }
        )
    )


if __name__ == "__main__":
    post_extraction_comment()
