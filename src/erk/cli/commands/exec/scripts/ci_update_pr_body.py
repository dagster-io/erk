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

from erk.cli.config import load_config
from erk_shared.context.helpers import (
    require_git,
    require_github,
    require_prompt_executor,
    require_repo_root,
)
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.pr_footer import build_pr_body_footer, build_remote_execution_note
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.gt.prompts import get_commit_message_prompt, truncate_diff


@dataclass(frozen=True)
class UpdateSuccess:
    """Success result when PR body is updated."""

    success: bool
    pr_number: int
    summary_source: Literal["ai", "commit-message", "minimal-fallback"]


@dataclass(frozen=True)
class UpdateError:
    """Error result when PR body update fails."""

    success: bool
    error: Literal[
        "pr-not-found",
        "empty-diff",
        "diff-fetch-failed",
        "claude-execution-failed",
        "claude-empty-output",
        "github-api-failed",
    ]
    message: str
    stderr: str | None


def _build_prompt(
    diff_content: str, current_branch: str, parent_branch: str, repo_root: Path
) -> str:
    """Build prompt for PR summary generation.

    Note: We deliberately do NOT include commit messages here. The commit messages
    may contain info about .worker-impl/ deletions that don't appear in the final PR diff.
    """
    context_section = f"""## Context

- Current branch: {current_branch}
- Parent branch: {parent_branch}"""

    system_prompt = get_commit_message_prompt(repo_root)
    return f"""{system_prompt}

{context_section}

## Diff

```diff
{diff_content}
```

Generate a commit message for this diff:"""


def _try_ai_summary(
    *,
    executor: PromptExecutor,
    repo_root: Path,
    diff_content: str,
    current_branch: str,
    parent_branch: str,
) -> str | None:
    """Try to generate AI summary from diff.

    Args:
        executor: PromptExecutor for Claude
        repo_root: Repository root path
        diff_content: Truncated diff content
        current_branch: Current branch name
        parent_branch: Parent branch name

    Returns:
        AI-generated summary on success, None on any failure
    """
    prompt = _build_prompt(diff_content, current_branch, parent_branch, repo_root)
    result = executor.execute_prompt(
        prompt, model="haiku", tools=None, cwd=repo_root, system_prompt=None, dangerous=False
    )

    if not result.success:
        return None

    if not result.output or not result.output.strip():
        return None

    return result.output


def _get_fallback_summary(git: Git, repo_root: Path, parent_branch: str) -> str | None:
    """Get fallback summary from commit messages.

    Filters out noise commits like .worker-impl/ deletions and CI triggers.

    Args:
        git: Git interface
        repo_root: Repository root path
        parent_branch: Parent branch name

    Returns:
        Joined meaningful commit messages as bullets, or None if none found
    """
    commit_messages = git.commit.get_commit_messages_since(repo_root, parent_branch)

    # Filter out noise commits
    noise_prefixes = [
        "Remove .worker-impl/",
        "Trigger CI workflows",
        "Update plan for issue",
        "Add plan for issue",
    ]

    meaningful_messages = []
    for message in commit_messages:
        if not any(message.startswith(prefix) for prefix in noise_prefixes):
            meaningful_messages.append(message)

    if not meaningful_messages:
        return None

    # Format as bullet list if multiple commits
    if len(meaningful_messages) == 1:
        return meaningful_messages[0]

    return "\n".join(f"- {msg}" for msg in meaningful_messages)


def _build_pr_body(
    *,
    summary: str,
    pr_number: int,
    issue_number: int,
    run_id: str | None,
    run_url: str | None,
    plans_repo: str | None,
) -> str:
    """Build the full PR body with summary, optional workflow link, and footer.

    Args:
        summary: AI-generated PR summary
        pr_number: PR number for checkout instructions
        issue_number: Issue number to close on merge
        run_id: Optional workflow run ID
        run_url: Optional workflow run URL
        plans_repo: Target repo in "owner/repo" format for cross-repo plans

    Returns:
        Formatted PR body markdown
    """
    parts = [f"## Summary\n\n{summary}"]

    # Add workflow link if provided
    if run_id is not None and run_url is not None:
        parts.append(build_remote_execution_note(run_id, run_url))

    # Add footer with checkout instructions
    parts.append(
        build_pr_body_footer(pr_number=pr_number, issue_number=issue_number, plans_repo=plans_repo)
    )

    return "\n".join(parts)


