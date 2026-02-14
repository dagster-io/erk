"""Update PR title and body using AI-generated description.

This command generates an AI-powered PR title and body from the full diff
between the current branch and its parent, then updates the PR on GitHub.

Unlike `erk pr submit`, this does NOT amend the local commit or push changes.
It only updates the PR's title and body, preserving existing header and footer
metadata.
"""

import uuid
from pathlib import Path

import click

from erk.cli.commands.pr.shared import (
    build_plan_details_section,
    render_progress,
    require_claude_available,
    run_commit_message_generation,
)
from erk.core.commit_message_generator import CommitMessageGenerator
from erk.core.context import ErkContext
from erk.core.plan_context_provider import PlanContextProvider
from erk_shared.gateway.github.pr_footer import (
    extract_footer_from_body,
    extract_header_from_body,
    rebuild_pr_body,
)
from erk_shared.gateway.github.types import BodyText, PRNotFound
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.diff_extraction import execute_diff_extraction


@click.command("update-description")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.option("--session-id", default=None, help="Session ID for scratch file isolation")
@click.pass_obj
def pr_update_description(ctx: ErkContext, *, debug: bool, session_id: str | None) -> None:
    """Update PR title and body with AI-generated description.

    Analyzes the full diff between the current branch and its parent,
    generates a descriptive title and body using Claude, and updates the
    PR on GitHub. Preserves existing header and footer metadata.

    Examples:

    \b
      # Update PR description
      erk pr update-description

      # With session ID for scratch isolation
      erk pr update-description --session-id "abc123"
    """
    _execute_update_description(ctx, debug=debug, session_id=session_id)


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

    current_branch = ctx.git.branch.get_current_branch(cwd)
    if current_branch is None:
        raise click.ClickException("Not on a branch (detached HEAD state)")

    repo_root = ctx.git.repo.get_repository_root(cwd)
    trunk_branch = ctx.git.branch.detect_trunk_branch(repo_root)
    parent_branch = (
        ctx.branch_manager.get_parent_branch(Path(repo_root), current_branch) or trunk_branch
    )

    # Find PR for this branch
    pr_result = ctx.github.get_pr_for_branch(repo_root, current_branch)
    if isinstance(pr_result, PRNotFound):
        raise click.ClickException(
            f"No pull request found for branch '{current_branch}'\n\n"
            "Create a PR first with `gt submit` or `gh pr create`."
        )

    pr_number = pr_result.number
    existing_body = pr_result.body

    click.echo(click.style(f"   Branch: {current_branch}", dim=True))
    click.echo(click.style(f"   Parent: {parent_branch}", dim=True))
    click.echo(click.style(f"   PR: #{pr_number}", dim=True))
    click.echo("")

    # Phase 2: Diff extraction
    click.echo(click.style("Phase 2: Getting diff", bold=True))
    diff_file = _run_diff_extraction(
        ctx,
        cwd=cwd,
        session_id=resolved_session_id,
        base_branch=parent_branch,
        debug=debug,
    )

    if diff_file is None:
        raise click.ClickException("Failed to extract diff for AI analysis")

    click.echo("")

    # Phase 3: Plan context
    click.echo(click.style("Phase 3: Fetching plan context", bold=True))

    plan_provider = PlanContextProvider(ctx.github_issues)
    plan_context = plan_provider.get_plan_context(
        repo_root=Path(repo_root),
        branch_name=current_branch,
    )

    if plan_context is not None:
        click.echo(
            click.style(
                f"   Incorporating plan from issue #{plan_context.issue_number}",
                fg="green",
            )
        )
        if plan_context.objective_summary is not None:
            click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
    else:
        click.echo(click.style("   No linked plan found", dim=True))
    click.echo("")

    # Phase 4: AI generation
    click.echo(click.style("Phase 4: Generating PR description", bold=True))

    commit_messages = ctx.git.commit.get_commit_messages_since(cwd, parent_branch)

    msg_gen = CommitMessageGenerator(ctx.prompt_executor)
    msg_result = run_commit_message_generation(
        generator=msg_gen,
        diff_file=diff_file,
        repo_root=Path(repo_root),
        current_branch=current_branch,
        parent_branch=parent_branch,
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

    # Preserve header and footer from existing PR body
    header = extract_header_from_body(existing_body)
    footer = extract_footer_from_body(existing_body)

    # Embed plan details if available
    content = pr_body
    if plan_context is not None:
        content = pr_body + build_plan_details_section(plan_context)

    # Rebuild body with preserved header/footer
    final_body = rebuild_pr_body(
        header=header,
        content=content,
        footer=footer or "",
    )

    ctx.github.update_pr_title_and_body(
        repo_root=repo_root,
        pr_number=pr_number,
        title=pr_title,
        body=BodyText(content=final_body),
    )

    click.echo(click.style("   PR updated", fg="green"))
    click.echo("")

    # Phase 6: Cleanup
    if diff_file is not None and diff_file.exists():
        try:
            diff_file.unlink()
        except OSError:
            pass

    click.echo(f"PR #{pr_number} updated: {pr_title}")


def _run_diff_extraction(
    ctx: ErkContext,
    *,
    cwd: Path,
    session_id: str,
    base_branch: str,
    debug: bool,
) -> Path | None:
    """Run diff extraction phase.

    Uses the same execute_diff_extraction as submit/summarize, but with
    pr_number=0 since we're updating an existing PR's description.
    """
    result: Path | None = None

    for event in execute_diff_extraction(
        ctx, cwd, pr_number=0, session_id=session_id, base_branch=base_branch
    ):
        if isinstance(event, ProgressEvent):
            if debug:
                render_progress(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    return result
