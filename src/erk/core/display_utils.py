"""Display formatting utilities for erk.

This module contains pure business logic for formatting and displaying worktree
information in the CLI. All functions are pure (no I/O) and can be tested without
filesystem access.
"""

import re
from datetime import datetime

import click

from erk_shared.github.types import PullRequestInfo, WorkflowRun


def get_visible_length(text: str) -> int:
    """Calculate the visible length of text, excluding ANSI and OSC escape sequences.

    Args:
        text: Text that may contain escape sequences

    Returns:
        Number of visible characters
    """
    # Remove ANSI color codes (\033[...m)
    text = re.sub(r"\033\[[0-9;]*m", "", text)
    # Remove OSC 8 hyperlink sequences (\033]8;;URL\033\\)
    text = re.sub(r"\033\]8;;[^\033]*\033\\", "", text)
    return len(text)


def get_pr_status_emoji(pr: PullRequestInfo) -> str:
    """Determine the emoji to display for a PR based on its status.

    Args:
        pr: Pull request information

    Returns:
        Emoji character representing the PR's current state,
        with 💥 appended if there are merge conflicts
    """
    # Determine base emoji based on PR state
    if pr.is_draft:
        emoji = "🚧"
    elif pr.state == "MERGED":
        emoji = "🎉"
    elif pr.state == "CLOSED":
        emoji = "⛔"
    elif pr.checks_passing is True:
        emoji = "✅"
    elif pr.checks_passing is False:
        emoji = "❌"
    else:
        # Open PR with no checks
        emoji = "👀"

    # Append conflict indicator if PR has merge conflicts
    # Only for open PRs (published or draft)
    if pr.has_conflicts and pr.state == "OPEN":
        emoji += "💥"

    return emoji


def format_pr_info(
    pr: PullRequestInfo | None,
    graphite_url: str | None,
    *,
    use_graphite: bool = True,
) -> str:
    """Format PR status indicator with emoji and clickable link.

    Args:
        pr: Pull request information (None if no PR exists)
        graphite_url: Graphite URL for the PR (None if unavailable)
        use_graphite: If True, use Graphite URL; if False, use GitHub URL from pr.url

    Returns:
        Formatted PR info string (e.g., "✅ #23") or empty string if no PR
    """
    if pr is None:
        return ""

    emoji = get_pr_status_emoji(pr)

    # Format PR number text
    pr_text = f"#{pr.number}"

    # Determine which URL to use based on use_graphite setting
    url = graphite_url if use_graphite else pr.url

    # If we have a URL, make it clickable using OSC 8 terminal escape sequence
    if url:
        # Wrap the link text in cyan color to distinguish from non-clickable bright_blue indicators
        colored_pr_text = click.style(pr_text, fg="cyan")
        clickable_link = f"\033]8;;{url}\033\\{colored_pr_text}\033]8;;\033\\"
        return f"{emoji} {clickable_link}"
    else:
        # No URL available - just show colored text without link
        colored_pr_text = click.style(pr_text, fg="cyan")
        return f"{emoji} {colored_pr_text}"


def get_workflow_status_emoji(workflow_run: WorkflowRun) -> str:
    """Determine the emoji to display for a workflow run based on its status.

    Args:
        workflow_run: Workflow run information

    Returns:
        Emoji character representing the workflow's current state
    """
    if workflow_run.status == "completed":
        if workflow_run.conclusion == "success":
            return "✅"
        if workflow_run.conclusion == "failure":
            return "❌"
        if workflow_run.conclusion == "cancelled":
            return "⛔"
        # Other conclusions (skipped, timed_out, etc.)
        return "❓"
    if workflow_run.status == "in_progress":
        return "⟳"
    if workflow_run.status == "queued":
        return "⧗"
    # Unknown status
    return "❓"


