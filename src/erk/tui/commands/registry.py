"""Command registry for command palette.

This module defines all available commands and their availability predicates.
Commands are organized by category: Actions, Opens, Copies.
"""

from erk.tui.commands.types import CommandCategory, CommandContext, CommandDefinition

CATEGORY_EMOJI: dict[CommandCategory, str] = {
    CommandCategory.ACTION: "⚡",
    CommandCategory.OPEN: "🔗",
    CommandCategory.COPY: "📋",
}


# === Display Name Generators ===
# These functions generate context-aware display names for the command palette.


def _display_close_plan(ctx: CommandContext) -> str:
    """Display name for close_plan command."""
    return f"erk plan close {ctx.row.issue_number}"


def _display_submit_to_queue(ctx: CommandContext) -> str:
    """Display name for submit_to_queue command."""
    return f"erk plan submit {ctx.row.issue_number}"


def _display_land_pr(ctx: CommandContext) -> str:
    """Display name for land_pr command."""
    return f"erk land {ctx.row.pr_number}"


def _display_fix_conflicts_remote(ctx: CommandContext) -> str:
    """Display name for fix_conflicts_remote command."""
    return f"erk pr fix-conflicts-remote {ctx.row.pr_number}"


def _display_open_issue(ctx: CommandContext) -> str:
    """Display name for open_issue command."""
    if ctx.row.issue_url:
        return f"plan: {ctx.row.issue_url}"
    return "Issue"


def _display_open_pr(ctx: CommandContext) -> str:
    """Display name for open_pr command."""
    if ctx.row.pr_url:
        return f"pr: {ctx.row.pr_url}"
    return "PR"


def _display_open_run(ctx: CommandContext) -> str:
    """Display name for open_run command."""
    if ctx.row.run_url:
        return f"run: {ctx.row.run_url}"
    return "Workflow Run"


def _display_copy_checkout(ctx: CommandContext) -> str:
    """Display name for copy_checkout command."""
    if ctx.row.worktree_branch:
        return f"erk br co {ctx.row.worktree_branch}"
    if ctx.row.pr_number:
        return f"erk pr co {ctx.row.pr_number}"
    return "erk br co <branch>"


def _display_copy_pr_checkout(ctx: CommandContext) -> str:
    """Display name for copy_pr_checkout command."""
    if ctx.row.pr_number:
        pr = ctx.row.pr_number
        return f'source "$(erk pr checkout {pr} --script)" && erk pr sync --dangerous'
    return "checkout && sync"


def _display_copy_prepare(ctx: CommandContext) -> str:
    """Display name for copy_prepare command."""
    return f"erk prepare {ctx.row.issue_number}"


def _display_copy_prepare_dangerous(ctx: CommandContext) -> str:
    """Display name for copy_prepare_dangerous command."""
    return f"erk prepare {ctx.row.issue_number} --dangerous"


def _display_copy_prepare_activate(ctx: CommandContext) -> str:
    """Display name for copy_prepare_activate command."""
    return f'source "$(erk prepare {ctx.row.issue_number} --script)" && erk implement --dangerous'


def _display_copy_submit(ctx: CommandContext) -> str:
    """Display name for copy_submit command."""
    return f"erk plan submit {ctx.row.issue_number}"


def _display_copy_replan(ctx: CommandContext) -> str:
    """Display name for copy_replan command."""
    return f"erk plan replan {ctx.row.issue_number}"


