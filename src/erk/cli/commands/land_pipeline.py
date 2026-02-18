"""Linear pipelines for the land command.

Two pipelines bridge the shell script serialization boundary:
- Validation pipeline: runs in `erk land` CLI, gathers all state and confirmations
- Execution pipeline: runs in `erk exec land-execute`, performs mutations

Each step: (ErkContext, LandState) -> LandState | LandError
"""

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import click

from erk.cli.commands.navigation_helpers import check_clean_working_tree
from erk.cli.commands.objective_helpers import (
    get_objective_for_branch,
    prompt_objective_update,
)
from erk.cli.commands.review_pr_cleanup import cleanup_review_pr
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.ensure_ideal import EnsureIdeal
from erk.core.context import ErkContext
from erk_shared.gateway.github.types import MergeError, PRDetails
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.types import LandPrError
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanHeaderNotFoundError, PlanNotFound
from erk_shared.stack.validation import validate_parent_is_trunk

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LandState:
    """Immutable state threaded through both land pipelines."""

    # CLI inputs
    cwd: Path
    force: bool
    script: bool
    pull_flag: bool
    no_delete: bool
    up_flag: bool
    dry_run: bool
    target_arg: str | None

    # Resolved target (populated by resolve_target)
    repo_root: Path
    main_repo_root: Path
    branch: str
    pr_number: int
    pr_details: PRDetails | None
    worktree_path: Path | None
    is_current_branch: bool
    use_graphite: bool
    target_child_branch: str | None

    # Derived (populated by later steps)
    objective_number: int | None
    plan_id: str | None
    cleanup_confirmed: bool
    merged_pr_number: int | None


@dataclass(frozen=True)
class LandError:
    """Error result from a pipeline step."""

    phase: str
    error_type: str
    message: str
    details: dict[str, str]


# ---------------------------------------------------------------------------
# Pipeline Step Type
# ---------------------------------------------------------------------------

LandStep = Callable[[ErkContext, LandState], LandState | LandError]


# ---------------------------------------------------------------------------
# Validation Pipeline Steps
# ---------------------------------------------------------------------------


