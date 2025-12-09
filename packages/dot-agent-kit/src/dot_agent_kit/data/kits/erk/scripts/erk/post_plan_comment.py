"""Post plan issue comment with workflow instructions.

This kit CLI command posts a structured comment to a plan issue containing
the plan content and workflow instructions for starting work.

Usage:
    dot-agent run erk post-plan-issue-comment --issue-number 123 \\
        --plan-content "..." --plan-title "..."
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.issues import RealGitHubIssues
from erk_shared.github.metadata import (
    create_plan_issue_block,
    render_erk_issue_event,
)
from erk_shared.naming import sanitize_worktree_name


@click.command(name="post-plan-comment")
@click.option("--issue-number", required=True, type=int, help="GitHub issue number")
@click.option("--plan-content", required=True, help="Plan markdown content")
@click.option("--plan-title", required=True, help="Plan title for worktree name generation")
@click.option("--plan-file", required=False, help="Optional path to plan file")
def post_plan_comment(
    issue_number: int,
    plan_content: str,
    plan_title: str,
    plan_file: str | None = None,
) -> None:
    """Post plan issue comment with workflow instructions."""
    timestamp = datetime.now(UTC).isoformat()

    # Generate worktree name from title using existing utility
    worktree_name = sanitize_worktree_name(plan_title)

    # Create metadata block
    block = create_plan_issue_block(
        issue_number=issue_number,
        worktree_name=worktree_name,
        timestamp=timestamp,
        plan_file=plan_file,
    )

    # Build workflow instructions
    one_liner = (
        f'claude --permission-mode acceptEdits -p "/erk:create-wt-from-plan-issue '
        f'#{issue_number} {worktree_name}" && erk co {worktree_name} && '
        f'claude --permission-mode acceptEdits "/erk:plan-implement"'
    )
    step_1_cmd = (
        f'claude --permission-mode acceptEdits -p "/erk:create-wt-from-plan-issue '
        f'#{issue_number} {worktree_name}"'
    )
    workflow_instructions = f"""## Quick Start

One-liner to create worktree and start implementation:
```bash
{one_liner}
```

Or step-by-step:

1. Create worktree from this issue:
   ```bash
   {step_1_cmd}
   ```

2. Navigate to the worktree:
   ```bash
   erk co {worktree_name}
   ```

3. Implement the plan:
   ```bash
   claude --permission-mode acceptEdits "/erk:plan-implement"
   ```"""

    # Combine plan content and workflow instructions
    description = f"{plan_content}\n\n---\n\n{workflow_instructions}"

    # Render comment
    comment_body = render_erk_issue_event(
        title=f"📋 {plan_title}",
        metadata=block,
        description=description,
    )

    # Post comment
    github = RealGitHubIssues()
    repo_root = Path.cwd()
    github.add_comment(repo_root, issue_number, comment_body)

    # Output success
    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue_number,
                "worktree_name": worktree_name,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    post_plan_comment()
