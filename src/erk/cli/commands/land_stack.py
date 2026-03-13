"""Stack landing for `erk land --stack`.

Lands an entire Graphite stack bottom-up while preserving the existing land
command's validation and cleanup guarantees:
- all confirmations happen before mutations
- child PR base updates are verified before landing a parent branch
- local cleanup reuses the same branch/worktree cleanup paths as `erk land`
"""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.land_cmd import (
    CleanupContext,
    _cleanup_landed_branch,
    check_unresolved_comments,
)
from erk.cli.commands.land_learn import _create_learn_pr_for_merged_branch
from erk.cli.commands.navigation_helpers import check_clean_working_tree
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    run_objective_update_after_land,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.types import MergeError, PRDetails, PRNotFound
from erk_shared.gateway.gt.operations.land_pr import (
    get_direct_child_branches_for_land,
    reparent_child_pr_bases_for_land,
)
from erk_shared.output.output import machine_output, user_output


@dataclass(frozen=True)
class StackLandEntry:
    """Validated stack entry ready for execution."""

    branch: str
    pr_number: int
    worktree_path: Path | None
    pr_id: str | None
    objective_number: int | None


@dataclass(frozen=True)
class StackLandPlan:
    """Pre-validated stack landing plan."""

    main_repo_root: Path
    trunk_branch: str
    current_branch: str
    current_worktree_path: Path | None
    entries: tuple[StackLandEntry, ...]
    cleanup_confirmed: bool


def execute_land_stack(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    script: bool,
    force: bool,
    pull_flag: bool,
    no_delete: bool,
    skip_learn: bool,
) -> None:
    """Land the current Graphite stack bottom-up."""
    plan = _prepare_stack_land(
        ctx,
        repo=repo,
        force=force,
        no_delete=no_delete,
    )
    _display_stack_summary(
        plan.entries, no_delete=no_delete, cleanup_confirmed=plan.cleanup_confirmed
    )

    if ctx.dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        raise SystemExit(0)

    merged_entries: list[StackLandEntry] = []
    for index, entry in enumerate(plan.entries):
        if index > 0:
            user_output(
                click.style(f"  Rebasing {entry.branch} onto {plan.trunk_branch}...", dim=True)
            )
            _rebase_entry_onto_trunk(
                ctx,
                main_repo_root=plan.main_repo_root,
                branch=entry.branch,
                trunk_branch=plan.trunk_branch,
                merged_entries=merged_entries,
            )

        child_branches = get_direct_child_branches_for_land(ctx, plan.main_repo_root, entry.branch)
        if child_branches:
            user_output(
                click.style(f"  Reparenting {len(child_branches)} child branch(es)...", dim=True)
            )
            _reparent_children_for_stack(
                ctx,
                main_repo_root=plan.main_repo_root,
                parent_branch=entry.branch,
                child_branches=child_branches,
                trunk_branch=plan.trunk_branch,
                merged_entries=merged_entries,
            )

        _merge_entry(
            ctx,
            main_repo_root=plan.main_repo_root,
            entry=entry,
            merged_entries=merged_entries,
            total_entries=len(plan.entries),
        )
        merged_entries.append(entry)
        _run_post_merge_hooks(
            ctx,
            entry=entry,
            main_repo_root=plan.main_repo_root,
            skip_learn=skip_learn,
        )

    if not no_delete and plan.cleanup_confirmed:
        _cleanup_stack_after_success(
            ctx,
            repo=repo,
            plan=plan,
        )
    elif not no_delete:
        user_output("Local branches and worktrees preserved.")

    if pull_flag:
        _pull_trunk_after_stack_land(
            ctx,
            main_repo_root=plan.main_repo_root,
            trunk_branch=plan.trunk_branch,
        )

    _write_stack_activation_script_if_needed(
        ctx,
        main_repo_root=plan.main_repo_root,
        script=script,
        current_worktree_path=plan.current_worktree_path,
    )

    user_output(
        click.style("\n✓", fg="green", bold=True)
        + f" Stack landed: {len(plan.entries)} PR(s) merged successfully"
    )
    raise SystemExit(0)


