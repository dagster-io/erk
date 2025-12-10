#!/usr/bin/env python3
"""Update PR body with generated summary and footer.

This command consolidates the full PR body update workflow into a single operation:
1. Get PR number from branch
2. Generate PR body (summary + footer) via Claude
3. Update the PR via GitHub API

Replaces multi-command bash composition in workflows.

Usage:
    erk kit exec erk update-pr-body --branch "my-branch" --issue-number 456

Output:
    JSON object with success status and PR number

Exit Codes:
    0: Success (PR body updated)
    1: Error (PR not found, generation failed)

Examples:
    $ erk kit exec erk update-pr-body --branch "feature-branch" --issue-number 123
    {
      "success": true,
      "pr_number": 1895,
      "message": "PR body updated successfully"
    }
"""

import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import PRNotFound
from erk_shared.integrations.gt.prompts import COMMIT_MESSAGE_SYSTEM_PROMPT, truncate_diff
from erk_shared.prompt_executor import PromptExecutor

from dot_agent_kit.context_helpers import (
    require_git,
    require_github,
    require_prompt_executor,
    require_repo_root,
)


@dataclass
class UpdateSuccess:
    """Success result when PR body was updated."""

    success: bool
    pr_number: int
    message: str


@dataclass
class UpdateError:
    """Error result when update fails."""

    success: bool
    error: Literal[
        "pr_not_found",
        "empty_diff",
        "claude_failed",
        "pr_diff_failed",
        "gh_edit_failed",
    ]
    message: str


def _build_summary_prompt(diff_content: str, current_branch: str, parent_branch: str) -> str:
    """Build prompt for PR summary generation."""
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


def _update_pr_body_impl(
    github: GitHub,
    git: Git,
    executor: PromptExecutor,
    repo_root: Path,
    branch: str,
    issue_number: int | None,
) -> UpdateSuccess | UpdateError:
    """Update PR body with generated summary and footer.

    Args:
        github: GitHub interface for PR operations
        git: Git interface for branch operations
        executor: Prompt executor for Claude
        repo_root: Repository root directory
        branch: Branch name to find PR for
        issue_number: Optional issue number to include in footer

    Returns:
        UpdateSuccess with pr_number, or UpdateError on failure
    """
    # Get PR for branch
    pr = github.get_pr_for_branch(repo_root, branch)
    if isinstance(pr, PRNotFound):
        return UpdateError(
            success=False,
            error="pr_not_found",
            message=f"No PR found for branch '{branch}'",
        )

    pr_number = pr.number

    # Get PR diff
    try:
        pr_diff = github.get_pr_diff(repo_root, pr_number)
    except RuntimeError as e:
        return UpdateError(
            success=False,
            error="pr_diff_failed",
            message=f"Failed to get PR diff: {e}",
        )

    if not pr_diff.strip():
        return UpdateError(
            success=False,
            error="empty_diff",
            message="PR diff is empty",
        )

    # Truncate if needed
    diff_content, _ = truncate_diff(pr_diff)

    # Get branch context
    current_branch = git.get_current_branch(repo_root) or branch
    parent_branch = git.detect_trunk_branch(repo_root)

    # Generate summary via Claude
    prompt = _build_summary_prompt(diff_content, current_branch, parent_branch)
    result = executor.execute_prompt(prompt, model="haiku", cwd=repo_root)

    if not result.success:
        return UpdateError(
            success=False,
            error="claude_failed",
            message=f"Claude execution failed: {result.error}",
        )

    summary = result.output

    # Build footer and compose body
    footer = build_pr_body_footer(pr_number=pr_number, issue_number=issue_number)
    body = f"""## Summary

{summary}
{footer}"""

    # Write to temp file and call gh pr edit
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(body)
        temp_path = Path(f.name)

    try:
        subprocess.run(
            ["gh", "pr", "edit", branch, "--body-file", str(temp_path)],
            check=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        temp_path.unlink(missing_ok=True)
        return UpdateError(
            success=False,
            error="gh_edit_failed",
            message=f"Failed to update PR: {e.stderr}",
        )
    finally:
        temp_path.unlink(missing_ok=True)

    return UpdateSuccess(
        success=True,
        pr_number=pr_number,
        message="PR body updated successfully",
    )


@click.command(name="update-pr-body")
@click.option("--branch", required=True, help="Branch name to find PR for")
@click.option("--issue-number", type=int, required=False, help="Issue number to close")
@click.pass_context
def update_pr_body(
    ctx: click.Context,
    branch: str,
    issue_number: int | None,
) -> None:
    """Update PR body with generated summary and footer.

    Consolidates the full PR body update workflow: finds PR for branch, generates
    summary via Claude, and updates PR body via GitHub CLI.
    """
    github = require_github(ctx)
    git = require_git(ctx)
    executor = require_prompt_executor(ctx)
    repo_root = require_repo_root(ctx)

    result = _update_pr_body_impl(github, git, executor, repo_root, branch, issue_number)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, UpdateError):
        raise SystemExit(1)
