"""Command registry for command palette.

This module defines all available commands and their availability predicates.
Commands are organized by category: Actions, Opens, Copies.
Plan commands appear only in Plans/Learn views; objective commands appear only in Objectives view.
"""

from erk.tui.commands.types import CommandCategory, CommandContext, CommandDefinition
from erk.tui.views.types import ViewMode

CATEGORY_EMOJI: dict[CommandCategory, str] = {
    CommandCategory.ACTION: "⚡",
    CommandCategory.OPEN: "🔗",
    CommandCategory.COPY: "📋",
}


# === View Mode Predicates ===


def _is_plan_view(ctx: CommandContext) -> bool:
    """True when not in Objectives view (i.e., Plans or Learn)."""
    return ctx.view_mode != ViewMode.OBJECTIVES


def _is_objectives_view(ctx: CommandContext) -> bool:
    """True when in Objectives view."""
    return ctx.view_mode == ViewMode.OBJECTIVES


# === Display Name Generators (Plan Commands) ===


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
    return f"erk launch pr-fix-conflicts --pr {ctx.row.pr_number}"


def _display_address_remote(ctx: CommandContext) -> str:
    """Display name for address_remote command."""
    return f"erk launch pr-address --pr {ctx.row.pr_number}"


def _display_open_issue(ctx: CommandContext) -> str:
    """Display name for open_issue command."""
    if ctx.row.issue_url:
        return ctx.row.issue_url
    return "Issue"


def _display_open_pr(ctx: CommandContext) -> str:
    """Display name for open_pr command."""
    if ctx.row.pr_url:
        return ctx.row.pr_url
    return "PR"


def _display_open_run(ctx: CommandContext) -> str:
    """Display name for open_run command."""
    if ctx.row.run_url:
        return ctx.row.run_url
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


def _display_copy_prepare_activate(ctx: CommandContext) -> str:
    """Display name for copy_prepare_activate command."""
    return f'source "$(erk prepare {ctx.row.issue_number} --script)" && erk implement --dangerous'


def _display_copy_submit(ctx: CommandContext) -> str:
    """Display name for copy_submit command."""
    return f"erk plan submit {ctx.row.issue_number}"


def _display_copy_replan(ctx: CommandContext) -> str:
    """Display name for copy_replan command."""
    return f"erk plan replan {ctx.row.issue_number}"


# === Display Name Generators (Objective Commands) ===


def _display_one_shot_plan(ctx: CommandContext) -> str:
    """Display name for one_shot_plan command."""
    return f"erk objective plan {ctx.row.issue_number} --one-shot"


def _display_check_objective(ctx: CommandContext) -> str:
    """Display name for check_objective command."""
    return f"erk objective check {ctx.row.issue_number}"


def _display_close_objective(ctx: CommandContext) -> str:
    """Display name for close_objective command."""
    return f"erk objective close {ctx.row.issue_number} --force"


def _display_open_objective(ctx: CommandContext) -> str:
    """Display name for open_objective command."""
    if ctx.row.issue_url:
        return ctx.row.issue_url
    return "Objective"


def _display_copy_plan(ctx: CommandContext) -> str:
    """Display name for copy_plan command."""
    return f"erk objective plan {ctx.row.issue_number}"


def _display_copy_view(ctx: CommandContext) -> str:
    """Display name for copy_view command."""
    return f"erk objective view {ctx.row.issue_number}"


