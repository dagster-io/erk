"""Create worktree from GitHub issue with erk-plan label.

This kit CLI command provides deterministic worktree creation from GitHub issues,
replacing the non-deterministic agent-based workflow.

Usage:
    dot-agent run erk create-wt-from-issue <issue-number-or-url>

Output:
    User-friendly formatted output with next steps

Exit Codes:
    0: Success (worktree created)
    1: Error (parsing failed, issue not found, missing label, etc.)

Examples:
    $ dot-agent run erk create-wt-from-issue 776
    ✅ Worktree created from issue #776: **feature-name**

    Branch: `issue-776-25-11-22`
    Location: `/path/to/worktree`
    Plan: `.impl/plan.md`
    Issue: https://github.com/owner/repo/issues/776

    **Next step:**

    `erk checkout issue-776-25-11-22 && claude --permission-mode acceptEdits "/erk:plan-implement"`

    $ dot-agent run erk create-wt-from-issue https://github.com/owner/repo/issues/776
    (same as above)
"""

from dataclasses import dataclass
from pathlib import Path

import click
from erk_shared.github.metadata import update_plan_header_worktree_name
from erk_shared.impl_folder import save_issue_reference
from erk_shared.integrations.erk_wt import ErkWtKit


@dataclass
class WorktreeCreationSuccess:
    """Successful worktree creation result.

    Attributes:
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        worktree_name: Name of created worktree
        worktree_path: Absolute path to worktree
        branch_name: Git branch name
    """

    issue_number: int
    issue_url: str
    worktree_name: str
    worktree_path: str
    branch_name: str


def has_erk_plan_label(labels: list[str]) -> bool:
    """Check if erk-plan label is present.

    Args:
        labels: List of label names

    Returns:
        True if erk-plan label present, False otherwise
    """
    return "erk-plan" in labels


def create_wt_from_issue_impl(
    issue_reference: str,
    ops: ErkWtKit,
) -> tuple[bool, str | WorktreeCreationSuccess]:
    """Pure business logic for creating worktree from issue.

    Args:
        issue_reference: Issue number or GitHub URL
        ops: Operations interface for subprocess calls

    Returns:
        Tuple of (success, result) where:
        - success=True: result is WorktreeCreationSuccess
        - success=False: result is error message string
    """
    # Step 1: Parse issue reference
    parse_result = ops.parse_issue_reference(issue_reference)
    if not parse_result.success:
        return (False, f"Failed to parse issue reference: {parse_result.message}")

    if parse_result.issue_number is None:
        return (False, "Parse succeeded but no issue number returned")

    issue_number = parse_result.issue_number

    # Step 2: Fetch issue from GitHub
    issue_data = ops.fetch_issue(issue_number)
    if issue_data is None:
        return (
            False,
            f"Failed to fetch issue #{issue_number} from GitHub. "
            "Check that the issue exists and gh CLI is authenticated.",
        )

    # Step 3: Check for erk-plan label
    if not has_erk_plan_label(issue_data.labels):
        label_list = ", ".join(issue_data.labels) if issue_data.labels else "none"
        return (
            False,
            f"Issue #{issue_number} does not have the 'erk-plan' label.\n"
            f"Current labels: {label_list}\n"
            "Add the 'erk-plan' label to the issue and try again.",
        )

    # Step 4: Extract plan from issue body
    body = issue_data.body
    if not body or not body.strip():
        return (False, f"Issue #{issue_number} has no body content")

    # Step 5: Create worktree
    worktree_result = ops.create_worktree(body)
    if not worktree_result.success:
        return (
            False,
            f"Failed to create worktree from issue #{issue_number}. "
            "Check erk command output for details.",
        )

    if (
        worktree_result.worktree_name is None
        or worktree_result.worktree_path is None
        or worktree_result.branch_name is None
    ):
        return (False, "Worktree creation succeeded but missing required fields")

    # Step 6: Update issue with actual worktree name
    updated_body = update_plan_header_worktree_name(
        issue_body=body,
        worktree_name=worktree_result.worktree_name,
    )
    ops.update_issue_body(issue_number, updated_body)

    # Step 7: Save issue reference to .impl/issue.json
    impl_dir = Path(worktree_result.worktree_path) / ".impl"
    if impl_dir.exists():
        save_issue_reference(impl_dir, issue_number, issue_data.url)

    # Step 8: Post GitHub comment (non-fatal)
    ops.post_creation_comment(
        issue_number,
        worktree_result.worktree_name,
        worktree_result.branch_name,
    )
    # Non-fatal: continue even if comment fails

    return (
        True,
        WorktreeCreationSuccess(
            issue_number=issue_number,
            issue_url=issue_data.url,
            worktree_name=worktree_result.worktree_name,
            worktree_path=worktree_result.worktree_path,
            branch_name=worktree_result.branch_name,
        ),
    )


@click.command(name="create-wt-from-issue")
@click.argument("issue_reference")
@click.pass_context
def create_wt_from_issue(ctx: click.Context, issue_reference: str) -> None:
    """Create worktree from GitHub issue with erk-plan label.

    ISSUE_REFERENCE: GitHub issue number or full URL
    """
    from erk_shared.integrations.erk_wt import RealErkWtKit

    ops = RealErkWtKit()
    success, result = create_wt_from_issue_impl(issue_reference, ops)

    if not success:
        click.echo(click.style("Error: ", fg="red") + str(result), err=True)
        raise SystemExit(1)

    # success=True, result is WorktreeCreationSuccess
    if not isinstance(result, WorktreeCreationSuccess):
        click.echo(
            click.style("Error: ", fg="red") + "Unexpected result type",
            err=True,
        )
        raise SystemExit(1)

    # Display success output
    click.echo(f"✅ Worktree created from issue #{result.issue_number}: **{result.worktree_name}**")
    click.echo("")
    click.echo(f"Branch: `{result.branch_name}`")
    click.echo(f"Location: `{result.worktree_path}`")
    click.echo("Plan: `.impl/plan.md`")
    click.echo(f"Issue: {result.issue_url}")
    click.echo("")
    click.echo("**Next step:**")
    click.echo("")
    click.echo(
        f"`erk checkout {result.branch_name} && "
        f'claude --permission-mode acceptEdits "/erk:plan-implement"`'
    )
