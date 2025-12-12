"""Generate PR summary from PR diff.

This kit CLI command generates a PR summary by analyzing the PR diff
using Claude. It uses the same prompt as commit message generation but
does NOT include commit messages (which may contain misleading info
about .worker-impl/ deletions).

This is used by the GitHub Actions workflow when updating PR bodies
after implementation.

Usage:
    erk kit exec erk generate-pr-summary --pr-number 123

Output:
    PR summary text (title on first line, body follows)

Exit Codes:
    0: Success
    1: Error (missing pr-number, no diff, Claude failure)

Examples:
    $ erk kit exec erk generate-pr-summary --pr-number 1895
    Fix authentication flow for OAuth providers

    This PR fixes the OAuth authentication flow...
    ...
"""

import click

from erk_shared.context.helpers import (
    require_git,
    require_github,
    require_prompt_executor,
    require_repo_root,
)
from erk_shared.integrations.gt.prompts import COMMIT_MESSAGE_SYSTEM_PROMPT, truncate_diff


def _build_prompt(diff_content: str, current_branch: str, parent_branch: str) -> str:
    """Build prompt for PR summary generation.

    Note: We deliberately do NOT include commit messages here, unlike
    CommitMessageGenerator. The commit messages may contain info about
    .worker-impl/ deletions that don't appear in the final PR diff.
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


@click.command(name="generate-pr-summary")
@click.option("--pr-number", type=int, required=True, help="PR number to summarize")
@click.pass_context
def generate_pr_summary(ctx: click.Context, pr_number: int) -> None:
    """Generate PR summary from PR diff using Claude.

    Analyzes the PR diff (what GitHub shows) and generates a summary.
    Does NOT use commit messages, which may contain misleading info
    about files that net to zero in the final diff.

    Args:
        pr_number: The PR number to analyze
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    git = require_git(ctx)
    executor = require_prompt_executor(ctx)

    # Get PR diff
    try:
        pr_diff = github.get_pr_diff(repo_root, pr_number)
    except RuntimeError as e:
        click.echo(f"Error: Failed to get PR diff: {e}", err=True)
        raise SystemExit(1) from e

    if not pr_diff.strip():
        click.echo("Error: PR diff is empty", err=True)
        raise SystemExit(1)

    # Truncate if needed
    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated:
        click.echo("Warning: Diff truncated for size", err=True)

    # Get branch context using injected Git
    current_branch = git.get_current_branch(repo_root) or f"pr-{pr_number}"
    parent_branch = git.detect_trunk_branch(repo_root)

    # Build prompt and run Claude via injected executor
    prompt = _build_prompt(diff_content, current_branch, parent_branch)
    result = executor.execute_prompt(prompt, model="haiku", cwd=repo_root)

    if not result.success:
        click.echo(f"Error: Claude execution failed: {result.error}", err=True)
        raise SystemExit(1) from None

    # Output the summary (no trailing newline, let caller handle formatting)
    click.echo(result.output, nl=False)