def format_workflow_status(workflow_run: WorkflowRun | None, workflow_url: str | None) -> str:
    """Format workflow run status indicator with emoji and link.

    Args:
        workflow_run: Workflow run information (None if no workflow run)
        workflow_url: GitHub Actions workflow run URL (None if unavailable)

    Returns:
        Formatted workflow status string (e.g., "✅ CI") or empty string if no workflow
    """
    if workflow_run is None:
        return ""

    emoji = get_workflow_status_emoji(workflow_run)

    # Format status text
    status_text = "CI"

    # If we have a URL, make it clickable using OSC 8 terminal escape sequence
    if workflow_url:
        # Wrap the link text in cyan color
        colored_status_text = click.style(status_text, fg="cyan")
        clickable_link = f"\033]8;;{workflow_url}\033\\{colored_status_text}\033]8;;\033\\"
        return f"{emoji} {clickable_link}"
    else:
        # No URL available - just show colored text without link
        colored_status_text = click.style(status_text, fg="cyan")
        return f"{emoji} {colored_status_text}"


def format_workflow_run_id(workflow_run: WorkflowRun | None, workflow_url: str | None) -> str:
    """Format workflow run ID with linkification using Rich markup.

    Args:
        workflow_run: Workflow run information (None if no workflow run)
        workflow_url: GitHub Actions workflow run URL (None if unavailable)

    Returns:
        Formatted workflow run ID string with Rich markup, or empty string if no workflow
    """
    if workflow_run is None:
        return ""

    run_id_text = workflow_run.run_id

    # Use Rich markup for proper rendering in Rich tables
    # Note: [cyan] must wrap [link], not vice versa, for Rich to render both correctly
    if workflow_url:
        return f"[cyan][link={workflow_url}]{run_id_text}[/link][/cyan]"
    else:
        return f"[cyan]{run_id_text}[/cyan]"


def get_workflow_run_state(workflow_run: WorkflowRun) -> str:
    """Get normalized state string for a workflow run.

    Combines status and conclusion into a single state string suitable for
    filtering and display.

    Args:
        workflow_run: Workflow run information

    Returns:
        One of: "queued", "in_progress", "success", "failure", "cancelled"
    """
    if workflow_run.status == "completed":
        if workflow_run.conclusion == "success":
            return "success"
        if workflow_run.conclusion == "failure":
            return "failure"
        if workflow_run.conclusion == "cancelled":
            return "cancelled"
        # Other conclusions (skipped, timed_out, etc.) map to failure
        return "failure"
    if workflow_run.status == "in_progress":
        return "in_progress"
    # status == "queued" or unknown
    return "queued"


def format_workflow_outcome(workflow_run: WorkflowRun | None) -> str:
    """Format workflow run outcome as emoji + text with Rich markup.

    Args:
        workflow_run: Workflow run information (None if no workflow run)

    Returns:
        Formatted outcome string with Rich markup (e.g., "[green]✅ Success[/green]")
        or "[dim]-[/dim]" if no workflow run
    """
    if workflow_run is None:
        return "[dim]-[/dim]"

    state = get_workflow_run_state(workflow_run)

    if state == "queued":
        return "[yellow]⧗ Queued[/yellow]"
    if state == "in_progress":
        return "[blue]⟳ Running[/blue]"
    if state == "success":
        return "[green]✅ Success[/green]"
    if state == "failure":
        return "[red]❌ Failure[/red]"
    if state == "cancelled":
        return "[dim]⛔ Cancelled[/dim]"

    # Fallback (shouldn't happen)
    return "[dim]-[/dim]"


def format_branch_without_worktree(
    branch_name: str,
    pr_info: str | None,
    max_branch_len: int = 0,
    max_pr_info_len: int = 0,
) -> str:
    """Format a branch without a worktree for display.

    Returns a line like: "branch-name PR #123 ✅"

    Args:
        branch_name: Name of the branch
        pr_info: Formatted PR info string (e.g., "✅ #23") or None
        max_branch_len: Maximum branch name length for alignment (0 disables)
        max_pr_info_len: Maximum PR info length for alignment (0 disables)

    Returns:
        Formatted string with branch name and PR info
    """
    # Format branch name in yellow (same as worktree branches)
    branch_styled = click.style(branch_name, fg="yellow")

    # Add padding to branch name if alignment is enabled
    if max_branch_len > 0:
        branch_padding = max_branch_len - len(branch_name)
        branch_styled += " " * branch_padding

    line = branch_styled

    # Add PR info if available
    if pr_info:
        # Calculate visible length for alignment
        pr_info_visible_len = get_visible_length(pr_info)

        # Add padding to PR info if alignment is enabled
        if max_pr_info_len > 0:
            pr_info_padding = max_pr_info_len - pr_info_visible_len
            pr_info_padded = pr_info + (" " * pr_info_padding)
        else:
            pr_info_padded = pr_info

        line += f" {pr_info_padded}"

    return line


