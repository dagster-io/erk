"""Generate enhanced PR comment for pr-address workflow.

This exec command generates a detailed PR comment summarizing changes made
by the pr-address workflow. It reads a diff from stdin and uses Claude to
generate a human-readable summary.

Usage:
    git diff $PRE_HEAD..HEAD | erk exec generate-pr-address-summary \
        --pr-number 123 \
        --pre-head abc1234 \
        --model-name claude-sonnet-4-5 \
        --run-url https://github.com/owner/repo/actions/runs/789 \
        --job-status success

Output:
    Complete markdown comment body (including marker for idempotent updates)

Exit Codes:
    0: Success
    1: Error (Claude failure, invalid job status)

Examples:
    # Success with changes
    $ echo "+added line" | erk exec generate-pr-address-summary \
        --pr-number 123 --pre-head abc --run-url URL --job-status success
    <!-- erk:pr-address-run -->
    ## PR Review Comments Addressed
    ...

    # Success with no changes
    $ echo "" | erk exec generate-pr-address-summary \
        --pr-number 123 --pre-head abc --run-url URL --job-status success
    <!-- erk:pr-address-run -->
    ## PR Review Comments Addressed
    No changes were needed...
"""

import sys

import click

from erk_shared.context.helpers import (
    require_git,
    require_prompt_executor,
    require_repo_root,
)

# Marker for idempotent comment updates
PR_ADDRESS_MARKER = "<!-- erk:pr-address-run -->"


def _build_summary_prompt(diff_content: str) -> str:
    """Build prompt for summarizing pr-address changes.

    Args:
        diff_content: Git diff showing changes made

    Returns:
        Prompt text for Claude
    """
    return f"""Summarize the following code changes made to address PR review comments.

Write a brief (2-5 sentences), human-readable summary of what was changed and why.
Focus on the semantic meaning of the changes, not the literal lines changed.
Use bullet points if multiple distinct changes were made.
Do not include code blocks or diffs in your response.

```diff
{diff_content}
```

Provide only the summary text, nothing else."""


def _build_success_comment(
    *,
    pr_number: int,
    summary: str,
    model_name: str,
    run_url: str,
    commit_count: int,
) -> str:
    """Build comment body for successful pr-address run with changes.

    Args:
        pr_number: PR number that was addressed
        summary: Claude-generated summary of changes
        model_name: Claude model used
        run_url: URL to workflow run
        commit_count: Number of commits added

    Returns:
        Complete markdown comment body with marker
    """
    parts = [
        PR_ADDRESS_MARKER,
        "## PR Review Comments Addressed",
        "",
        "This PR was updated by an automated process triggered by:",
        "```",
        f"erk pr address-remote {pr_number}",
        "```",
        "",
        "### What is this?",
        "",
        "[Erk](https://github.com/schrockn/erk) is a CLI tool for plan-oriented agentic",
        "engineering. The `pr-address` workflow uses Claude to read PR review comments",
        "and address them automatically.",
        "",
        "### Changes Made",
        "",
        summary,
        "",
        "### Details",
        "",
        f"- **Model:** {model_name}",
        f"- **Workflow run:** [View details]({run_url})",
        f"- **Commits added:** {commit_count}",
        "",
        "---",
        "*Automated by erk pr-address workflow*",
    ]
    return "\n".join(parts)


def _build_no_changes_comment(
    *,
    pr_number: int,
    model_name: str,
    run_url: str,
) -> str:
    """Build comment body when no changes were needed.

    Args:
        pr_number: PR number that was addressed
        model_name: Claude model used
        run_url: URL to workflow run

    Returns:
        Complete markdown comment body with marker
    """
    parts = [
        PR_ADDRESS_MARKER,
        "## PR Review Comments Addressed",
        "",
        "This PR was reviewed by an automated process triggered by:",
        "```",
        f"erk pr address-remote {pr_number}",
        "```",
        "",
        "### Result",
        "",
        "No changes were needed to address the review comments.",
        "",
        "This could mean:",
        "- Comments were already addressed in a previous commit",
        "- Comments were informational (no action required)",
        "- Claude determined the existing code already satisfies the feedback",
        "",
        "### Details",
        "",
        f"- **Model:** {model_name}",
        f"- **Workflow run:** [View details]({run_url})",
        "",
        "---",
        "*Automated by erk pr-address workflow*",
    ]
    return "\n".join(parts)


