"""Prepare command - shorthand for creating a branch from a plan issue."""

import click

from erk.cli.commands.branch.create_cmd import branch_create


@click.command("prepare")
@click.argument("plan", metavar="PLAN")
@click.option("--no-slot", is_flag=True, help="Create branch without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@click.option(
    "--create-only",
    is_flag=True,
    help="Only create worktree, don't include implementation command",
)
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Include --dangerous flag to skip permission prompts during implementation",
)
@click.option(
    "--docker",
    is_flag=True,
    help="Include --docker flag for filesystem-isolated implementation",
)
@click.pass_context
def prepare(
    ctx: click.Context,
    plan: str,
    no_slot: bool,
    force: bool,
    create_only: bool,
    dangerous: bool,
    docker: bool,
) -> None:
    """Prepare a plan for execution by creating a worktree.

    PLAN is a GitHub issue number or URL with the erk-plan label.

    This is a shorthand for: erk br create --for-plan PLAN
    """
    ctx.invoke(
        branch_create,
        branch_name=None,
        for_plan=plan,
        no_slot=no_slot,
        force=force,
        create_only=create_only,
        dangerous=dangerous,
        docker=docker,
    )
