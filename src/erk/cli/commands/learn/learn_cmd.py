"""Learn command for extracting insights from plan implementations.

This command discovers all Claude Code sessions associated with a plan issue
and optionally launches Claude with the /erk:learn skill.

Note: Session data retrieval and tracking are handled by separate exec scripts:
- `erk exec get-learn-sessions` - Returns JSON with session data
- `erk exec track-learn-evaluation` - Posts tracking comment to issue
"""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_learn_materials_gist_url,
)
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_confirm, user_output
from erk_shared.sessions.discovery import (
    find_local_sessions_for_project,
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
    local_session_ids: list[str]
    last_remote_impl_at: str | None


def _extract_issue_number(identifier: str) -> int | None:
    """Extract issue number from identifier (number or URL).

    Args:
        identifier: Issue number or GitHub issue URL

    Returns:
        Issue number or None if invalid
    """
    # Try direct number (LBYL: check before converting)
    if identifier.isdigit():
        return int(identifier)

    # Try URL format: https://github.com/owner/repo/issues/123
    if "/issues/" in identifier:
        parts = identifier.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            return int(parts[-1])

    return None


@click.command("learn")
@click.argument("issue", type=str, required=False)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Launch Claude to extract insights without prompting",
)
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Launch Claude with --dangerously-skip-permissions (skip all permission prompts)",
)
@click.pass_obj
def learn_cmd(
    ctx: ErkContext,
    issue: str | None,
    interactive: bool,
    *,
    dangerous: bool,
) -> None:
    """Extract insights from sessions associated with a plan.

    ISSUE can be a plan issue number (e.g., "123") or a full GitHub URL.
    If not provided, infers from current branch name (P{issue}-...).

    Discovers all Claude Code sessions related to the plan:
    - Planning session (created the plan)
    - Implementation sessions (ran the implementation)
    - Previous learn sessions (already analyzed)

    By default, displays sessions and prompts to launch Claude interactively
    for insight extraction. Use -i to auto-launch Claude without prompting.

    Examples:

        erk learn                  # Infer from branch

        erk learn 123

        erk learn 123 -i           # Auto-launch Claude
    """
    # Resolve issue number: explicit argument or infer from branch
    issue_number: int | None = None
    if issue is not None:
        issue_number = _extract_issue_number(issue)
        if issue_number is None:
            user_output(click.style(f"Error: Invalid issue identifier: {issue}", fg="red"))
            raise SystemExit(1)
    else:
        # Try to infer from current branch
        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is not None:
            issue_number = extract_leading_issue_number(branch)

    if issue_number is None:
        user_output(
            click.style("Error: ", fg="red")
            + "No issue specified and could not infer from branch name"
        )
        user_output("Usage: erk learn <issue-number>")
        user_output("Or run from a branch named P{issue}-...")
        raise SystemExit(1)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Check for preprocessed learn materials gist URL before session discovery
    gist_url = _get_learn_materials_gist_url(ctx, repo_root, issue_number)
    if gist_url is not None:
        user_output(
            click.style(f"Preprocessed learn materials for plan #{issue_number}", bold=True)
            + f"\n\nGist: {click.style(gist_url, fg='cyan')}"
            + "\n\nSessions have been preprocessed and uploaded."
            + "\nClaude will download and analyze from the gist directly."
        )
        _confirm_and_launch(
            ctx=ctx,
            repo_root=repo_root,
            interactive=interactive,
            dangerous=dangerous,
            confirm_prompt=(
                "Use Claude to learn from preprocessed materials and produce documentation?"
            ),
            command=f"/erk:learn {issue_number} gist_url={gist_url}",
        )
        return

    # No gist URL — fall through to session discovery
    # Find sessions for the plan
    sessions_for_plan = find_sessions_for_plan(
        ctx.issues,
        repo_root,
        issue_number,
    )

    # Get readable sessions (ones that exist on disk) using global lookup
    readable_sessions = get_readable_sessions(
        sessions_for_plan,
        ctx.claude_installation,
    )
    readable_session_ids = [sid for sid, _ in readable_sessions]
    session_paths = [str(path) for _, path in readable_sessions]

    # Local session fallback: when GitHub has no tracked sessions, scan local sessions
    local_session_ids: list[str] = []
    if not readable_session_ids:
        local_session_ids = find_local_sessions_for_project(
            ctx.claude_installation,
            ctx.cwd,
            limit=10,
        )
        # Get paths for local sessions
        for sid in local_session_ids:
            path = ctx.claude_installation.get_session_path(ctx.cwd, sid)
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
        local_session_ids=local_session_ids,
        last_remote_impl_at=sessions_for_plan.last_remote_impl_at,
    )

    # Display sessions
    _display_human_readable(result)

    # Only offer interactive mode if there are any sessions (tracked or local)
    has_sessions = bool(readable_session_ids) or bool(local_session_ids)
    if not has_sessions:
        return

    _confirm_and_launch(
        ctx=ctx,
        repo_root=repo_root,
        interactive=interactive,
        dangerous=dangerous,
        confirm_prompt=(
            "Use Claude to learn from these sessions and produce documentation in docs/learned?"
        ),
        command=f"/erk:learn {issue_number}",
    )


def _confirm_and_launch(
    *,
    ctx: ErkContext,
    repo_root: Path,
    interactive: bool,
    dangerous: bool,
    confirm_prompt: str,
    command: str,
) -> None:
    """Confirm with user (or auto-launch with -i), then execute interactively."""
    should_launch = interactive
    if not interactive:
        user_output("")
        should_launch = user_confirm(confirm_prompt, default=True)

    if should_launch:
        ctx.prompt_executor.execute_interactive(
            worktree_path=repo_root,
            dangerous=dangerous,
            command=command,
            target_subpath=None,
            permission_mode="edits",
        )


def _get_learn_materials_gist_url(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
) -> str | None:
    """Check plan header for a stored learn_materials_gist_url.

    Args:
        ctx: ErkContext
        repo_root: Repository root path
        issue_number: Plan issue number

    Returns:
        Gist URL if found on the plan header, None otherwise
    """
    issue = ctx.issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return None

    return extract_plan_header_learn_materials_gist_url(issue.body)


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
    elif result.last_remote_impl_at is not None:
        user_output(
            "Implementation sessions: "
            + click.style("(ran remotely - logs not accessible locally)", dim=True)
        )
    else:
        user_output("Implementation sessions: " + click.style("(none)", dim=True))

    # Previous learn sessions
    if result.learn_session_ids:
        user_output(f"Previous learn sessions ({len(result.learn_session_ids)}):")
        for sid in result.learn_session_ids:
            user_output(f"  - {click.style(sid, fg='yellow')}")

    user_output("")

    # Readable sessions summary (tracked sessions from GitHub metadata)
    total_tracked = len(result.readable_session_ids)
    total_local = len(result.local_session_ids)

    if total_tracked > 0:
        user_output(f"Readable sessions: {click.style(str(total_tracked), fg='green', bold=True)}")
        for path in result.session_paths:
            user_output(f"  {click.style(path, dim=True)}")
    elif total_local > 0:
        # Fallback: show local sessions when no tracked sessions exist
        user_output(
            click.style("No tracked sessions in GitHub metadata.", dim=True)
            + " Found local sessions:"
        )
        user_output(f"Local sessions: {click.style(str(total_local), fg='cyan', bold=True)}")
        for path in result.session_paths:
            user_output(f"  {click.style(path, dim=True)}")
    else:
        user_output(click.style("No readable sessions found on this machine.", fg="red"))
