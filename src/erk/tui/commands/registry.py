"""Command registry for command palette.

This module defines all available commands and their availability predicates.
Commands are organized by category: Actions, Opens, Copies.
"""

from erk.tui.commands.types import CommandContext, CommandDefinition


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
            name="Action: Close Plan",
            description="Close issue and linked PRs",
            shortcut=None,
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="submit_to_queue",
            name="Action: Submit to Queue",
            description="Submit plan for remote AI implementation",
            shortcut="s",
            is_available=lambda ctx: ctx.row.issue_url is not None,
        ),
        # === OPENS ===
        CommandDefinition(
            id="open_browser",
            name="Open: In Browser",
            description="Open PR (or issue if no PR)",
            shortcut="o",
            is_available=lambda ctx: bool(ctx.row.pr_url or ctx.row.issue_url),
        ),
        CommandDefinition(
            id="open_issue",
            name="Open: Issue",
            description="Open issue in browser",
            shortcut="i",
            is_available=lambda ctx: ctx.row.issue_url is not None,
        ),
        CommandDefinition(
            id="open_pr",
            name="Open: PR",
            description="Open PR in browser",
            shortcut="p",
            is_available=lambda ctx: ctx.row.pr_url is not None,
        ),
        CommandDefinition(
            id="open_run",
            name="Open: Workflow Run",
            description="Open GitHub Actions run",
            shortcut="r",
            is_available=lambda ctx: ctx.row.run_url is not None,
        ),
        # === COPIES ===
        CommandDefinition(
            id="copy_checkout",
            name="Copy: erk co <worktree>",
            description="Copy checkout command",
            shortcut="c",
            is_available=lambda ctx: ctx.row.exists_locally,
        ),
        CommandDefinition(
            id="copy_pr_checkout",
            name="Copy: erk pr co <number>",
            description="Copy PR checkout command",
            shortcut="e",
            is_available=lambda ctx: ctx.row.pr_number is not None,
        ),
        CommandDefinition(
            id="copy_implement",
            name="Copy: erk implement",
            description="Copy implement command",
            shortcut="1",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_implement_dangerous",
            name="Copy: erk implement --dangerous",
            description="Copy dangerous implement command",
            shortcut="2",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_implement_yolo",
            name="Copy: erk implement --yolo",
            description="Copy yolo implement command",
            shortcut="3",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_submit",
            name="Copy: erk submit",
            description="Copy submit command",
            shortcut="4",
            is_available=lambda _: True,
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
