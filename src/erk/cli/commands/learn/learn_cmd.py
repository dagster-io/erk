"""Learn command for extracting insights from plan implementations.

This command discovers all Claude Code sessions associated with a plan issue
and outputs their paths for use in extraction workflows.
"""

import json
from dataclasses import asdict, dataclass

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.learn.tracking import track_learn_invocation
from erk_shared.output.output import user_output
from erk_shared.sessions.discovery import (
    find_sessions_for_plan,
    get_readable_sessions,
)


@dataclass(frozen=True)
class LearnResult:
    """Result of learn command."""

    issue_number: int
    planning_session_id: str | None
    implementation_session_ids: list[str]
    learn_session_ids: list[str]
    readable_session_ids: list[str]
    session_paths: list[str]


def _extract_issue_number(identifier: str) -> int | None:
    """Extract issue number from identifier (number or URL).

    Args:
        identifier: Issue number or GitHub issue URL

    Returns:
        Issue number or None if invalid
    """
    # Try direct number
    try:
        return int(identifier)
    except ValueError:
        pass

    # Try URL format: https://github.com/owner/repo/issues/123
    if "/issues/" in identifier:
        parts = identifier.rstrip("/").split("/")
        if parts:
            try:
                return int(parts[-1])
            except ValueError:
                pass

    return None


@click.command("learn")
@click.argument("issue", type=str)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--no-track", is_flag=True, help="Don't post tracking comment to issue")
@click.option("--session-id", default=None, help="Session ID for tracking (passed by Claude hooks)")
@click.pass_obj
def learn_cmd(
    ctx: ErkContext,
    issue: str,
    output_json: bool,
    no_track: bool,
    session_id: str | None,
) -> None:
    """Extract insights from sessions associated with a plan.

    ISSUE can be a plan issue number (e.g., "123") or a full GitHub URL.

    Discovers all Claude Code sessions related to the plan:
    - Planning session (created the plan)
    - Implementation sessions (ran the implementation)
    - Previous learn sessions (already analyzed)

    Outputs session paths for use in extraction workflows.

    Examples:

        erk learn 123

        erk learn https://github.com/org/repo/issues/123 --json
    """
    # Extract issue number
    issue_number = _extract_issue_number(issue)
    if issue_number is None:
        user_output(click.style(f"Error: Invalid issue identifier: {issue}", fg="red"))
        raise SystemExit(1)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Find sessions for the plan
    try:
        sessions_for_plan = find_sessions_for_plan(
            ctx.issues,
            repo_root,
            issue_number,
        )
    except RuntimeError as e:
        user_output(click.style(f"Error: Failed to find sessions: {e}", fg="red"))
        raise SystemExit(1) from e

    # Get readable sessions (ones that exist on disk)
    readable_session_ids = get_readable_sessions(
        sessions_for_plan,
        ctx.claude_installation,
        ctx.cwd,
    )

    # Get paths for readable sessions
    session_paths: list[str] = []
    for session_id in readable_session_ids:
        path = ctx.claude_installation.get_session_path(ctx.cwd, session_id)
        if path is not None:
            session_paths.append(str(path))

    # Build result
    result = LearnResult(
        issue_number=issue_number,
        planning_session_id=sessions_for_plan.planning_session_id,
        implementation_session_ids=sessions_for_plan.implementation_session_ids,
        learn_session_ids=sessions_for_plan.learn_session_ids,
        readable_session_ids=readable_session_ids,
        session_paths=session_paths,
    )

    # Track invocation (unless disabled)
    if not no_track:
        try:
            track_learn_invocation(
                ctx.issues,
                repo_root,
                issue_number,
                session_id=session_id,
                readable_count=len(readable_session_ids),
                total_count=len(sessions_for_plan.all_session_ids()),
            )
        except RuntimeError as e:
            # Non-fatal - tracking failed but we can still output results
            user_output(
                click.style("Warning: ", fg="yellow") + f"Failed to track learn invocation: {e}"
            )

    # Output
    if output_json:
        click.echo(json.dumps(asdict(result), indent=2))
    else:
        _display_human_readable(result)


def _display_human_readable(result: LearnResult) -> None:
    """Display result in human-readable format."""
    user_output(click.style(f"Sessions for plan #{result.issue_number}", bold=True))
    user_output("")

    # Planning session
    if result.planning_session_id:
        user_output(f"Planning session: {click.style(result.planning_session_id, fg='cyan')}")
    else:
        user_output("Planning session: " + click.style("(not tracked)", dim=True))

    # Implementation sessions
    if result.implementation_session_ids:
        user_output(f"Implementation sessions ({len(result.implementation_session_ids)}):")
        for sid in result.implementation_session_ids:
            user_output(f"  - {click.style(sid, fg='green')}")
    else:
        user_output("Implementation sessions: " + click.style("(none)", dim=True))

    # Previous learn sessions
    if result.learn_session_ids:
        user_output(f"Previous learn sessions ({len(result.learn_session_ids)}):")
        for sid in result.learn_session_ids:
            user_output(f"  - {click.style(sid, fg='yellow')}")

    user_output("")

    # Readable sessions summary
    total = len(result.readable_session_ids)
    if total == 0:
        user_output(click.style("No readable sessions found on this machine.", fg="red"))
    else:
        user_output(f"Readable sessions: {click.style(str(total), fg='green', bold=True)}")
        for path in result.session_paths:
            user_output(f"  {click.style(path, dim=True)}")
