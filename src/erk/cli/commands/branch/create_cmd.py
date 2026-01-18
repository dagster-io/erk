"""Branch create command - create a new branch with optional slot assignment."""

import click

from erk.cli.activation import print_activation_instructions, write_worktree_activate_script
from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.output.output import user_output


@click.command("create")
@click.argument("branch_name", metavar="BRANCH", required=False)
@click.option(
    "--for-plan",
    "for_plan",
    type=str,
    default=None,
    help="GitHub issue number or URL with erk-plan label",
)
@click.option("--no-slot", is_flag=True, help="Create branch without slot assignment")
@click.option("-f", "--force", is_flag=True, help="Auto-unassign oldest branch if pool is full")
@click.pass_obj
def branch_create(
    ctx: ErkContext,
    branch_name: str | None,
    for_plan: str | None,
    no_slot: bool,
    force: bool,
) -> None:
    """Create a NEW branch and optionally assign it to a pool slot.

    BRANCH is the name of the new git branch to create.

    By default, the command will:
    1. Verify the branch does NOT already exist (fails if it does)
    2. Create the branch from trunk
    3. Find the next available slot in the pool
    4. Create a worktree for that slot
    5. Assign the branch to the slot

    Use --no-slot to create a branch without assigning it to a slot.
    Use --for-plan to create a branch from a GitHub issue with erk-plan label.
    Use `erk br assign` to assign an EXISTING branch to a slot.
    """
    # Mutual exclusivity validation
    if for_plan is not None and branch_name is not None:
        user_output(
            "Error: Cannot specify both BRANCH and --for-plan.\n"
            "Use --for-plan to derive branch name from issue, or provide BRANCH directly."
        )
        raise SystemExit(1) from None

    if for_plan is None and branch_name is None:
        user_output("Error: Must provide BRANCH argument or --for-plan option.")
        raise SystemExit(1) from None

    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Plan setup - fetches plan and derives branch name if --for-plan is used
    setup: IssueBranchSetup | None = None

    if for_plan is not None:
        issue_number = parse_issue_identifier(for_plan)
        try:
            plan = ctx.plan_store.get_plan(repo.root, str(issue_number))
        except RuntimeError as e:
            raise click.ClickException(str(e)) from e

        result = prepare_plan_for_worktree(plan, ctx.time.now())
        if isinstance(result, IssueValidationFailed):
            user_output(f"Error: {result.message}")
            raise SystemExit(1) from None

        setup = result
        branch_name = setup.branch_name

        for warning in setup.warnings:
            user_output(click.style("Warning: ", fg="yellow") + warning)

    # At this point, branch_name is guaranteed to be set (either from argument or from plan)
    # Type assertion for the type checker
    assert branch_name is not None

    # Check if branch already exists
    local_branches = ctx.git.list_local_branches(repo.root)
    if branch_name in local_branches:
        user_output(
            f"Error: Branch '{branch_name}' already exists.\n"
            "Use `erk br assign` to assign an existing branch to a slot."
        )
        raise SystemExit(1) from None

    # Create the new branch, respecting Graphite stacking
    trunk = ctx.git.detect_trunk_branch(repo.root)
    if trunk is None:
        user_output("Error: Could not detect trunk branch.")
        raise SystemExit(1) from None

    # Stack on current branch if we're on a non-trunk branch
    current_branch = ctx.git.get_current_branch(repo.root)
    if current_branch and current_branch != trunk:
        parent_branch = current_branch
    else:
        parent_branch = trunk

    ctx.git.create_branch(repo.root, branch_name, parent_branch)
    ctx.branch_manager.track_branch(repo.root, branch_name, parent_branch)
    user_output(f"Created branch: {branch_name}")

    # If --no-slot is specified, we're done (but warn about .impl if --for-plan was used)
    if no_slot:
        if setup is not None:
            user_output(
                click.style("Note: ", fg="yellow")
                + ".impl folder not created (no worktree allocated)"
            )
        return

    # Allocate a slot for the branch (branch already exists, so this just assigns)
    slot_result = allocate_slot_for_branch(
        ctx,
        repo,
        branch_name,
        force=force,
        reuse_inactive_slots=True,
        cleanup_artifacts=True,
    )
    user_output(click.style(f"✓ Assigned {branch_name} to {slot_result.slot_name}", fg="green"))

    # Create .impl/ folder if --for-plan was used
    if setup is not None:
        impl_path = create_impl_folder(
            slot_result.worktree_path,
            setup.plan_content,
            overwrite=True,
        )

        save_issue_reference(
            impl_path,
            setup.issue_number,
            setup.issue_url,
            setup.issue_title,
        )

        user_output(f"Created .impl/ folder from issue #{setup.issue_number}")

        # Write activation script
        script_path = write_worktree_activate_script(
            worktree_path=slot_result.worktree_path,
            post_create_commands=None,
        )

        # Print primary activation command with clipboard copy
        print_activation_instructions(script_path, source_branch=None, force=False)

        # Print combined activate + implement command
        user_output("\nTo activate and start implementation:")
        user_output(f"  source {script_path} && erk implement --here")

        # Print dangerous mode option (skip permission prompts)
        user_output("\nTo activate and start implementation (skip permissions):")
        user_output(f"  source {script_path} && erk implement --here --dangerous")