def _prepare_stack_land(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    force: bool,
    no_delete: bool,
) -> StackLandPlan:
    main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
    check_clean_working_tree(ctx)
    user_output(click.style("  ✓", fg="green") + " Working tree is clean")

    Ensure.invariant(
        ctx.branch_manager.is_graphite_managed(),
        "--stack requires Graphite for stack tracking.\n\n"
        "To enable Graphite: erk config set use_graphite true",
    )
    user_output(click.style("  ✓", fg="green") + " Graphite stack management confirmed")

    current_branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(ctx.cwd),
        "Not currently on a branch (detached HEAD).",
    )
    current_worktree_path = ctx.git.worktree.find_worktree_for_branch(
        main_repo_root, current_branch
    )
    trunk_branch = ctx.git.branch.detect_trunk_branch(main_repo_root)
    Ensure.invariant(
        current_branch != trunk_branch,
        f"Cannot use --stack from trunk branch '{trunk_branch}'.\n"
        "Check out a stacked branch first, then retry: erk land --stack",
    )
    user_output(click.style("  ✓", fg="green") + f" Current branch: {current_branch}")
    stack = ctx.branch_manager.get_branch_stack(main_repo_root, current_branch)

    Ensure.invariant(
        stack is not None,
        f"Branch '{current_branch}' is not in a Graphite stack.\n"
        "Use 'erk land' without --stack for non-stacked branches.",
    )
    assert stack is not None
    Ensure.invariant(
        len(stack) >= 2,
        f"Stack has no branches to land (only contains trunk '{stack[0]}').",
    )
    user_output(click.style("  ✓", fg="green") + f" Stack has {len(stack) - 1} branch(es) to land")

    entries = _validate_stack_entries(
        ctx,
        main_repo_root=main_repo_root,
        stack_branches=stack[1:],
        trunk_branch=trunk_branch,
        force=force,
    )

    cleanup_confirmed = True
    if not no_delete and not force and not ctx.dry_run:
        cleanup_confirmed = ctx.console.confirm(
            f"After landing, clean up {len(entries)} local branch/worktree entr"
            + ("y" if len(entries) == 1 else "ies")
            + "?",
            default=True,
        )

    return StackLandPlan(
        main_repo_root=main_repo_root,
        trunk_branch=trunk_branch,
        current_branch=current_branch,
        current_worktree_path=current_worktree_path,
        entries=tuple(entries),
        cleanup_confirmed=cleanup_confirmed,
    )


def _validate_stack_entries(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    stack_branches: list[str],
    trunk_branch: str,
    force: bool,
) -> list[StackLandEntry]:
    entries: list[StackLandEntry] = []
    root_needs_clean_check = False
    user_output(click.style("  Validating stack entries...", dim=True))

    for index, branch in enumerate(stack_branches):
        pr_details = ctx.github.get_pr_for_branch(main_repo_root, branch)
        Ensure.invariant(
            not isinstance(pr_details, PRNotFound),
            f"No pull request found for branch '{branch}' in the stack.",
        )
        assert isinstance(pr_details, PRDetails)

        expected_base = trunk_branch if index == 0 else stack_branches[index - 1]
        Ensure.invariant(
            pr_details.state == "OPEN",
            f"PR #{pr_details.number} for branch '{branch}' is not open "
            f"(state: {pr_details.state}).\n"
            "All PRs in the stack must be open to land.",
        )
        Ensure.invariant(
            pr_details.base_ref_name == expected_base,
            f"PR #{pr_details.number} [{branch}] targets '{pr_details.base_ref_name}' "
            f"but should target '{expected_base}'.\n\n"
            "The GitHub PR bases no longer match the local Graphite stack.\n"
            "Run: gt restack --no-interactive && gt submit --no-interactive\n"
            "Then retry: erk land --stack",
        )

        check_unresolved_comments(ctx, main_repo_root, pr_details.number, force=force)

        worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)
        if worktree_path is not None and ctx.git.status.has_uncommitted_changes(worktree_path):
            Ensure.invariant(
                False,
                f"Branch '{branch}' has uncommitted changes in worktree {worktree_path}.\n"
                "Commit or stash them before landing the stack.",
            )
        if worktree_path is None:
            root_needs_clean_check = True

        entries.append(
            StackLandEntry(
                branch=branch,
                pr_number=pr_details.number,
                worktree_path=worktree_path,
                pr_id=ctx.plan_backend.resolve_pr_number_for_branch(main_repo_root, branch),
                objective_number=get_objective_for_branch(ctx, main_repo_root, branch),
            )
        )
        user_output(
            click.style("  ✓", fg="green")
            + f" PR #{pr_details.number} [{branch}]: open, base correct, clean"
        )

    if root_needs_clean_check and ctx.git.status.has_uncommitted_changes(main_repo_root):
        Ensure.invariant(
            False,
            f"Root worktree at {main_repo_root} has uncommitted changes.\n"
            "Commit or stash them before landing the stack.",
        )

    return entries