def format_worktree_line(
    *,
    name: str,
    branch: str | None,
    pr_info: str | None,
    plan_summary: str | None,
    is_root: bool,
    is_current: bool,
    max_name_len: int = 0,
    max_branch_len: int = 0,
    max_pr_info_len: int = 0,
    pr_title: str | None = None,
    workflow_run: WorkflowRun | None = None,
    workflow_url: str | None = None,
    max_workflow_len: int = 0,
) -> str:
    """Format a single worktree line with colorization and optional alignment.

    Args:
        name: Worktree name to display
        branch: Branch name (if any)
        pr_info: Formatted PR info string (e.g., "✅ #23") or None
        plan_summary: Plan title or None if no plan
        is_root: True if this is the root repository worktree
        is_current: True if this is the worktree the user is currently in
        max_name_len: Maximum name length for alignment (0 = no alignment)
        max_branch_len: Maximum branch length for alignment (0 = no alignment)
        max_pr_info_len: Maximum PR info visible length for alignment (0 = no alignment)
        pr_title: PR title from GitHub (preferred over plan_summary if available)
        workflow_run: Workflow run information (None if no workflow)
        workflow_url: GitHub Actions workflow run URL (None if unavailable)
        max_workflow_len: Maximum workflow status visible length for alignment (0 = no alignment)

    Returns:
        Formatted line: name (branch) {PR info} {workflow status} {PR title or plan summary}
    """
    # Root worktree gets green to distinguish it from regular worktrees
    name_color = "green" if is_root else "cyan"

    # Calculate padding for name field
    name_padding = max_name_len - len(name) if max_name_len > 0 else 0
    name_with_padding = name + (" " * name_padding)
    name_part = click.style(name_with_padding, fg=name_color, bold=True)

    # Build parts for display: name (branch) {PR info} {plan summary}
    parts = [name_part]

    # Add branch in parentheses (yellow)
    # If name matches branch, show "=" instead of repeating the branch name
    if branch:
        branch_display = "=" if name == branch else branch
        # Calculate padding for branch field (including parentheses)
        branch_with_parens = f"({branch_display})"
        branch_padding = max_branch_len - len(branch_with_parens) if max_branch_len > 0 else 0
        branch_with_padding = branch_with_parens + (" " * branch_padding)
        branch_part = click.style(branch_with_padding, fg="yellow")
        parts.append(branch_part)
    elif max_branch_len > 0:
        # Add spacing even if no branch to maintain alignment
        parts.append(" " * max_branch_len)

    # Add PR info or placeholder with alignment
    pr_info_placeholder = click.style("[no PR]", fg="white", dim=True)
    pr_display = pr_info if pr_info else pr_info_placeholder

    if max_pr_info_len > 0:
        # Calculate visible length and add padding
        visible_len = get_visible_length(pr_display)
        padding = max_pr_info_len - visible_len
        pr_display_with_padding = pr_display + (" " * padding)
        parts.append(pr_display_with_padding)
    else:
        parts.append(pr_display)

    # Add workflow status with alignment
    workflow_status = format_workflow_status(workflow_run, workflow_url)
    if workflow_status:
        if max_workflow_len > 0:
            # Calculate visible length and add padding
            visible_len = get_visible_length(workflow_status)
            padding = max_workflow_len - visible_len
            workflow_with_padding = workflow_status + (" " * padding)
            parts.append(workflow_with_padding)
        else:
            parts.append(workflow_status)
    elif max_workflow_len > 0:
        # Add spacing to maintain alignment when no workflow
        parts.append(" " * max_workflow_len)

    # Add PR title, plan summary, or placeholder (PR title takes precedence)
    if pr_title:
        # PR title available - use it without emoji
        title_colored = click.style(pr_title, fg="cyan")
        parts.append(title_colored)
    elif plan_summary:
        # No PR title but have plan summary - use with emoji
        plan_colored = click.style(f"📋 {plan_summary}", fg="bright_magenta")
        parts.append(plan_colored)
    else:
        # No PR title and no plan summary
        parts.append(click.style("[no plan]", fg="white", dim=True))

    # Build the main line
    line = " ".join(parts)

    # Add indicator on the right for current worktree
    if is_current:
        indicator = click.style(" ← (cwd)", fg="bright_blue")
        line += indicator

    return line


