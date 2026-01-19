import click

from erk.cli.activation import (
    ENABLE_ACTIVATION_SCRIPTS,
    ensure_worktree_activate_script,
    print_activation_instructions,
    render_activation_script,
)
from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
    check_pending_learn_marker,
    get_slot_name_for_worktree,
    render_deferred_deletion_commands,
    resolve_down_navigation,
    verify_pr_closed_or_merged,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.graphite_command import GraphiteCommandWithHiddenOptions
from erk.cli.help_formatter import script_option
from erk.core.context import ErkContext
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.output.output import machine_output, user_output


@click.command("down", cls=GraphiteCommandWithHiddenOptions)
@script_option
@click.option(
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating down",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force deletion even if marker exists or PR is open (prompts)",
)
@click.pass_obj
def down_cmd(ctx: ErkContext, script: bool, delete_current: bool, force: bool) -> None:
    """Move to parent branch in worktree stack.

    Prints the activation path for the target worktree.
    To navigate automatically, enable shell integration:

      erk config set shell_integration true
      erk init --shell  # Then restart your shell

    With shell integration enabled:
      erk down

    Without shell integration:
      source <(erk down --script)  # Or use the printed activation path

    Requires Graphite to be enabled: 'erk config set use_graphite true'
    """
    # Validate preconditions upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)
    trunk_branch = ctx.trunk_branch

    # Get current branch
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    # Store current worktree path for deletion (before navigation)
    # Find the worktree for the current branch
    current_worktree_path = None
    if delete_current:
        current_worktree_path = Ensure.not_none(
            ctx.git.find_worktree_for_branch(repo.root, current_branch),
            f"Cannot find worktree for current branch '{current_branch}'.",
        )

    # Safety checks before navigation (if --delete-current flag is set)
    if delete_current and current_worktree_path is not None:
        check_clean_working_tree(ctx)
        verify_pr_closed_or_merged(ctx, repo.root, current_branch, force)
        # Check for pending learn marker
        check_pending_learn_marker(current_worktree_path, force)

    # Get all worktrees for checking if target has a worktree
    worktrees = ctx.git.list_worktrees(repo.root)

    # Resolve navigation to get target branch or 'root' (may auto-create worktree)
    target_name, was_created = resolve_down_navigation(
        ctx,
        repo=repo,
        current_branch=current_branch,
        worktrees=worktrees,
        trunk_branch=trunk_branch,
    )

    # Show creation message if worktree was just created
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree for {click.style(target_name, fg='yellow')} and moved to it"
        )

    # Prepare deferred deletion commands if --delete-current is set
    deletion_commands: list[str] | None = None
    if delete_current and current_worktree_path is not None:
        main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
        slot_name = get_slot_name_for_worktree(repo.pool_json_path, current_worktree_path)
        use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
        deletion_commands = render_deferred_deletion_commands(
            worktree_path=current_worktree_path,
            branch=current_branch,
            slot_name=slot_name,
            is_graphite_managed=use_graphite,
            main_repo_root=main_repo_root,
        )

    # Check if target_name refers to 'root' which means root repo
    if target_name == "root":
        if delete_current and current_worktree_path is not None:
            # Handle activation inline with deferred deletion
            root_path = repo.main_repo_root if repo.main_repo_root else repo.root
            if script:
                script_content = render_activation_script(
                    worktree_path=root_path,
                    target_subpath=compute_relative_path_in_worktree(worktrees, ctx.cwd),
                    post_cd_commands=deletion_commands,
                    final_message='echo "Went to root repo: $(pwd)"',
                    comment="work activate-script (root repo)",
                )
                result = ctx.script_writer.write_activation_script(
                    script_content,
                    command_name="down",
                    comment="activate root",
                )
                machine_output(str(result.path), nl=False)
            else:
                # Print activation instructions for opt-in workflow
                # SPECULATIVE: activation-scripts (objective #4954)
                if ENABLE_ACTIVATION_SCRIPTS:
                    script_path = ensure_worktree_activate_script(
                        worktree_path=root_path,
                        post_create_commands=None,
                    )
                    print_activation_instructions(
                        script_path,
                        source_branch=current_branch,
                        force=force,
                        mode="activate_only",
                        copy=True,
                    )

            # Deletion is deferred to script sourcing - no immediate cleanup
            raise SystemExit(0)
        else:
            # No cleanup needed, use standard activation
            activate_root_repo(
                ctx,
                repo=repo,
                script=script,
                command_name="down",
                post_cd_commands=None,
                source_branch=current_branch,
                force=force,
            )

    # Resolve target branch to actual worktree path
    target_wt_path = Ensure.not_none(
        ctx.git.find_worktree_for_branch(repo.root, target_name),
        f"Branch '{target_name}' has no worktree. This should not happen.",
    )

    if delete_current and current_worktree_path is not None:
        # Handle activation inline with deferred deletion
        Ensure.path_exists(ctx, target_wt_path, f"Worktree not found: {target_wt_path}")

        if script:
            activation_script = render_activation_script(
                worktree_path=target_wt_path,
                target_subpath=compute_relative_path_in_worktree(worktrees, ctx.cwd),
                post_cd_commands=deletion_commands,
                final_message='echo "Activated worktree: $(pwd)"',
                comment="work activate-script",
            )
            result = ctx.script_writer.write_activation_script(
                activation_script,
                command_name="down",
                comment=f"activate {target_wt_path.name}",
            )
            machine_output(str(result.path), nl=False)
        else:
            user_output(
                "Shell integration not detected. "
                "Run 'erk init --shell' to set up automatic activation."
            )
            user_output("\nOr use: source <(erk down --script)")

            # Print activation instructions for opt-in workflow
            # SPECULATIVE: activation-scripts (objective #4954)
            if ENABLE_ACTIVATION_SCRIPTS:
                script_path = ensure_worktree_activate_script(
                    worktree_path=target_wt_path,
                    post_create_commands=None,
                )
                print_activation_instructions(
                    script_path,
                    source_branch=current_branch,
                    force=force,
                    mode="activate_only",
                    copy=True,
                )

        # Deletion is deferred to script sourcing - no immediate cleanup
        raise SystemExit(0)
    else:
        # No cleanup needed, use standard activation
        activate_worktree(
            ctx=ctx,
            repo=repo,
            target_path=target_wt_path,
            script=script,
            command_name="down",
            preserve_relative_path=True,
            post_cd_commands=None,
            source_branch=current_branch,
            force=force,
        )