def _update_pr_body_impl(
    *,
    git: Git,
    github: GitHub,
    executor: PromptExecutor,
    repo_root: Path,
    issue_number: int,
    run_id: str | None,
    run_url: str | None,
    plans_repo: str | None,
) -> UpdateSuccess | UpdateError:
    """Implementation of PR body update with fallback logic.

    Args:
        git: Git interface
        github: GitHub interface
        executor: PromptExecutor for Claude
        repo_root: Repository root path
        issue_number: Issue number to close on merge
        run_id: Optional workflow run ID
        run_url: Optional workflow run URL
        plans_repo: Target repo in "owner/repo" format for cross-repo plans

    Returns:
        UpdateSuccess with summary_source on success, UpdateError only for unrecoverable errors
    """
    # Get current branch
    current_branch = git.branch.get_current_branch(repo_root)
    if current_branch is None:
        return UpdateError(
            success=False,
            error="pr-not-found",
            message="Could not determine current branch",
            stderr=None,
        )

    # Get PR for branch
    pr_result = github.get_pr_for_branch(repo_root, current_branch)
    if isinstance(pr_result, PRNotFound):
        return UpdateError(
            success=False,
            error="pr-not-found",
            message=f"No PR found for branch {current_branch}",
            stderr=None,
        )

    pr_number = pr_result.number

    # Get parent branch for context
    parent_branch = git.branch.detect_trunk_branch(repo_root)

    # Try to get PR diff (non-fatal if fails)
    diff_content: str | None = None
    try:
        pr_diff = github.get_pr_diff(repo_root, pr_number)
        if pr_diff.strip():
            diff_content, _was_truncated = truncate_diff(pr_diff)
    except RuntimeError:
        # Diff fetch failed - will fall back to commit messages
        pass

    # Tier 1: Try AI-generated summary (only if diff is available)
    summary: str | None = None
    summary_source: Literal["ai", "commit-message", "minimal-fallback"] = "ai"

    if diff_content is not None:
        summary = _try_ai_summary(
            executor=executor,
            repo_root=repo_root,
            diff_content=diff_content,
            current_branch=current_branch,
            parent_branch=parent_branch,
        )

    # Tier 2: Fall back to commit messages
    if summary is None:
        summary = _get_fallback_summary(git, repo_root, parent_branch)
        summary_source = "commit-message"

    # Tier 3: Last resort minimal message
    if summary is None:
        summary = "Implementation complete. See commit history for details."
        summary_source = "minimal-fallback"

    # Build full PR body
    pr_body = _build_pr_body(
        summary=summary,
        pr_number=pr_number,
        issue_number=issue_number,
        run_id=run_id,
        run_url=run_url,
        plans_repo=plans_repo,
    )

    # Update PR body (only truly unrecoverable error)
    try:
        github.update_pr_body(repo_root, pr_number, pr_body)
    except RuntimeError as e:
        return UpdateError(
            success=False,
            error="github-api-failed",
            message=f"Failed to update PR: {e}",
            stderr=None,
        )

    return UpdateSuccess(success=True, pr_number=pr_number, summary_source=summary_source)


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

    # Load config to get plans_repo
    config = load_config(repo_root)
    plans_repo = config.plans_repo

    result = _update_pr_body_impl(
        git=git,
        github=github,
        executor=executor,
        repo_root=repo_root,
        issue_number=issue_number,
        run_id=run_id,
        run_url=run_url,
        plans_repo=plans_repo,
    )

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if update failed
    if isinstance(result, UpdateError):
        raise SystemExit(1)
