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
from erk.cli.commands.navigation_helpers import find_assignment_by_worktree_path
from erk.cli.commands.slot.common import allocate_slot_for_branch, update_slot_assignment_tip
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_pool import load_pool_state
from erk_shared.gateway.git.branch_ops.types import BranchAlreadyExists
from erk_shared.impl_folder import create_impl_folder, save_plan_ref
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.output.output import user_output
from erk_shared.plan_store import get_plan_backend
from erk_shared.plan_store.types import PlanNotFound


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
@click.option(
    "--new-slot", is_flag=True, help="Force allocation of a new slot instead of stacking in place"
)
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
    new_slot: bool,
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

    if new_slot and no_slot:
        user_output("Error: --new-slot and --no-slot cannot be used together.")
        raise SystemExit(1) from None

    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Plan setup - fetches plan and derives branch name if --for-plan is used
    setup: IssueBranchSetup | None = None
    plan_backend = None

    if for_plan is not None:
        issue_number = parse_issue_identifier(for_plan)
        result = ctx.plan_store.get_plan(repo.root, str(issue_number))
        if isinstance(result, PlanNotFound):
            raise click.ClickException(f"Issue #{issue_number} not found")
        plan = result

        plan_backend = get_plan_backend(ctx.global_config)
        result = prepare_plan_for_worktree(
            plan, ctx.time.now(), plan_backend=plan_backend, warn_non_open=True
        )
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

    # Detect trunk branch (needed for both paths)
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)
    if trunk is None:
        user_output("Error: Could not detect trunk branch.")
        raise SystemExit(1) from None

    # Check if branch already exists
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    branch_exists_locally = branch_name in local_branches

    # PLAN_BACKEND_SPLIT: draft-PR backend tracks existing remote branch;
    # github backend creates new branch
    if setup is not None and plan_backend == "draft_pr":
        # Draft PR backend: branch was created by plan-save, so it's expected to exist
        if branch_exists_locally:
            user_output(f"Using existing branch: {branch_name}")
        else:
            # Branch only on remote — fetch and create local tracking branch
            ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)
            ctx.branch_manager.create_tracking_branch(
                repo.root, branch_name, f"origin/{branch_name}"
            )
            user_output(f"Created tracking branch: {branch_name}")
        ctx.branch_manager.track_branch(repo.root, branch_name, trunk)
    elif setup is None or plan_backend == "github":
        # Standard path: branch must NOT already exist
        if branch_exists_locally:
            user_output(
                f"Error: Branch '{branch_name}' already exists.\n"
                "Use `erk br assign` to assign an existing branch to a slot."
            )
            raise SystemExit(1) from None

        # Stack on current branch if we're on a non-trunk branch
        current_branch = ctx.git.branch.get_current_branch(repo.root)
        if current_branch and current_branch != trunk:
            parent_branch = current_branch
        else:
            parent_branch = trunk

        result = ctx.branch_manager.create_branch(repo.root, branch_name, parent_branch)
        if isinstance(result, BranchAlreadyExists):
            user_output(f"Error: {result.message}")
            raise SystemExit(1) from None
        user_output(f"Created branch: {branch_name}")
    else:
        raise RuntimeError(f"Unexpected plan_backend: {plan_backend!r}")

    # If --no-slot is specified, we're done (but warn about .impl if --for-plan was used)
    if no_slot:
        if setup is not None:
            user_output(
                click.style("Note: ", fg="yellow")
                + ".impl folder not created (no worktree allocated)"
            )
        return

    # Detect if running in an assigned slot (for stack-in-place)
    state = load_pool_state(repo.pool_json_path)
    current_assignment = None
    if state is not None and not new_slot:
        current_assignment = find_assignment_by_worktree_path(state, repo.root)

    if current_assignment is not None:
        # Stack in place — update assignment to new tip, no new slot
        # state is guaranteed non-None since current_assignment was found in it
        assert state is not None
        slot_result = update_slot_assignment_tip(
            repo.pool_json_path,
            state,
            current_assignment,
            branch_name=branch_name,
            now=ctx.time.now().isoformat(),
        )
        user_output(
            click.style(
                f"✓ Stacked {branch_name} in {slot_result.slot_name} (in place)", fg="green"
            )
        )
    else:
        # Not in a slot — allocate normally
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

        save_plan_ref(
            impl_path,
            provider="github",
            plan_id=str(setup.issue_number),
            url=setup.issue_url,
            labels=(),
            objective_id=setup.objective_issue,
        )

        # In script mode, output activation script path and exit
        if script:
            activation_script = render_activation_script(
                worktree_path=slot_result.worktree_path,
                target_subpath=None,
                post_cd_commands=None,
                final_message=f'echo "Prepared plan #{setup.issue_number} at $(pwd)"',
                comment="erk branch create activation script",
            )
            result = ctx.script_writer.write_activation_script(
                activation_script,
                command_name="branch-create",
                comment=f"branch create --for-plan {setup.issue_number}",
            )
            result.output_for_shell_integration()
            sys.exit(0)

        user_output(f"Created .impl/ folder from plan #{setup.issue_number}")

        # Write activation script
        activate_script_path = write_worktree_activate_script(
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
            activate_script_path,
            source_branch=None,
            force=False,
            config=config,
            copy=True,
        )