def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Resolve landing target from CLI arguments.

    Expects repo_root and main_repo_root to be pre-populated by the CLI handler
    (via discover_repo_context before pipeline entry).

    Dispatches by target_arg:
    - None => current branch
    - digit/URL => PR number
    - else => branch name

    Populates: branch, pr_number, pr_details, worktree_path, is_current_branch,
    use_graphite, target_child_branch.
    """
    from erk.cli.commands.land_cmd import parse_argument

    repo_root = state.repo_root
    main_repo_root = state.main_repo_root

    if state.target_arg is None:
        return _resolve_current_branch(ctx, state, repo_root, main_repo_root)

    parsed = parse_argument(state.target_arg)

    if parsed.arg_type == "branch":
        return _resolve_branch(
            ctx,
            state,
            repo_root=repo_root,
            main_repo_root=main_repo_root,
            branch_name=state.target_arg,
        )

    # PR number or URL
    pr_number = parsed.pr_number
    if pr_number is None:
        return LandError(
            phase="resolve_target",
            error_type="invalid_target",
            message=f"Invalid PR identifier: {state.target_arg}\n"
            "Expected a PR number (e.g., 123) or GitHub URL.",
            details={"target": state.target_arg},
        )
    return _resolve_pr(
        ctx, state, repo_root=repo_root, main_repo_root=main_repo_root, pr_number=pr_number
    )


def _resolve_current_branch(
    ctx: ErkContext,
    state: LandState,
    repo_root: Path,
    main_repo_root: Path,
) -> LandState | LandError:
    """Resolve target when landing current branch."""
    check_clean_working_tree(ctx)

    current_branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(ctx.cwd),
        "Not currently on a branch (detached HEAD)",
    )

    current_worktree_path = Ensure.not_none(
        ctx.git.worktree.find_worktree_for_branch(repo_root, current_branch),
        f"Cannot find worktree for current branch '{current_branch}'.",
    )

    # Validate --up preconditions BEFORE any mutations
    target_child_branch: str | None = None
    if state.up_flag:
        Ensure.invariant(
            ctx.branch_manager.is_graphite_managed(),
            "--up flag requires Graphite for child branch tracking.\n\n"
            + "To enable Graphite: erk config set use_graphite true\n\n"
            + "Without --up, erk land will navigate to trunk after landing.",
        )
        children = Ensure.truthy(
            ctx.branch_manager.get_child_branches(repo_root, current_branch),
            f"Cannot use --up: branch '{current_branch}' has no children.\n"
            "Use 'erk land' without --up to return to trunk.",
        )
        children_list = ", ".join(f"'{c}'" for c in children)
        Ensure.invariant(
            len(children) == 1,
            f"Cannot use --up: branch '{current_branch}' has multiple children: "
            f"{children_list}.\n"
            "Use 'erk land' without --up, then 'erk co <branch>' to choose.",
        )
        target_child_branch = children[0]

    # Validate Graphite stack
    use_graphite = ctx.branch_manager.is_graphite_managed()
    if use_graphite:
        parent = ctx.graphite.get_parent_branch(ctx.git, repo_root, current_branch)
        trunk = ctx.git.branch.detect_trunk_branch(repo_root)
        validation_error = validate_parent_is_trunk(
            current_branch=current_branch,
            parent_branch=parent,
            trunk_branch=trunk,
        )
        Ensure.invariant(
            validation_error is None,
            validation_error.message if validation_error else "",
        )

    # Look up PR
    pr_details = EnsureIdeal.unwrap_pr(
        ctx.github.get_pr_for_branch(main_repo_root, current_branch),
        f"No pull request found for branch '{current_branch}'.",
    )

    return dataclasses.replace(
        state,
        branch=current_branch,
        pr_number=pr_details.number,
        pr_details=pr_details,
        worktree_path=current_worktree_path,
        is_current_branch=True,
        use_graphite=use_graphite,
        target_child_branch=target_child_branch,
    )


def _resolve_pr(
    ctx: ErkContext,
    state: LandState,
    *,
    repo_root: Path,
    main_repo_root: Path,
    pr_number: int,
) -> LandState | LandError:
    """Resolve target when landing by PR number."""
    from erk.cli.commands.land_cmd import resolve_branch_for_pr

    if state.up_flag:
        return LandError(
            phase="resolve_target",
            error_type="up_with_pr",
            message="Cannot use --up when specifying a PR.\n"
            "The --up flag only works when landing the current branch's PR.",
            details={"pr_number": str(pr_number)},
        )

    pr_details = EnsureIdeal.unwrap_pr(
        ctx.github.get_pr(main_repo_root, pr_number),
        f"Pull request #{pr_number} not found.",
    )

    branch = resolve_branch_for_pr(ctx, main_repo_root, pr_details)
    current_branch = ctx.git.branch.get_current_branch(ctx.cwd)
    is_current_branch = current_branch == branch
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch)

    return dataclasses.replace(
        state,
        branch=branch,
        pr_number=pr_details.number,
        pr_details=pr_details,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        use_graphite=False,
        target_child_branch=None,
    )


def _resolve_branch(
    ctx: ErkContext,
    state: LandState,
    *,
    repo_root: Path,
    main_repo_root: Path,
    branch_name: str,
) -> LandState | LandError:
    """Resolve target when landing by branch name."""
    pr_details = EnsureIdeal.unwrap_pr(
        ctx.github.get_pr_for_branch(main_repo_root, branch_name),
        f"No pull request found for branch '{branch_name}'.",
    )

    current_branch = ctx.git.branch.get_current_branch(ctx.cwd)
    is_current_branch = current_branch == branch_name
    worktree_path = ctx.git.worktree.find_worktree_for_branch(main_repo_root, branch_name)

    return dataclasses.replace(
        state,
        branch=branch_name,
        pr_number=pr_details.number,
        pr_details=pr_details,
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        use_graphite=False,
        target_child_branch=None,
    )


def validate_pr(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Validate PR is ready to land.

    Checks: clean working tree, PR state=OPEN, PR base=trunk, unresolved comments.
    """
    from erk.cli.commands.land_cmd import check_unresolved_comments

    # Clean working tree check (only for current branch)
    if state.is_current_branch:
        check_clean_working_tree(ctx)

    # PR state is OPEN
    if state.pr_details is None:
        return LandError(
            phase="validate_pr",
            error_type="no_pr_details",
            message=f"PR details not available for #{state.pr_number}.",
            details={},
        )

    Ensure.invariant(
        state.pr_details.state == "OPEN",
        f"Pull request #{state.pr_number} is not open "
        f"(state: {state.pr_details.state}).\n"
        f"PR #{state.pr_number} has already been {state.pr_details.state.lower()}.",
    )

    # PR base is trunk (skip for Graphite)
    if not state.use_graphite:
        trunk = ctx.git.branch.detect_trunk_branch(state.main_repo_root)
        Ensure.invariant(
            state.pr_details.base_ref_name == trunk,
            f"PR #{state.pr_number} targets '{state.pr_details.base_ref_name}' "
            + f"but should target '{trunk}'.\n\n"
            + "The GitHub PR's base branch has diverged from your local stack.\n"
            + "Run: gt restack && gt submit\n"
            + f"Then retry: erk land {state.branch}",
        )

    # Unresolved comments check
    check_unresolved_comments(ctx, state.main_repo_root, state.pr_number, force=state.force)

    return state


