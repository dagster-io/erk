#!/usr/bin/env python3
"""Update PR body with AI-generated summary and footer.

This command generates a PR summary from the diff using Claude, then updates
the PR body with the summary, optional workflow link, and standardized footer.

This combines generate-pr-summary + footer construction + gh pr edit in one step,
replacing ~30 lines of bash in GitHub Actions workflows.

Usage:
    erk exec ci-update-pr-body \\
        --issue-number 123 \\
        [--run-id 456789] \\
        [--run-url https://github.com/owner/repo/actions/runs/456789]

Output:
    JSON object with success status

Exit Codes:
    0: Success (PR body updated)
    1: Error (no PR for branch, empty diff, Claude failure, or GitHub API failed)

Examples:
    $ erk exec ci-update-pr-body --issue-number 123
    {
      "success": true,
      "pr_number": 789
    }

    $ erk exec ci-update-pr-body \\
        --issue-number 123 \\
        --run-id 456789 \\
        --run-url https://github.com/owner/repo/actions/runs/456789
    {
      "success": true,
      "pr_number": 789
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.context.helpers import (
    require_git,
    require_github,
    require_prompt_executor,
    require_repo_root,
)
from erk_shared.gateway.gt.prompts import COMMIT_MESSAGE_SYSTEM_PROMPT, truncate_diff
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.pr_footer import build_pr_body_footer, build_remote_execution_note
from erk_shared.github.types import PRNotFound
from erk_shared.prompt_executor import PromptExecutor


@dataclass(frozen=True)
class UpdateSuccess:
    """Success result when PR body is updated."""

    success: bool
    pr_number: int


@dataclass(frozen=True)
class UpdateError:
    """Error result when PR body update fails."""

    success: bool
    error: Literal[
        "pr_not_found", "empty_diff", "diff_fetch_failed", "claude_failed", "github_api_failed"
    ]
    message: str


def _build_prompt(diff_content: str, current_branch: str, parent_branch: str) -> str:
    """Build prompt for PR summary generation.

    Note: We deliberately do NOT include commit messages here. The commit messages
    may contain info about .worker-impl/ deletions that don't appear in the final PR diff.
    """
    context_section = f"""## Context

- Current branch: {current_branch}
- Parent branch: {parent_branch}"""

    return f"""{COMMIT_MESSAGE_SYSTEM_PROMPT}

{context_section}

## Diff

```diff
{diff_content}
```

Generate a commit message for this diff:"""


def _build_pr_body(
    summary: str,
    pr_number: int,
    issue_number: int,
    run_id: str | None,
    run_url: str | None,
) -> str:
    """Build the full PR body with summary, optional workflow link, and footer.

    Args:
        summary: AI-generated PR summary
        pr_number: PR number for checkout instructions
        issue_number: Issue number to close on merge
        run_id: Optional workflow run ID
        run_url: Optional workflow run URL

    Returns:
        Formatted PR body markdown
    """
    parts = [f"## Summary\n\n{summary}"]

    # Add workflow link if provided
    if run_id is not None and run_url is not None:
        parts.append(build_remote_execution_note(run_id, run_url))

    # Add footer with checkout instructions
    parts.append(build_pr_body_footer(pr_number=pr_number, issue_number=issue_number))

    return "\n".join(parts)


def _update_pr_body_impl(
    git: Git,
    github: GitHub,
    executor: PromptExecutor,
    repo_root: Path,
    issue_number: int,
    run_id: str | None,
    run_url: str | None,
) -> UpdateSuccess | UpdateError:
    """Implementation of PR body update.

    Args:
        git: Git interface
        github: GitHub interface
        executor: PromptExecutor for Claude
        repo_root: Repository root path
        issue_number: Issue number to close on merge
        run_id: Optional workflow run ID
        run_url: Optional workflow run URL

    Returns:
        UpdateSuccess on success, UpdateError on failure
    """
    # Get current branch
    current_branch = git.get_current_branch(repo_root)
    if current_branch is None:
        return UpdateError(
            success=False,
            error="pr_not_found",
            message="Could not determine current branch",
        )

    # Get PR for branch
    pr_result = github.get_pr_for_branch(repo_root, current_branch)
    if isinstance(pr_result, PRNotFound):
        return UpdateError(
            success=False,
            error="pr_not_found",
            message=f"No PR found for branch {current_branch}",
        )

    pr_number = pr_result.number

    # Get PR diff
    try:
        pr_diff = github.get_pr_diff(repo_root, pr_number)
    except RuntimeError as e:
        return UpdateError(
            success=False,
            error="diff_fetch_failed",
            message=f"Failed to get PR diff: {e}",
        )

    if not pr_diff.strip():
        return UpdateError(
            success=False,
            error="empty_diff",
            message="PR diff is empty",
        )

    # Truncate diff if needed
    diff_content, _was_truncated = truncate_diff(pr_diff)

    # Get parent branch for context
    parent_branch = git.detect_trunk_branch(repo_root)

    # Generate summary using Claude
    prompt = _build_prompt(diff_content, current_branch, parent_branch)
    result = executor.execute_prompt(prompt, model="haiku", cwd=repo_root)

    if not result.success:
        return UpdateError(
            success=False,
            error="claude_failed",
            message=f"Claude execution failed: {result.error}",
        )

    # Check for empty output
    if not result.output or not result.output.strip():
        return UpdateError(
            success=False,
            error="claude_failed",
            message="Claude returned empty output (possible API/auth issue)",
        )

    # Build full PR body
    pr_body = _build_pr_body(result.output, pr_number, issue_number, run_id, run_url)

    # Update PR body
    try:
        github.update_pr_body(repo_root, pr_number, pr_body)
    except RuntimeError as e:
        return UpdateError(
            success=False,
            error="github_api_failed",
            message=f"Failed to update PR: {e}",
        )

    return UpdateSuccess(success=True, pr_number=pr_number)


@click.command(name="ci-update-pr-body")
@click.option("--issue-number", type=int, required=True, help="Issue number to close on merge")
@click.option("--run-id", type=str, default=None, help="Optional workflow run ID")
@click.option("--run-url", type=str, default=None, help="Optional workflow run URL")
@click.pass_context
def ci_update_pr_body(
    ctx: click.Context,
    issue_number: int,
    run_id: str | None,
    run_url: str | None,
) -> None:
    """Update PR body with AI-generated summary and footer.

    Generates a summary from the PR diff using Claude, then updates the PR body
    with the summary, optional workflow link, and standardized footer with
    checkout instructions.
    """
    git = require_git(ctx)
    github = require_github(ctx)
    executor = require_prompt_executor(ctx)
    repo_root = require_repo_root(ctx)

    result = _update_pr_body_impl(git, github, executor, repo_root, issue_number, run_id, run_url)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if update failed
    if isinstance(result, UpdateError):
        raise SystemExit(1)