def _display_stack_summary(
    entries: tuple[StackLandEntry, ...],
    *,
    no_delete: bool,
    cleanup_confirmed: bool,
) -> None:
    user_output(f"\nLanding {len(entries)} PR(s) bottom-up:\n")
    for index, entry in enumerate(entries, start=1):
        user_output(f"  {index}. PR #{entry.pr_number} [{entry.branch}]")

    if no_delete:
        user_output("\nLocal cleanup: disabled (--no-delete)")
    elif cleanup_confirmed:
        user_output("\nLocal cleanup: enabled after full success")
    else:
        user_output("\nLocal cleanup: skipped by user")


def _rebase_entry_onto_trunk(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    branch: str,
    trunk_branch: str,
    merged_entries: list[StackLandEntry],
) -> None:
    try:
        ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk_branch)
    except RuntimeError as exc:
        Ensure.invariant(
            False,
            _format_partial_failure(
                merged_entries=merged_entries,
                message=(
                    f"Failed to fetch origin/{trunk_branch} before rebasing '{branch}'.\n\n"
                    f"{exc}\n\n"
                    "Then retry: erk land --stack"
                ),
            ),
        )

    rebase_cwd = _resolve_rebase_cwd(ctx, main_repo_root=main_repo_root, branch=branch)
    rebase_result = ctx.git.rebase.rebase_onto(rebase_cwd, f"origin/{trunk_branch}")
    if not rebase_result.success:
        try:
            ctx.git.rebase.rebase_abort(rebase_cwd)
        except RuntimeError as exc:
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Automatic rebase abort failed in {rebase_cwd}: {exc}"
            )

        conflict_list = (
            ", ".join(rebase_result.conflict_files)
            if rebase_result.conflict_files
            else "unknown files"
        )
        Ensure.invariant(
            False,
            _format_partial_failure(
                merged_entries=merged_entries,
                message=(
                    f"Rebase conflicts on branch '{branch}': {conflict_list}\n\n"
                    f"Resolve conflicts in:\n"
                    f"  cd {rebase_cwd}\n"
                    f"  git rebase origin/{trunk_branch}\n"
                    "Then retry: erk land --stack"
                ),
            ),
        )

    try:
        ctx.branch_manager.retrack_branch(main_repo_root, branch)
    except Exception as exc:
        Ensure.invariant(
            False,
            _format_partial_failure(
                merged_entries=merged_entries,
                message=(
                    f"Failed to re-track rebased branch '{branch}' in Graphite.\n\n"
                    f"{exc}\n\n"
                    "Then retry: erk land --stack"
                ),
            ),
        )

    push_result = ctx.git.remote.push_to_remote(
        rebase_cwd,
        "origin",
        branch,
        set_upstream=False,
        force=True,
    )
    if isinstance(push_result, PushError):
        Ensure.invariant(
            False,
            _format_partial_failure(
                merged_entries=merged_entries,
                message=(
                    f"Failed to push rebased branch '{branch}' to origin.\n\n"
                    f"{push_result.message}\n\n"
                    "Then retry: erk land --stack"
                ),
            ),
        )

    user_output(click.style("  ✓", fg="green") + f" Rebased onto {trunk_branch}")