def check_learn_status(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Check learn status for plan branches, prompt if needed.

    Populates: plan_id.
    """
    from erk.cli.commands.land_cmd import _check_learn_status_and_prompt

    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(state.main_repo_root, state.branch)

    if plan_id is not None and (
        state.is_current_branch or state.worktree_path is not None
    ):
        _check_learn_status_and_prompt(
            ctx,
            repo_root=state.main_repo_root,
            plan_id=plan_id,
            force=state.force,
            script=state.script,
        )

    return dataclasses.replace(state, plan_id=plan_id)


def gather_confirmations(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Gather cleanup confirmation upfront during validation.

    Populates: cleanup_confirmed.
    """
    from erk.cli.commands.land_cmd import LandTarget, _gather_cleanup_confirmation

    # Force and dry-run skip confirmation entirely (no repo discovery needed)
    if state.force or ctx.dry_run:
        return dataclasses.replace(state, cleanup_confirmed=True)

    # pr_details guaranteed non-None after resolve_target + validate_pr
    assert state.pr_details is not None

    target = LandTarget(
        branch=state.branch,
        pr_details=state.pr_details,
        worktree_path=state.worktree_path,
        is_current_branch=state.is_current_branch,
        use_graphite=state.use_graphite,
        target_child_branch=state.target_child_branch,
    )

    repo = discover_repo_context(ctx, state.cwd)
    confirmation = _gather_cleanup_confirmation(ctx, target=target, repo=repo, force=state.force)

    return dataclasses.replace(state, cleanup_confirmed=confirmation.proceed)


def resolve_objective(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Look up objective for branch.

    Populates: objective_number.
    """
    objective_number = get_objective_for_branch(ctx, state.main_repo_root, state.branch)
    return dataclasses.replace(state, objective_number=objective_number)


# ---------------------------------------------------------------------------
# Execution Pipeline Steps
# ---------------------------------------------------------------------------


def merge_pr(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Merge the PR via Graphite or GitHub API.

    Populates: merged_pr_number.
    """
    if state.use_graphite and state.worktree_path is not None:
        result = render_events(execute_land_pr(ctx, state.worktree_path))
        if isinstance(result, LandPrError):
            return LandError(
                phase="merge_pr",
                error_type="graphite_merge_failed",
                message=result.message,
                details={"branch": state.branch},
            )
        merged_pr_number = result.pr_number
    else:
        pr_details = EnsureIdeal.unwrap_pr(
            ctx.github.get_pr(state.main_repo_root, state.pr_number),
            f"Pull request #{state.pr_number} not found.",
        )
        user_output(f"Merging PR #{state.pr_number}...")
        subject = f"{pr_details.title} (#{state.pr_number})" if pr_details.title else None
        body = pr_details.body or None
        merge_result = ctx.github.merge_pr(
            state.main_repo_root,
            state.pr_number,
            squash=True,
            verbose=False,
            subject=subject,
            body=body,
        )
        if isinstance(merge_result, MergeError):
            return LandError(
                phase="merge_pr",
                error_type="github_merge_failed",
                message=f"Failed to merge PR #{state.pr_number}\n\n{merge_result.message}",
                details={"pr_number": str(state.pr_number)},
            )
        merged_pr_number = state.pr_number

    user_output(click.style("✓", fg="green") + f" Merged PR #{merged_pr_number} [{state.branch}]")
    return dataclasses.replace(state, merged_pr_number=merged_pr_number)


def update_objective(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Update objective if linked."""
    if state.objective_number is not None and state.merged_pr_number is not None:
        prompt_objective_update(
            ctx,
            repo_root=state.main_repo_root,
            objective_number=state.objective_number,
            pr_number=state.merged_pr_number,
            branch=state.branch,
            force=True,
        )
    return state


def update_learn_plan(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Update parent plan learn_status if this is a learn plan."""
    if state.plan_id is None or state.merged_pr_number is None:
        return state

    learned_from = ctx.plan_backend.get_metadata_field(
        state.main_repo_root, state.plan_id, "learned_from_issue"
    )
    if isinstance(learned_from, PlanNotFound) or learned_from is None:
        return state

    try:
        ctx.plan_backend.update_metadata(
            state.main_repo_root,
            str(learned_from),
            {"learn_status": "plan_completed", "learn_plan_pr": state.merged_pr_number},
        )
        user_output(f"Updated learn status on parent plan #{learned_from}")
    except (RuntimeError, PlanHeaderNotFoundError):
        user_output(f"Warning: Could not update learn status on parent plan #{learned_from}")

    return state


def close_review_pr(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Close review PR if plan has one."""
    if state.plan_id is None:
        return state

    cleanup_review_pr(
        ctx,
        repo_root=state.main_repo_root,
        issue_number=int(state.plan_id),
        reason=f"the plan (issue #{state.plan_id}) was implemented and landed",
    )
    return state


def cleanup_and_navigate(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Dispatch cleanup by type, navigate. Terminal step (may SystemExit)."""
    from erk.cli.commands.land_cmd import _cleanup_and_navigate

    repo = discover_repo_context(ctx, state.cwd)
    _cleanup_and_navigate(
        ctx,
        repo=repo,
        branch=state.branch,
        worktree_path=state.worktree_path,
        script=state.script,
        pull_flag=state.pull_flag,
        force=True,
        is_current_branch=state.is_current_branch,
        target_child_branch=state.target_child_branch,
        objective_number=state.objective_number,
        no_delete=state.no_delete,
        skip_activation_output=True,
        cleanup_confirmed=state.cleanup_confirmed,
    )
    return state


# ---------------------------------------------------------------------------
# Pipeline Definitions
# ---------------------------------------------------------------------------


@cache
def _validation_pipeline() -> tuple[LandStep, ...]:
    return (
        resolve_target,
        validate_pr,
        check_learn_status,
        gather_confirmations,
        resolve_objective,
    )


@cache
def _execution_pipeline() -> tuple[LandStep, ...]:
    return (
        merge_pr,
        update_objective,
        update_learn_plan,
        close_review_pr,
        cleanup_and_navigate,
    )


# ---------------------------------------------------------------------------
# Pipeline Runners
# ---------------------------------------------------------------------------


def run_validation_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run the validation pipeline, returning final state or first error."""
    for step in _validation_pipeline():
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result
        state = result
    return state


def run_execution_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run the execution pipeline, returning final state or first error."""
    for step in _execution_pipeline():
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result
        state = result
    return state


# ---------------------------------------------------------------------------
# State Factories
# ---------------------------------------------------------------------------


def make_initial_state(
    *,
    cwd: Path,
    force: bool,
    script: bool,
    pull_flag: bool,
    no_delete: bool,
    up_flag: bool,
    dry_run: bool,
    target_arg: str | None,
    repo_root: Path,
    main_repo_root: Path,
) -> LandState:
    """Create initial LandState with CLI-provided values and pre-discovered repo paths.

    repo_root and main_repo_root are discovered by the CLI handler before pipeline entry.
    Other discovery fields start as empty/defaults and are populated by resolve_target().
    """
    return LandState(
        cwd=cwd,
        force=force,
        script=script,
        pull_flag=pull_flag,
        no_delete=no_delete,
        up_flag=up_flag,
        dry_run=dry_run,
        target_arg=target_arg,
        # Pre-discovered repo paths
        repo_root=repo_root,
        main_repo_root=main_repo_root,
        branch="",
        pr_number=0,
        pr_details=None,
        worktree_path=None,
        is_current_branch=False,
        use_graphite=False,
        target_child_branch=None,
        # Derived (populated by later steps)
        objective_number=None,
        plan_id=None,
        cleanup_confirmed=False,
        merged_pr_number=None,
    )


def make_execution_state(
    *,
    cwd: Path,
    pr_number: int,
    branch: str,
    worktree_path: Path | None,
    is_current_branch: bool,
    objective_number: int | None,
    use_graphite: bool,
    pull_flag: bool,
    no_delete: bool,
    no_cleanup: bool,
    script: bool,
    target_child_branch: str | None,
) -> LandState:
    """Create LandState for the execution pipeline from exec script args.

    Re-derives repo_root, main_repo_root, plan_id from the args
    passed through the shell script serialization boundary.
    """
    from erk_shared.naming import extract_leading_issue_number

    issue_number = extract_leading_issue_number(branch)
    plan_id = str(issue_number) if issue_number is not None else None

    return LandState(
        cwd=cwd,
        force=True,  # Execute mode always skips confirmations
        script=script,
        pull_flag=pull_flag,
        no_delete=no_delete,
        up_flag=False,  # --up resolved by exec script before calling
        dry_run=False,  # Execute mode never dry-runs
        target_arg=None,
        # Pre-resolved from exec script args
        repo_root=cwd,
        main_repo_root=cwd,  # Re-derived in merge_pr via discover_repo_context
        branch=branch,
        pr_number=pr_number,
        pr_details=None,  # Re-fetched by merge_pr if needed
        worktree_path=worktree_path,
        is_current_branch=is_current_branch,
        use_graphite=use_graphite,
        target_child_branch=target_child_branch,
        # Derived
        objective_number=objective_number,
        plan_id=plan_id,
        cleanup_confirmed=not no_cleanup,
        merged_pr_number=None,
    )
