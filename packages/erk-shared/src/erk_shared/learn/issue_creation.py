"""Create erk-learn GitHub issues for documentation gap capture.

This module creates issues labeled `erk-learn` containing synthesized
documentation gaps from implementation sessions.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.learn.types import LearnResult

# Label configuration
_LABEL_ERK_LEARN = "erk-learn"
_LABEL_ERK_LEARN_DESC = "Documentation gaps captured from implementation session"
_LABEL_ERK_LEARN_COLOR = "7057FF"  # Purple


def _format_issue_body(
    session_id: str,
    branch_name: str,
    pr_number: int,
    synthesis: str,
) -> str:
    """Format the issue body with metadata header and content.

    Args:
        session_id: Claude Code session ID
        branch_name: Git branch name
        pr_number: Pull request number
        synthesis: Synthesized documentation gaps markdown

    Returns:
        Formatted issue body with metadata block
    """
    timestamp = datetime.now(UTC).isoformat()

    return f"""<!-- erk-learn-header
session_id: {session_id}
branch: {branch_name}
pr_number: {pr_number}
created_at: {timestamp}
-->

## Documentation Gaps

{synthesis}

## Source Context
- **Branch**: {branch_name}
- **PR**: #{pr_number}
- **Session**: `{session_id}`
"""


def create_learn_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    branch_name: str,
    pr_number: int,
    session_id: str,
    synthesis: str,
) -> LearnResult:
    """Create erk-learn issue with synthesized documentation gaps.

    Follows the pattern from plan_issues.py:
    1. Ensure label exists
    2. Create issue with formatted body
    3. Return result with URL and number

    Args:
        github_issues: GitHubIssues interface for API calls
        repo_root: Repository root directory
        branch_name: Git branch name for context
        pr_number: PR number that was just landed
        session_id: Claude Code session ID
        synthesis: Synthesized documentation gaps markdown

    Returns:
        LearnResult with success status and issue details
    """
    # Step 1: Ensure label exists
    try:
        github_issues.ensure_label_exists(
            repo_root=repo_root,
            label=_LABEL_ERK_LEARN,
            description=_LABEL_ERK_LEARN_DESC,
            color=_LABEL_ERK_LEARN_COLOR,
        )
    except RuntimeError as e:
        return LearnResult(
            success=False,
            issue_url=None,
            issue_number=None,
            error=f"Failed to ensure label exists: {e}",
        )

    # Step 2: Create issue
    title = f"Learn: {branch_name}"
    body = _format_issue_body(session_id, branch_name, pr_number, synthesis)

    try:
        result = github_issues.create_issue(
            repo_root=repo_root,
            title=title,
            body=body,
            labels=[_LABEL_ERK_LEARN],
        )
    except RuntimeError as e:
        return LearnResult(
            success=False,
            issue_url=None,
            issue_number=None,
            error=f"Failed to create issue: {e}",
        )

    return LearnResult(
        success=True,
        issue_url=result.url,
        issue_number=result.number,
        error=None,
    )