def get_all_commands() -> list[CommandDefinition]:
    """Return all command definitions.

    Commands are ordered by category:
    1. Actions (mutative operations)
    2. Opens (browser navigation)
    3. Copies (clipboard operations)

    Returns:
        List of all available command definitions
    """
    return [
        # === ACTIONS ===
        CommandDefinition(
            id="close_plan",
            name="Close Plan",
            description="Close issue and linked PRs",
            category=CommandCategory.ACTION,
            shortcut=None,
            is_available=lambda _: True,
            get_display_name=_display_close_plan,
        ),
        CommandDefinition(
            id="submit_to_queue",
            name="Submit to Queue",
            description="Submit for remote AI implementation",
            category=CommandCategory.ACTION,
            shortcut="s",
            is_available=lambda ctx: ctx.row.issue_url is not None,
            get_display_name=_display_submit_to_queue,
        ),
        CommandDefinition(
            id="land_pr",
            name="Land PR",
            description="Merge and delete remote branch",
            category=CommandCategory.ACTION,
            shortcut=None,
            is_available=lambda ctx: (
                ctx.row.pr_number is not None
                and ctx.row.pr_state == "OPEN"
                and ctx.row.run_url is not None
            ),
            get_display_name=_display_land_pr,
        ),
        CommandDefinition(
            id="fix_conflicts_remote",
            name="Fix Conflicts Remote",
            description="Launch remote conflict resolution",
            category=CommandCategory.ACTION,
            shortcut="5",
            is_available=lambda ctx: ctx.row.pr_number is not None,
            get_display_name=_display_fix_conflicts_remote,
        ),
        # === OPENS ===
        CommandDefinition(
            id="open_issue",
            name="Issue",
            description="Plan issue",
            category=CommandCategory.OPEN,
            shortcut="i",
            is_available=lambda ctx: ctx.row.issue_url is not None,
            get_display_name=_display_open_issue,
        ),
        CommandDefinition(
            id="open_pr",
            name="PR",
            description="Pull request",
            category=CommandCategory.OPEN,
            shortcut="p",
            is_available=lambda ctx: ctx.row.pr_url is not None,
            get_display_name=_display_open_pr,
        ),
        CommandDefinition(
            id="open_run",
            name="Workflow Run",
            description="GitHub Actions",
            category=CommandCategory.OPEN,
            shortcut="r",
            is_available=lambda ctx: ctx.row.run_url is not None,
            get_display_name=_display_open_run,
        ),
        # === COPIES ===
        CommandDefinition(
            id="copy_checkout",
            name="erk br co <branch>",
            description="Checkout branch",
            category=CommandCategory.COPY,
            shortcut="c",
            is_available=lambda ctx: ctx.row.worktree_branch is not None,
            get_display_name=_display_copy_checkout,
        ),
        CommandDefinition(
            id="copy_pr_checkout",
            name="checkout && sync",
            description="Activate worktree",
            category=CommandCategory.COPY,
            shortcut="e",
            is_available=lambda ctx: ctx.row.pr_number is not None,
            get_display_name=_display_copy_pr_checkout,
        ),
        CommandDefinition(
            id="copy_prepare",
            name="erk prepare",
            description="Setup worktree from plan",
            category=CommandCategory.COPY,
            shortcut="1",
            is_available=lambda _: True,
            get_display_name=_display_copy_prepare,
        ),
        CommandDefinition(
            id="copy_prepare_dangerous",
            name="erk prepare --dangerous",
            description="Force overwrite existing",
            category=CommandCategory.COPY,
            shortcut="2",
            is_available=lambda _: True,
            get_display_name=_display_copy_prepare_dangerous,
        ),
        CommandDefinition(
            id="copy_prepare_activate",
            name="prepare && implement",
            description="One-liner: setup + start",
            category=CommandCategory.COPY,
            shortcut="4",
            is_available=lambda _: True,
            get_display_name=_display_copy_prepare_activate,
        ),
        CommandDefinition(
            id="copy_submit",
            name="erk plan submit",
            description="Submit to remote queue",
            category=CommandCategory.COPY,
            shortcut="3",
            is_available=lambda _: True,
            get_display_name=_display_copy_submit,
        ),
        CommandDefinition(
            id="copy_replan",
            name="erk plan replan",
            description="Re-evaluate against codebase",
            category=CommandCategory.COPY,
            shortcut="6",
            is_available=lambda ctx: ctx.row.issue_url is not None,
            get_display_name=_display_copy_replan,
        ),
    ]


def get_available_commands(ctx: CommandContext) -> list[CommandDefinition]:
    """Return commands available in current context.

    Args:
        ctx: Command context containing the plan row data

    Returns:
        List of commands that are available for the given context
    """
    return [cmd for cmd in get_all_commands() if cmd.is_available(ctx)]


def get_display_name(cmd: CommandDefinition, ctx: CommandContext) -> str:
    """Get the display name for a command in the given context.

    Args:
        cmd: The command definition
        ctx: The command context

    Returns:
        The dynamic display name if get_display_name is set, otherwise the static name
    """
    if cmd.get_display_name is not None:
        return cmd.get_display_name(ctx)
    return cmd.name
