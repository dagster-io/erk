"""Create a plan review branch and push to remote.

Usage:
    erk exec plan-create-review-branch <issue-number>

Output:
    JSON with branch name, file path, and plan title

Exit Codes:
    0: Success
    1: Error (issue not found, missing erk-plan label, no plan content, branch exists, or git error)
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_git, require_repo_root, require_time
from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import format_branch_timestamp_suffix


@dataclass(frozen=True)
class PlanReviewBranchSuccess:
    """Success response for plan review branch creation."""

    success: bool
    issue_number: int
    branch: str
    file_path: str
    plan_title: str


@dataclass(frozen=True)
class PlanReviewBranchError:
    """Error response for plan review branch creation."""

    success: bool
    error: str
    message: str


class PlanReviewBranchException(Exception):
    """Exception raised during plan review branch creation."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


def _fetch_plan_content(
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
) -> tuple[str, str]:
    """Fetch plan content from GitHub issue.

    Args:
        github_issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Issue number to fetch

    Returns:
        Tuple of (plan_title, plan_content) on success

    Raises:
        PlanReviewBranchException: If issue not found, missing label, or no plan content
    """
    # LBYL: Check if issue exists before fetching
    if not github_issues.issue_exists(repo_root, issue_number):
        raise PlanReviewBranchException(
            error="issue_not_found",
            message=f"Issue #{issue_number} not found",
        )

    # Issue exists, safe to fetch
    issue = github_issues.get_issue(repo_root, issue_number)

    # Validate erk-plan label
    if "erk-plan" not in issue.labels:
        raise PlanReviewBranchException(
            error="missing_erk_plan_label",
            message=f"Issue #{issue_number} does not have the erk-plan label",
        )

    # Extract plan comment ID from metadata
    plan_comment_id = extract_plan_header_comment_id(issue.body)
    if plan_comment_id is None:
        raise PlanReviewBranchException(
            error="no_plan_content",
            message=f"Issue #{issue_number} has no plan_comment_id in metadata",
        )

    # Fetch comments
    comments = github_issues.get_issue_comments_with_urls(repo_root, issue_number)

    if not comments:
        raise PlanReviewBranchException(
            error="no_plan_content",
            message=f"Issue #{issue_number} has no comments",
        )

    # Find the comment with the plan content
    for comment in comments:
        if comment.id == plan_comment_id:
            content = extract_plan_from_comment(comment.body)
            if content:
                return (issue.title, content)

    raise PlanReviewBranchException(
        error="no_plan_content",
        message=f"Issue #{issue_number} comment {plan_comment_id} has no plan markers",
    )


def _create_review_branch_impl(
    git: Git,
    *,
    github_issues: GitHubIssues,
    time: Time,
    repo_root: Path,
    issue_number: int,
) -> PlanReviewBranchSuccess:
    """Create a plan review branch and push to remote.

    Args:
        git: Git gateway
        github_issues: GitHub issues gateway
        time: Time gateway for timestamps
        repo_root: Repository root path
        issue_number: Issue number to create review branch for

    Returns:
        PlanReviewBranchSuccess on success

    Raises:
        PlanReviewBranchException: If plan content cannot be fetched or validated
    """
    # Fetch plan content (raises PlanReviewBranchException on failure)
    plan_title, plan_content = _fetch_plan_content(github_issues, repo_root, issue_number)

    # Define branch and file names with timestamp (format: plan-review-{issue}-{MM-DD-HHMM})
    timestamp_suffix = format_branch_timestamp_suffix(time.now())
    branch_name = f"plan-review-{issue_number}{timestamp_suffix}"
    file_name = f"PLAN-REVIEW-{issue_number}.md"

    # Fetch origin/master, create branch, commit, and push
    # These operations let exceptions escape as they represent invariant violations
    # if they fail (network/disk/auth issues are exceptional, not expected states)
    git.remote.fetch_branch(repo_root, "origin", "master")
    git.branch.create_branch(repo_root, branch_name, "origin/master", force=False)
    git.branch.checkout_branch(repo_root, branch_name)

    # Write plan file at repo root
    file_path = repo_root / file_name
    file_path.write_text(plan_content, encoding="utf-8")

    # Stage, commit, and push
    git.commit.stage_files(repo_root, [file_name])
    commit_message = f"Add plan #{issue_number} for review"
    git.commit.commit(repo_root, commit_message)
    git.remote.push_to_remote(repo_root, "origin", branch_name, set_upstream=True, force=False)

    return PlanReviewBranchSuccess(
        success=True,
        issue_number=issue_number,
        branch=branch_name,
        file_path=file_name,
        plan_title=plan_title,
    )


@click.command(name="plan-create-review-branch")
@click.argument("issue_number", type=int)
@click.pass_context
def plan_create_review_branch(
    ctx: click.Context,
    issue_number: int,
) -> None:
    """Create a plan review branch and push to remote.

    Creates a branch plan-review-{issue}-{timestamp} from origin/master, writes plan
    to PLAN-REVIEW-{issue}.md, commits, and pushes to origin.
    """
    git = require_git(ctx)
    github_issues = require_github_issues(ctx)
    time = require_time(ctx)
    repo_root = require_repo_root(ctx)

    try:
        result = _create_review_branch_impl(
            git,
            github_issues=github_issues,
            time=time,
            repo_root=repo_root,
            issue_number=issue_number,
        )
        click.echo(json.dumps(asdict(result)))
    except PlanReviewBranchException as e:
        error_response = PlanReviewBranchError(
            success=False,
            error=e.error,
            message=e.message,
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)