def get_all_commands() -> list[CommandDefinition]:
    """Return all command definitions.

    Commands are ordered by category:
    1. Actions (mutative operations)
    2. Opens (browser navigation)
    3. Copies (clipboard operations)

    Plan commands are filtered out in Objectives view; objective commands
    are filtered out in Plans/Learn views.

    Returns:
        List of all available command definitions
    """
    return [
        # === PLAN ACTIONS ===
        CommandDefinition(
            id="close_plan",
            name="Close Plan",
            description="close",
            category=CommandCategory.ACTION,
            shortcut=None,
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_close_plan,
        ),
        CommandDefinition(
            id="submit_to_queue",
            name="Submit to Queue",
            description="submit",
            category=CommandCategory.ACTION,
            shortcut="s",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.issue_url is not None,
            get_display_name=_display_submit_to_queue,
        ),
        CommandDefinition(
            id="land_pr",
            name="Land PR",
            description="land",
            category=CommandCategory.ACTION,
            shortcut=None,
            is_available=lambda ctx: (
                _is_plan_view(ctx)
                and ctx.row.pr_number is not None
                and ctx.row.pr_state == "OPEN"
                and ctx.row.run_url is not None
            ),
            get_display_name=_display_land_pr,
        ),
        CommandDefinition(
            id="fix_conflicts_remote",
            name="Fix Conflicts Remote",
            description="fix-conflicts",
            category=CommandCategory.ACTION,
            shortcut="5",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_fix_conflicts_remote,
        ),
        CommandDefinition(
            id="address_remote",
            name="Address Remote",
            description="address",
            category=CommandCategory.ACTION,
            shortcut=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_address_remote,
        ),
        # === OBJECTIVE ACTIONS ===
        CommandDefinition(
            id="one_shot_plan",
            name="Plan (One-Shot)",
            description="plan (one-shot)",
            category=CommandCategory.ACTION,
            shortcut="s",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_one_shot_plan,
        ),
        CommandDefinition(
            id="check_objective",
            name="Check Objective",
            description="check",
            category=CommandCategory.ACTION,
            shortcut="5",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_check_objective,
        ),
        CommandDefinition(
            id="close_objective",
            name="Close Objective",
            description="close",
            category=CommandCategory.ACTION,
            shortcut=None,
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_close_objective,
        ),
        # === PLAN OPENS ===
        CommandDefinition(
            id="open_issue",
            name="Issue",
            description="plan",
            category=CommandCategory.OPEN,
            shortcut="i",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.issue_url is not None,
            get_display_name=_display_open_issue,
        ),
        CommandDefinition(
            id="open_pr",
            name="PR",
            description="pr",
            category=CommandCategory.OPEN,
            shortcut="p",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_url is not None,
            get_display_name=_display_open_pr,
        ),
        CommandDefinition(
            id="open_run",
            name="Workflow Run",
            description="run",
            category=CommandCategory.OPEN,
            shortcut="r",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.run_url is not None,
            get_display_name=_display_open_run,
        ),
        # === OBJECTIVE OPENS ===
        CommandDefinition(
            id="open_objective",
            name="Objective",
            description="objective",
            category=CommandCategory.OPEN,
            shortcut="i",
            is_available=lambda ctx: _is_objectives_view(ctx) and ctx.row.issue_url is not None,
            get_display_name=_display_open_objective,
        ),
        # === PLAN COPIES ===
        CommandDefinition(
            id="copy_checkout",
            name="erk br co <branch>",
            description="checkout",
            category=CommandCategory.COPY,
            shortcut="c",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.worktree_branch is not None,
            get_display_name=_display_copy_checkout,
        ),
        CommandDefinition(
            id="copy_pr_checkout",
            name="checkout && sync",
            description="sync",
            category=CommandCategory.COPY,
            shortcut="e",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_pr_checkout,
        ),
        CommandDefinition(
            id="copy_prepare",
            name="erk prepare",
            description="prepare",
            category=CommandCategory.COPY,
            shortcut="1",
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_copy_prepare,
        ),
        CommandDefinition(
            id="copy_prepare_activate",
            name="prepare && implement",
            description="implement",
            category=CommandCategory.COPY,
            shortcut="4",
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_copy_prepare_activate,
        ),
        CommandDefinition(
            id="copy_submit",
            name="erk plan submit",
            description="submit",
            category=CommandCategory.COPY,
            shortcut="3",
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_copy_submit,
        ),
        CommandDefinition(
            id="copy_replan",
            name="erk plan replan",
            description="replan",
            category=CommandCategory.COPY,
            shortcut="6",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.issue_url is not None,
            get_display_name=_display_copy_replan,
        ),
        # === OBJECTIVE COPIES ===
        CommandDefinition(
            id="copy_plan",
            name="erk objective plan",
            description="plan",
            category=CommandCategory.COPY,
            shortcut="1",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_copy_plan,
        ),
        CommandDefinition(
            id="copy_view",
            name="erk objective view",
            description="view",
            category=CommandCategory.COPY,
            shortcut="3",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_copy_view,
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
