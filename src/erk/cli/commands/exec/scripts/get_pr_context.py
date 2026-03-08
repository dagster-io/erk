"""Get PR context for agent-driven description generation.

Outputs JSON to stdout with branch info, PR info, diff file path,
commit messages, and plan context. Designed for use by Claude Code
agents that generate PR descriptions natively rather than via subprocess.

Usage:
    erk exec get-pr-context

Exit Codes:
    0: Success (JSON output on stdout)
    1: Error (no branch, no PR, diff extraction failure)
"""

import json
import uuid

import click

from erk.cli.commands.pr.repo_resolution import get_remote_github
from erk.cli.commands.pr.shared import (
    discover_branch_context,
    echo_plan_context_status,
    run_diff_extraction,
)
from erk.core.plan_context_provider import PlanContextProvider
from erk_shared.context.helpers import require_context
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.types import PRNotFound


@click.command(name="get-pr-context")
@click.option("--debug", is_flag=True, help="Show diagnostic output")
@click.pass_context
def get_pr_context(ctx: click.Context, *, debug: bool) -> None:
    """Output JSON with branch, PR, diff, commits, and plan context.

    Gathers all the context an agent needs to generate a PR title and body,
    then outputs it as a single JSON object to stdout.
    """
    erk_ctx = require_context(ctx)
    cwd = erk_ctx.cwd
    session_id = str(uuid.uuid4())

    # Discovery
    discovery = discover_branch_context(erk_ctx, cwd=cwd)

    # Find PR
    pr_result = erk_ctx.github.get_pr_for_branch(discovery.repo_root, discovery.current_branch)
    if isinstance(pr_result, PRNotFound):
        raise click.ClickException(
            f"No pull request found for branch '{discovery.current_branch}'\n\n"
            "Create a PR first with `erk exec push-and-create-pr`."
        )

    # Diff extraction
    diff_file = run_diff_extraction(
        erk_ctx,
        cwd=cwd,
        session_id=session_id,
        base_branch=discovery.parent_branch,
        debug=debug,
    )

    if diff_file is None:
        raise click.ClickException("Failed to extract diff")

    # Commit messages
    commit_messages = erk_ctx.git.commit.get_commit_messages_since(cwd, discovery.parent_branch)

    # Plan context
    plan_provider = PlanContextProvider(
        plan_backend=erk_ctx.plan_backend, remote_github=get_remote_github(erk_ctx)
    )
    if isinstance(erk_ctx.repo, NoRepoSentinel) or erk_ctx.repo.github is None:
        raise click.ClickException("Repository has no GitHub remote configured")
    plan_context = plan_provider.get_plan_context(
        repo_root=discovery.repo_root,
        branch_name=discovery.current_branch,
        owner=erk_ctx.repo.github.owner,
        repo=erk_ctx.repo.github.repo,
    )

    if debug:
        echo_plan_context_status(plan_context)

    # Build output
    plan_context_data: dict[str, str | None] | None = None
    if plan_context is not None:
        plan_context_data = {
            "plan_id": plan_context.plan_id,
            "plan_content": plan_context.plan_content,
            "objective_summary": plan_context.objective_summary,
        }

    output = {
        "branch": {
            "current": discovery.current_branch,
            "parent": discovery.parent_branch,
        },
        "pr": {
            "number": pr_result.number,
            "url": pr_result.url,
        },
        "diff_file": str(diff_file),
        "commit_messages": commit_messages if commit_messages is not None else [],
        "plan_context": plan_context_data,
    }

    click.echo(json.dumps(output, indent=2))