def _build_failure_comment(
    *,
    pr_number: int,
    run_url: str,
) -> str:
    """Build comment body when workflow failed.

    Args:
        pr_number: PR number that was addressed
        run_url: URL to workflow run

    Returns:
        Complete markdown comment body with marker
    """
    parts = [
        PR_ADDRESS_MARKER,
        "## PR Review Comment Addressing Failed",
        "",
        "The automated process triggered by:",
        "```",
        f"erk pr address-remote {pr_number}",
        "```",
        "encountered an error.",
        "",
        f"**[View workflow logs]({run_url})** for details.",
        "",
        "### What to do",
        "",
        "- Check the workflow logs for error details",
        "- You can manually address the review comments",
        "- Or retry by running `erk pr address-remote` again",
        "",
        "---",
        "*Automated by erk pr-address workflow*",
    ]
    return "\n".join(parts)


def _count_commits(git, repo_root, pre_head: str) -> int:
    """Count commits between pre_head and HEAD.

    Args:
        git: Git gateway
        repo_root: Repository root path
        pre_head: Commit SHA before Claude ran

    Returns:
        Number of commits added
    """
    # count_commits_ahead accepts any ref (branch or commit SHA)
    return git.analysis.count_commits_ahead(repo_root, pre_head)


@click.command(name="generate-pr-address-summary")
@click.option("--pr-number", type=int, required=True, help="PR number being addressed")
@click.option(
    "--pre-head",
    type=str,
    required=True,
    help="Commit SHA before Claude ran",
)
@click.option(
    "--model-name",
    type=str,
    default="claude-sonnet-4-5",
    help="Claude model name used",
)
@click.option(
    "--run-url",
    type=str,
    required=True,
    help="URL to the workflow run",
)
@click.option(
    "--job-status",
    type=click.Choice(["success", "failure"]),
    required=True,
    help="Job status (success or failure)",
)
@click.pass_context
def generate_pr_address_summary(
    ctx: click.Context,
    *,
    pr_number: int,
    pre_head: str,
    model_name: str,
    run_url: str,
    job_status: str,
) -> None:
    """Generate enhanced PR comment for pr-address workflow.

    Reads diff from stdin and generates a detailed summary comment.
    For successful runs with changes, uses Claude to summarize the diff.
    For no-changes or failure cases, generates appropriate static messages.

    The output includes a marker for idempotent updates via post-or-update-pr-summary.
    """
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    # Handle failure case first (no diff needed)
    if job_status == "failure":
        comment = _build_failure_comment(
            pr_number=pr_number,
            run_url=run_url,
        )
        click.echo(comment, nl=False)
        return

    # Read diff from stdin
    diff_content = sys.stdin.read().strip()

    # Count commits for the summary
    commit_count = _count_commits(git, repo_root, pre_head)

    # No changes case
    if not diff_content:
        comment = _build_no_changes_comment(
            pr_number=pr_number,
            model_name=model_name,
            run_url=run_url,
        )
        click.echo(comment, nl=False)
        return

    # Success with changes - use Claude to summarize
    executor = require_prompt_executor(ctx)

    prompt = _build_summary_prompt(diff_content)
    result = executor.execute_prompt(prompt, model="haiku", cwd=repo_root)

    if not result.success:
        click.echo(f"Error: Claude execution failed: {result.error}", err=True)
        raise SystemExit(1)

    summary = result.output.strip()
    if not summary:
        summary = "Changes were made to address review comments."

    comment = _build_success_comment(
        pr_number=pr_number,
        summary=summary,
        model_name=model_name,
        run_url=run_url,
        commit_count=commit_count,
    )
    click.echo(comment, nl=False)
