#!/usr/bin/env python3
"""Generate complete PR body with summary and footer.

This command composes a complete PR body by generating a summary from the PR diff
using Claude, then combining it with a standardized footer. Replaces multi-command
bash composition in workflows.

Usage:
    erk kit exec erk generate-pr-body --pr-number 123 --issue-number 456

Output:
    JSON object with success status and body

Exit Codes:
    0: Success (body generated)
    1: Error (PR not found, empty diff, Claude failure)

Examples:
    $ erk kit exec erk generate-pr-body --pr-number 1895 --issue-number 123
    {
      "success": true,
      "body": "## Summary\\n\\nFix authentication flow...\\n\\n---\\n\\nCloses #123\\n\\n..."
    }
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.integrations.gt.prompts import COMMIT_MESSAGE_SYSTEM_PROMPT, truncate_diff
from erk_shared.prompt_executor import PromptExecutor

from dot_agent_kit.context_helpers import (
    require_git,
    require_github,
    require_prompt_executor,
    require_repo_root,
)


@dataclass
class GenerateSuccess:
    """Success result when PR body was generated."""

    success: bool
    body: str


@dataclass
class GenerateError:
    """Error result when generation fails."""

    success: bool
    error: Literal["empty_diff", "claude_failed", "pr_diff_failed"]
    message: str


def _build_summary_prompt(diff_content: str, current_branch: str, parent_branch: str) -> str:
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


def _generate_pr_body_impl(
    github: GitHub,
    git: Git,
    executor: PromptExecutor,
    repo_root: Path,
    pr_number: int,
    issue_number: int | None,
) -> GenerateSuccess | GenerateError:
    """Generate complete PR body with summary and footer.

    Args:
        github: GitHub interface for PR operations
        git: Git interface for branch operations
        executor: Prompt executor for Claude
        repo_root: Repository root directory
        pr_number: PR number to generate body for
        issue_number: Optional issue number to include in footer

    Returns:
        GenerateSuccess with body, or GenerateError on failure
    """
    # Get PR diff
    try:
        pr_diff = github.get_pr_diff(repo_root, pr_number)
    except RuntimeError as e:
        return GenerateError(
            success=False,
            error="pr_diff_failed",
            message=f"Failed to get PR diff: {e}",
        )

    if not pr_diff.strip():
        return GenerateError(
            success=False,
            error="empty_diff",
            message="PR diff is empty",
        )

    # Truncate if needed
    diff_content, _ = truncate_diff(pr_diff)

    # Get branch context
    current_branch = git.get_current_branch(repo_root) or f"pr-{pr_number}"
    parent_branch = git.detect_trunk_branch(repo_root)

    # Generate summary via Claude
    prompt = _build_summary_prompt(diff_content, current_branch, parent_branch)
    result = executor.execute_prompt(prompt, model="haiku", cwd=repo_root)

    if not result.success:
        return GenerateError(
            success=False,
            error="claude_failed",
            message=f"Claude execution failed: {result.error}",
        )

    summary = result.output

    # Build footer
    footer = build_pr_body_footer(pr_number=pr_number, issue_number=issue_number)

    # Compose full body
    body = f"""## Summary

{summary}
{footer}"""

    return GenerateSuccess(
        success=True,
        body=body,
    )


@click.command(name="generate-pr-body")
@click.option("--pr-number", type=int, required=True, help="PR number to generate body for")
@click.option("--issue-number", type=int, required=False, help="Issue number to close")
@click.pass_context
def generate_pr_body(
    ctx: click.Context,
    pr_number: int,
    issue_number: int | None,
) -> None:
    """Generate complete PR body with summary and footer.

    Generates a PR summary from the diff using Claude, then combines it with
    a standardized footer containing the checkout command and optional issue
    closing reference.
    """
    github = require_github(ctx)
    git = require_git(ctx)
    executor = require_prompt_executor(ctx)
    repo_root = require_repo_root(ctx)

    result = _generate_pr_body_impl(github, git, executor, repo_root, pr_number, issue_number)

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    # Exit with error code if failed
    if isinstance(result, GenerateError):
        raise SystemExit(1)