def _resolve_rebase_cwd(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    branch: str,
) -> Path:
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)
    if worktree_path is not None:
        return worktree_path

    ctx.branch_manager.checkout_branch(main_repo_root, branch)
    return main_repo_root


def _reparent_children_for_stack(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    parent_branch: str,
    child_branches: list[str],
    trunk_branch: str,
    merged_entries: list[StackLandEntry],
) -> None:
    error_message = reparent_child_pr_bases_for_land(
        ctx,
        main_repo_root,
        child_branches=child_branches,
        new_base=trunk_branch,
    )
    if error_message is not None:
        Ensure.invariant(
            False,
            _format_partial_failure(merged_entries=merged_entries, message=error_message),
        )

    local_branches = set(ctx.git.branch.list_local_branches(main_repo_root))
    for child_branch in child_branches:
        if child_branch not in local_branches:
            continue
        try:
            ctx.branch_manager.track_branch(main_repo_root, child_branch, trunk_branch)
        except Exception as exc:
            Ensure.invariant(
                False,
                _format_partial_failure(
                    merged_entries=merged_entries,
                    message=(
                        f"Failed to update local Graphite tracking for child branch "
                        f"'{child_branch}' after landing '{parent_branch}'.\n\n"
                        f"{exc}\n\n"
                        "Then retry: erk land --stack"
                    ),
                ),
            )

    user_output(click.style("  ✓", fg="green") + f" Reparented children to {trunk_branch}")


def _merge_entry(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    entry: StackLandEntry,
    merged_entries: list[StackLandEntry],
    total_entries: int,
) -> None:
    pr_details = ctx.github.get_pr(main_repo_root, entry.pr_number)
    Ensure.invariant(
        not isinstance(pr_details, PRNotFound),
        f"Pull request #{entry.pr_number} disappeared before merge.",
    )
    assert isinstance(pr_details, PRDetails)

    merge_result = ctx.github.merge_pr(
        main_repo_root,
        entry.pr_number,
        squash=True,
        verbose=False,
        subject=f"{pr_details.title} (#{entry.pr_number})" if pr_details.title else None,
        body=pr_details.body or None,
    )
    if isinstance(merge_result, MergeError):
        Ensure.invariant(
            False,
            _format_partial_failure(
                merged_entries=merged_entries,
                message=(
                    f"Failed to merge PR #{entry.pr_number} [{entry.branch}].\n\n"
                    f"{merge_result.message}\n\n"
                    "Then retry: erk land --stack"
                ),
            ),
        )

    deleted_remote_branch = ctx.github.delete_remote_branch(main_repo_root, entry.branch)
    if not deleted_remote_branch:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Remote branch '{entry.branch}' was not deleted automatically."
        )
    user_output(
        click.style("✓", fg="green")
        + f" Merged PR #{entry.pr_number} [{entry.branch}] "
        + f"({len(merged_entries) + 1}/{total_entries})"
    )


def _run_post_merge_hooks(
    ctx: ErkContext,
    *,
    entry: StackLandEntry,
    main_repo_root: Path,
    skip_learn: bool,
) -> None:
    if not skip_learn and entry.pr_id is not None:
        try:
            _create_learn_pr_for_merged_branch(
                ctx,
                pr_id=entry.pr_id,
                merged_pr_number=entry.pr_number,
                main_repo_root=main_repo_root,
                cwd=ctx.cwd,
            )
        except Exception as exc:
            user_output(
                click.style("Warning: ", fg="yellow") + f"Learn PR failed for {entry.branch}: {exc}"
            )

    if entry.objective_number is not None:
        try:
            run_objective_update_after_land(
                ctx,
                objective=entry.objective_number,
                pr=entry.pr_number,
                branch=entry.branch,
                worktree_path=main_repo_root,
            )
        except Exception as exc:
            user_output(
                click.style("Warning: ", fg="yellow")
                + f"Objective update failed for {entry.branch}: {exc}"
            )


