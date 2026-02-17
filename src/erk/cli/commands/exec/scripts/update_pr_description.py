"""Update PR title and body using AI-generated description.

This exec command generates an AI-powered PR title and body from the full diff
between the current branch and its parent, then updates the PR on GitHub.

Unlike `erk pr submit`, this does NOT amend the local commit or push changes.
It only updates the PR's title and body, preserving existing header and footer
metadata.

Usage:
    erk exec update-pr-description
    erk exec update-pr-description --session-id "abc123"

Exit Codes:
    0: Success
    1: Error (no PR, Claude unavailable, diff extraction failure)
"""

import uuid
from pathlib import Path

import click

from erk.cli.commands.pr.shared import (
    IssueLinkageMismatch,
    assemble_pr_body,
    cleanup_diff_file,
    discover_branch_context,
    discover_issue_for_footer,
    echo_plan_context_status,
    require_claude_available,
    run_commit_message_generation,
    run_diff_extraction,
)
from erk.core.commit_message_generator import CommitMessageGenerator
from erk.core.context import ErkContext
from erk.core.plan_context_provider import PlanContextProvider
from erk_shared.context.helpers import require_context
from erk_shared.gateway.github.pr_footer import extract_header_from_body
from erk_shared.gateway.github.types import BodyText, PRNotFound


@click.command(name="update-pr-description")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.option("--session-id", default=None, help="Session ID for scratch file isolation")
@click.pass_context
def update_pr_description(ctx: click.Context, *, debug: bool, session_id: str | None) -> None:
    """Update PR title and body with AI-generated description.

    Analyzes the full diff between the current branch and its parent,
    generates a descriptive title and body using Claude, and updates the
    PR on GitHub. Preserves existing header and footer metadata.
    """
    erk_ctx = require_context(ctx)
    _execute_update_description(erk_ctx, debug=debug, session_id=session_id)


def _execute_update_description(ctx: ErkContext, *, debug: bool, session_id: str | None) -> None:
    """Execute the update-description pipeline."""
    # Verify Claude is available
    require_claude_available(ctx)

    cwd = Path.cwd()
    if session_id is not None:
        resolved_session_id = session_id
    else:
        resolved_session_id = str(uuid.uuid4())

    # Phase 1: Discovery
    click.echo(click.style("Phase 1: Discovery", bold=True))

    discovery = discover_branch_context(ctx, cwd=cwd)

    # Find PR for this branch
    pr_result = ctx.github.get_pr_for_branch(discovery.repo_root, discovery.current_branch)
    if isinstance(pr_result, PRNotFound):
        raise click.ClickException(
            f"No pull request found for branch '{discovery.current_branch}'\n\n"
            "Create a PR first with `gt submit` or `gh pr create`."
        )

    pr_number = pr_result.number
    existing_body = pr_result.body

    click.echo(click.style(f"   Branch: {discovery.current_branch}", dim=True))
    click.echo(click.style(f"   Parent: {discovery.parent_branch}", dim=True))
    click.echo(click.style(f"   PR: #{pr_number}", dim=True))
    click.echo("")

    # Phase 2: Diff extraction
    click.echo(click.style("Phase 2: Getting diff", bold=True))
    diff_file = run_diff_extraction(
        ctx,
        cwd=cwd,
        session_id=resolved_session_id,
        base_branch=discovery.parent_branch,
        debug=debug,
    )

    if diff_file is None:
        raise click.ClickException("Failed to extract diff for AI analysis")

    click.echo("")

    # Phase 3: Plan context
    click.echo(click.style("Phase 3: Fetching plan context", bold=True))

    plan_provider = PlanContextProvider(plan_store=ctx.plan_store, github_issues=ctx.github_issues)
    plan_context = plan_provider.get_plan_context(
        repo_root=discovery.repo_root,
        branch_name=discovery.current_branch,
    )

    echo_plan_context_status(plan_context)

    # Phase 4: AI generation
    click.echo(click.style("Phase 4: Generating PR description", bold=True))

    commit_messages = ctx.git.commit.get_commit_messages_since(cwd, discovery.parent_branch)

    msg_gen = CommitMessageGenerator(ctx.prompt_executor)
    msg_result = run_commit_message_generation(
        generator=msg_gen,
        diff_file=diff_file,
        repo_root=discovery.repo_root,
        current_branch=discovery.current_branch,
        parent_branch=discovery.parent_branch,
        commit_messages=commit_messages,
        plan_context=plan_context,
        debug=debug,
    )

    if not msg_result.success:
        raise click.ClickException(f"Failed to generate message: {msg_result.error_message}")

    click.echo("")

    # Phase 5: Update PR
    click.echo(click.style("Phase 5: Updating PR", bold=True))

    pr_title = msg_result.title or "Update"
    pr_body = msg_result.body or ""

    # Discover issue number and assemble PR body (shared with rewrite command)
    impl_dir = cwd / ".impl"
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None

    issue_discovery = discover_issue_for_footer(
        impl_dir=impl_dir,
        branch_name=discovery.current_branch,
        existing_pr_body=existing_body,
        plans_repo=plans_repo,
    )
    if isinstance(issue_discovery, IssueLinkageMismatch):
        raise click.ClickException(issue_discovery.message)

    final_body = assemble_pr_body(
        body=pr_body,
        plan_context=plan_context,
        pr_number=pr_number,
        issue_number=issue_discovery.issue_number,
        plans_repo=issue_discovery.plans_repo,
        header=extract_header_from_body(existing_body),
    )

    ctx.github.update_pr_title_and_body(
        repo_root=discovery.repo_root,
        pr_number=pr_number,
        title=pr_title,
        body=BodyText(content=final_body),
    )

    click.echo(click.style("   PR updated", fg="green"))
    click.echo("")

    # Phase 6: Cleanup
    cleanup_diff_file(diff_file)

    click.echo(f"PR #{pr_number} updated: {pr_title}")
