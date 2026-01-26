#!/usr/bin/env python3
"""Handle no-changes scenario in erk-impl workflow gracefully.

When implementation produces no code changes (duplicate plan, work already merged),
this command updates the PR with diagnostic information and marks it ready for review.

This replaces workflow failure with an informational PR that users can review and close.

Usage:
    erk exec handle-no-changes \
        --pr-number 123 \
        --issue-number 456 \
        --behind-count 5 \
        --base-branch master \
        [--recent-commits "abc1234 Fix bug\\ndef5678 Add feature"] \
        [--run-url https://github.com/owner/repo/actions/runs/789]

Output:
    JSON object with success status

Exit Codes:
    0: Success (PR updated, labeled, and marked ready)
    1: Error (GitHub API failure)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_github, require_repo_root
from erk_shared.gateway.github.types import BodyText


@dataclass(frozen=True)
class HandleNoChangesSuccess:
    """Success result when no-changes is handled."""

    success: bool
    pr_number: int
    issue_number: int


@dataclass(frozen=True)
class HandleNoChangesError:
    """Error result when handling fails."""

    success: bool
    error: str
    message: str


# Label definition (matches plan_issues.py)
_LABEL_NO_CHANGES = "no-changes"
_LABEL_NO_CHANGES_DESC = "Implementation produced no code changes"
_LABEL_NO_CHANGES_COLOR = "FFA500"


def _build_no_changes_title(*, issue_number: int, original_title: str) -> str:
    """Build PR title indicating no changes were produced.

    Args:
        issue_number: Plan issue number
        original_title: Original PR title

    Returns:
        New title with [no-changes] prefix and issue reference
    """
    return f"[no-changes] P{issue_number} Impl Attempt: {original_title}"


def _build_pr_body(
    *,
    issue_number: int,
    behind_count: int,
    base_branch: str,
    recent_commits: str | None,
    run_url: str | None,
) -> str:
    """Build PR body explaining why no changes were made.

    Args:
        issue_number: Plan issue number for linking
        behind_count: How many commits behind base branch
        base_branch: Base branch name
        recent_commits: Recent commits on base branch (newline-separated)
        run_url: Optional workflow run URL

    Returns:
        Formatted PR body markdown
    """
    parts = ["## No Code Changes", ""]
    parts.append("Implementation completed but produced no code changes.")
    parts.append("")
    parts.append("### Diagnosis")
    parts.append("")
    parts.append(
        f"**Likely cause: Duplicate plan** - The work may already be merged to `{base_branch}`."
    )
    parts.append("")

    if behind_count > 0:
        parts.append(f"Branch is **{behind_count} commits** behind `origin/{base_branch}`.")
        parts.append("")

    if recent_commits and recent_commits.strip():
        parts.append(f"**Recent commits on `{base_branch}`:**")
        for line in recent_commits.strip().split("\n"):
            if line.strip():
                parts.append(f"- {line.strip()}")
        parts.append("")

    parts.append("### Next Steps")
    parts.append("")
    parts.append("1. Review the recent commits above to check if the work is done")
    parts.append(f"2. If done: Close this PR and the linked plan issue #{issue_number}")
    parts.append("3. If not done: Investigate why no changes were produced")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(f"Closes #{issue_number}")

    if run_url:
        parts.append("")
        parts.append(f"[View workflow run]({run_url})")

    return "\n".join(parts)


def _build_issue_comment(*, pr_number: int) -> str:
    """Build comment for the plan issue linking to the PR.

    Args:
        pr_number: PR number to link to

    Returns:
        Issue comment markdown
    """
    return (
        f"Implementation produced no code changes. "
        f"See PR #{pr_number} for diagnostic information.\n\n"
        f"If the work is already complete, close both this issue and the PR."
    )


@click.command(name="handle-no-changes")
@click.option("--pr-number", type=int, required=True, help="PR number to update")
@click.option("--issue-number", type=int, required=True, help="Plan issue number")
@click.option("--behind-count", type=int, required=True, help="How many commits behind base branch")
@click.option("--base-branch", type=str, required=True, help="Base branch name")
@click.option("--original-title", type=str, required=True, help="Original PR title")
@click.option(
    "--recent-commits",
    type=str,
    default=None,
    help="Recent commits on base branch (newline-separated)",
)
@click.option("--run-url", type=str, default=None, help="Optional workflow run URL")
@click.pass_context
def handle_no_changes(
    ctx: click.Context,
    *,
    pr_number: int,
    issue_number: int,
    behind_count: int,
    base_branch: str,
    original_title: str,
    recent_commits: str | None,
    run_url: str | None,
) -> None:
    """Handle no-changes scenario gracefully.

    Updates the PR with diagnostic information explaining why no changes were made,
    adds the no-changes label, marks the PR ready for review, and adds a comment
    to the plan issue.

    Exits with code 0 on success (making the workflow succeed rather than fail).
    """
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    # Build PR title and body
    new_title = _build_no_changes_title(issue_number=issue_number, original_title=original_title)
    pr_body = _build_pr_body(
        issue_number=issue_number,
        behind_count=behind_count,
        base_branch=base_branch,
        recent_commits=recent_commits,
        run_url=run_url,
    )

    # 1. Update PR title and body
    try:
        github.update_pr_title_and_body(
            repo_root=repo_root,
            pr_number=pr_number,
            title=new_title,
            body=BodyText(content=pr_body),
        )
    except RuntimeError as e:
        result = HandleNoChangesError(
            success=False,
            error="github-api-failed",
            message=f"Failed to update PR title and body: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from None

    # 2. Ensure label exists and add to PR
    try:
        github.issues.ensure_label_exists(
            repo_root=repo_root,
            label=_LABEL_NO_CHANGES,
            description=_LABEL_NO_CHANGES_DESC,
            color=_LABEL_NO_CHANGES_COLOR,
        )
        github.add_label_to_pr(repo_root, pr_number, _LABEL_NO_CHANGES)
    except RuntimeError as e:
        result = HandleNoChangesError(
            success=False,
            error="github-api-failed",
            message=f"Failed to add label: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from None

    # 3. Mark PR ready for review
    try:
        github.mark_pr_ready(repo_root, pr_number)
    except RuntimeError as e:
        result = HandleNoChangesError(
            success=False,
            error="github-api-failed",
            message=f"Failed to mark PR ready: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from None

    # 4. Add comment to plan issue
    try:
        comment = _build_issue_comment(pr_number=pr_number)
        github.issues.add_comment(repo_root, issue_number, comment)
    except RuntimeError as e:
        result = HandleNoChangesError(
            success=False,
            error="github-api-failed",
            message=f"Failed to add issue comment: {e}",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(1) from None

    # Success - output JSON and exit 0
    result = HandleNoChangesSuccess(
        success=True,
        pr_number=pr_number,
        issue_number=issue_number,
    )
    click.echo(json.dumps(asdict(result), indent=2))