def _cleanup_stack_after_success(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    plan: StackLandPlan,
) -> None:
    if any(entry.worktree_path is None for entry in plan.entries):
        ctx.branch_manager.checkout_branch(plan.main_repo_root, plan.trunk_branch)

    user_output(click.style(f"  Cleaning up {len(plan.entries)} branch(es)...", dim=True))
    cleanup_warnings: list[str] = []
    for entry in plan.entries:
        cleanup = CleanupContext(
            ctx=ctx,
            repo=repo,
            branch=entry.branch,
            worktree_path=ctx.git.worktree.find_worktree_for_branch(
                plan.main_repo_root,
                entry.branch,
            ),
            main_repo_root=plan.main_repo_root,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            no_delete=False,
            skip_activation_output=True,
            cleanup_confirmed=True,
        )
        try:
            _cleanup_landed_branch(cleanup)
        except Exception as exc:
            cleanup_warnings.append(f"{entry.branch}: {exc}")

    if cleanup_warnings:
        user_output(click.style("Warning: ", fg="yellow") + "Stack merged, but cleanup had issues:")
        for warning in cleanup_warnings:
            user_output(f"  - {warning}")


def _pull_trunk_after_stack_land(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    trunk_branch: str,
) -> None:
    current_branch = ctx.git.branch.get_current_branch(main_repo_root)
    if current_branch != trunk_branch:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Skipping pull because {main_repo_root} is on "
            + f"'{current_branch}', not '{trunk_branch}'."
        )
        return

    try:
        ctx.git.remote.fetch_branch(main_repo_root, "origin", trunk_branch)
    except RuntimeError:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Could not fetch origin/{trunk_branch} before pull."
        )
        return

    divergence = ctx.git.branch.is_branch_diverged_from_remote(
        main_repo_root,
        trunk_branch,
        "origin",
    )
    if divergence.is_diverged:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Local {trunk_branch} has diverged from origin/{trunk_branch}.\n"
            + f"  (local is {divergence.ahead} ahead, {divergence.behind} behind)\n"
            + "  Skipping pull."
        )
        return
    if divergence.behind == 0:
        return

    user_output(f"Pulling latest changes from origin/{trunk_branch}...")
    try:
        ctx.git.remote.pull_branch(main_repo_root, "origin", trunk_branch, ff_only=True)
    except RuntimeError:
        user_output(
            click.style("Warning: ", fg="yellow") + "git pull failed (try running manually)"
        )


def _write_stack_activation_script_if_needed(
    ctx: ErkContext,
    *,
    main_repo_root: Path,
    script: bool,
    current_worktree_path: Path | None,
) -> None:
    if not script:
        return

    target_path = ctx.cwd
    worktree_gone = current_worktree_path is not None and not ctx.git.worktree.path_exists(
        current_worktree_path
    )
    if worktree_gone:
        target_path = main_repo_root

    script_content = render_activation_script(
        worktree_path=target_path,
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Land complete"',
        comment="land complete (direct execution, no navigation)",
    )
    script_result = ctx.script_writer.write_activation_script(
        script_content,
        command_name="land",
        comment="no-op",
    )
    machine_output(str(script_result.path), nl=False)


def _format_partial_failure(
    *,
    merged_entries: list[StackLandEntry],
    message: str,
) -> str:
    if not merged_entries:
        return message

    merged_lines = [f"  - PR #{entry.pr_number} [{entry.branch}]" for entry in merged_entries]
    return "Merged so far:\n" + "\n".join(merged_lines) + "\n\n" + message
