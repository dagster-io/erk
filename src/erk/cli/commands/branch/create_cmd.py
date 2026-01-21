"""Branch create command - create a new branch with optional slot assignment."""

import sys

import click

from erk.cli.activation import (
    activation_config_activate_only,
    activation_config_for_implement,
    print_activation_instructions,
    render_activation_script,
    write_worktree_activate_script,
)
from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.output.output import user_output


@click.command("create", cls=CommandWithHiddenOptions)
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
@click.option(
    "--codespace",
    is_flag=True,
    help="Include --codespace flag for codespace-isolated implementation (uses default)",
)
@click.option(
    "--codespace-name",
    default=None,
    help="Use named codespace for isolated implementation",
)
@script_option
@click.pass_obj
def branch_create(
    ctx: ErkContext,
    branch_name: str | None,
    for_plan: str | None,
    no_slot: bool,
    force: bool,
    *,
    create_only: bool,
    dangerous: bool,
    docker: bool,
    codespace: bool,
    codespace_name: str | None,
    script: bool,
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

    if codespace and codespace_name is not None:
        user_output("Error: --codespace and --codespace-name cannot be used together.")
        raise SystemExit(1) from None

    if docker and (codespace or codespace_name is not None):
        user_output("Error: --docker and --codespace/--codespace-name cannot be used together.")
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

        # In script mode, output activation script path and exit
        if script:
            activation_script = render_activation_script(
                worktree_path=slot_result.worktree_path,
                target_subpath=None,
                post_cd_commands=None,
                final_message=f'echo "Prepared plan #{setup.issue_number} at $(pwd)"',
                comment="erk prepare activation script",
            )
            result = ctx.script_writer.write_activation_script(
                activation_script,
                command_name="prepare",
                comment=f"prepare {setup.issue_number}",
            )
            result.output_for_shell_integration()
            sys.exit(0)

        user_output(f"Created .impl/ folder from issue #{setup.issue_number}")

        # Handle script mode vs normal mode
        if script:
            # Build activation script that CDs to worktree, activates venv, and runs erk implement
            worktree_path = slot_result.worktree_path

            # Build implement command with flags
            implement_cmd = "erk implement"
            if docker:
                implement_cmd += " --docker"
            if codespace:
                implement_cmd += " --codespace"
            elif codespace_name is not None:
                implement_cmd += f" --codespace-name {codespace_name}"
            if dangerous:
                implement_cmd += " --dangerous"

            # Determine post-cd commands
            post_cd_commands: list[str] | None = None
            if not create_only:
                post_cd_commands = [implement_cmd]

            # Build the activation script
            script_content = render_activation_script(
                worktree_path=worktree_path,
                target_subpath=None,
                post_cd_commands=post_cd_commands,
                final_message='echo "Activated: $(pwd)"',
                comment="prepare activation",
            )

            result = ctx.script_writer.write_activation_script(
                script_content,
                command_name="prepare",
                comment=f"activate {worktree_path.name} and implement",
            )
            result.output_for_shell_integration()
        else:
            # Write activation script for manual sourcing
            script_path = write_worktree_activate_script(
                worktree_path=slot_result.worktree_path,
                post_create_commands=None,
            )

            # Print single activation command based on flags
            # Determine activation config from CLI flags
            if create_only:
                config = activation_config_activate_only()
            else:
                # Convert codespace flag/name to ActivationConfig format:
                # --codespace (flag only) → "" (empty string = default)
                # --codespace-name NAME → "NAME" (named)
                # neither → None (not using codespace)
                codespace_value: str | None = None
                if codespace:
                    codespace_value = ""  # Use default codespace
                elif codespace_name is not None:
                    codespace_value = codespace_name

                config = activation_config_for_implement(
                    docker=docker, dangerous=dangerous, codespace=codespace_value
                )

            print_activation_instructions(
                script_path,
                source_branch=None,
                force=False,
                config=config,
                copy=True,
            )