def format_plan_display(
    *, plan_identifier: str, state: str, title: str, labels: list[str], url: str | None = None
) -> str:
    """Format a plan for display in lists.

    Args:
        plan_identifier: Plan identifier (e.g., "42", "PROJ-123")
        state: Plan state ("OPEN" or "CLOSED")
        title: Plan title
        labels: List of label names
        url: Optional URL for clickable link

    Returns:
        Formatted string: "#42 (OPEN) [erk-plan] Title"
    """
    # Format state with color
    state_color = "green" if state == "OPEN" else "red"
    state_str = click.style(state, fg=state_color)

    # Format identifier
    id_text = f"#{plan_identifier}"

    # If we have a URL, make it clickable using OSC 8
    if url:
        colored_id = click.style(id_text, fg="cyan")
        clickable_id = f"\033]8;;{url}\033\\{colored_id}\033]8;;\033\\"
    else:
        clickable_id = click.style(id_text, fg="cyan")

    # Format labels
    labels_str = ""
    if labels:
        labels_str = " " + " ".join(
            click.style(f"[{label}]", fg="bright_magenta") for label in labels
        )

    return f"{clickable_id} ({state_str}){labels_str} {title}"


def format_submission_time(created_at: datetime | None) -> str:
    """Format workflow run submission time as MM-DD HH:MM in local timezone.

    Args:
        created_at: UTC datetime when run was created, or None

    Returns:
        Formatted string like "11-26 14:30" in local timezone, or "[dim]-[/dim]" if None
    """
    if created_at is None:
        return "[dim]-[/dim]"

    # Convert UTC to local timezone
    local_time = created_at.astimezone()

    # Format as MM-DD HH:MM
    return local_time.strftime("%m-%d %H:%M")


def format_relative_time(iso_timestamp: str | None, now: datetime | None = None) -> str:
    """Format ISO timestamp as human-readable relative time.

    Args:
        iso_timestamp: ISO 8601 timestamp string, or None
        now: Optional current time for testing (defaults to datetime.now(UTC))

    Returns:
        Relative time string like "just now", "5m ago", "2h ago", "3d ago"
        Returns empty string if iso_timestamp is None or invalid
    """
    from datetime import UTC

    if iso_timestamp is None:
        return ""

    # Parse ISO timestamp
    try:
        # Handle ISO format with timezone (e.g., "2025-01-15T10:30:00+00:00")
        dt = datetime.fromisoformat(iso_timestamp)
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
    except ValueError:
        return ""

    # Get current time
    current_time = now if now is not None else datetime.now(UTC)

    # Calculate difference
    delta = current_time - dt

    # Format based on magnitude
    total_seconds = int(delta.total_seconds())

    # Handle future timestamps or very recent (within 30 seconds)
    if total_seconds < 30:
        return "just now"

    # Minutes
    if total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}m ago"

    # Hours
    if total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours}h ago"

    # Days
    if total_seconds < 604800:  # 7 days
        days = total_seconds // 86400
        return f"{days}d ago"

    # Weeks
    if total_seconds < 2592000:  # 30 days
        weeks = total_seconds // 604800
        return f"{weeks}w ago"

    # Months (approximate)
    months = total_seconds // 2592000
    if months < 12:
        return f"{months}mo ago"

    # Years
    years = total_seconds // 31536000
    return f"{years}y ago"
