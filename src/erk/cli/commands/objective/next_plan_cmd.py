"""Launch Claude to create a plan from an objective step."""

from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.exec.scripts.update_roadmap_step import (
    _replace_step_refs_in_body,
    _replace_table_in_text,
)
from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.objective.check_cmd import (
    ObjectiveValidationError,
    ObjectiveValidationSuccess,
    validate_objective,
)
from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.context.types import InteractiveAgentConfig
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import extract_metadata_value
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    RoadmapStep,
)
from erk_shared.gateway.github.types import BodyText
from erk_shared.output.output import user_output


def _find_step_by_id(
    phases: list[RoadmapPhase], step_id: str
) -> tuple[RoadmapStep, RoadmapPhase] | None:
    """Find a step by its ID across all phases.

    Args:
        phases: List of roadmap phases to search
        step_id: Step ID to find (e.g., "1.1", "2.3")

    Returns:
        Tuple of (step, phase) if found, None otherwise
    """
    for phase in phases:
        for step in phase.steps:
            if step.id == step_id:
                return step, phase
    return None


def _update_objective_step(
    issues: GitHubIssues,
    repo_root: Path,
    *,
    issue_number: int,
    step_id: str,
    pr_number: int,
) -> None:
    """Mark a step as 'planning' with the draft PR in the objective roadmap.

    Fetches the current issue body, updates the step's status to 'planning'
    and sets the PR column to the draft PR number, then writes back.

    Args:
        issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Objective issue number
        step_id: Step ID to update (e.g., "1.1")
        pr_number: Draft PR number from one-shot dispatch
    """
    issue = issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return

    updated_body = _replace_step_refs_in_body(
        issue.body,
        step_id,
        new_plan=None,
        new_pr=f"#{pr_number}",
        explicit_status="planning",
    )

    if updated_body is None:
        return

    issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # v2 format: also update the markdown table in the objective-body comment
    objective_comment_id = extract_metadata_value(
        updated_body, "objective-header", "objective_comment_id"
    )
    if objective_comment_id is not None:
        comment_body = issues.get_comment_by_id(repo_root, objective_comment_id)
        updated_comment = _replace_table_in_text(
            comment_body,
            step_id,
            new_plan=None,
            new_pr=f"#{pr_number}",
            explicit_status="planning",
        )
        if updated_comment is not None and updated_comment != comment_body:
            issues.update_comment(repo_root, objective_comment_id, updated_comment)


@alias("np")
@click.command("next-plan")
@click.argument("issue_ref")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    default=False,
    help="Allow dangerous permissions by passing --allow-dangerously-skip-permissions to Claude",
)
@click.option(
    "--one-shot",
    "one_shot_mode",
    is_flag=True,
    default=False,
    help="Dispatch via one-shot workflow for fully autonomous execution",
)
@click.option(
    "-m",
    "--model",
    type=str,
    default=None,
    help="Model to use for one-shot execution (requires --one-shot)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would happen without executing (requires --one-shot)",
)
@click.option(
    "--step",
    "step_id",
    type=str,
    default=None,
    help="Specific step ID to dispatch (requires --one-shot)",
)
@click.pass_obj
def next_plan(
    ctx: ErkContext,
    issue_ref: str,
    dangerous: bool,
    one_shot_mode: bool,
    model: str | None,
    dry_run: bool,
    step_id: str | None,
) -> None:
    """Create an implementation plan from an objective step.

    ISSUE_REF is an objective issue number or GitHub URL.

    By default, launches Claude interactively in plan mode.

    With --one-shot, dispatches via the one-shot CI workflow for
    fully autonomous planning and implementation.

    \b
    Examples:
      erk objective next-plan 42
      erk objective next-plan 42 --one-shot
      erk objective next-plan 42 --one-shot --step 1.2
      erk objective next-plan 42 --one-shot --dry-run
    """
    # Validate flag dependencies: --model, --dry-run, --step require --one-shot
    if not one_shot_mode:
        if model is not None:
            raise click.ClickException("--model requires --one-shot")
        if dry_run:
            raise click.ClickException("--dry-run requires --one-shot")
        if step_id is not None:
            raise click.ClickException("--step requires --one-shot")

    if one_shot_mode:
        _handle_one_shot(ctx, issue_ref=issue_ref, model=model, dry_run=dry_run, step_id=step_id)
    else:
        _handle_interactive(ctx, issue_ref=issue_ref, dangerous=dangerous)


def _handle_interactive(ctx: ErkContext, *, issue_ref: str, dangerous: bool) -> None:
    """Launch Claude interactively to create a plan."""
    # Build command with argument
    command = f"/erk:objective-next-plan {issue_ref}"

    # Get interactive Claude config with plan mode override
    if ctx.global_config is None:
        ia_config = InteractiveAgentConfig.default()
    else:
        ia_config = ctx.global_config.interactive_agent
    if dangerous:
        allow_dangerous_override = True
    else:
        allow_dangerous_override = None

    config = ia_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=allow_dangerous_override,
    )

    # Replace current process with Claude
    try:
        ctx.agent_launcher.launch_interactive(config, command=command)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e


def _handle_one_shot(
    ctx: ErkContext,
    *,
    issue_ref: str,
    model: str | None,
    dry_run: bool,
    step_id: str | None,
) -> None:
    """Dispatch objective step via one-shot workflow."""
    # Parse issue identifier
    issue_number = parse_issue_identifier(issue_ref)

    # Validate repo context
    if isinstance(ctx.repo, NoRepoSentinel):
        raise click.ClickException("Not in a git repository")
    assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
    repo: RepoContext = ctx.repo

    # Validate objective
    result = validate_objective(ctx.issues, repo.root, issue_number)

    if isinstance(result, ObjectiveValidationError):
        raise click.ClickException(result.error)

    assert isinstance(result, ObjectiveValidationSuccess)

    if not result.phases:
        raise click.ClickException(f"Objective #{issue_number} has no roadmap phases")

    # Determine target step
    if step_id is not None:
        found = _find_step_by_id(result.phases, step_id)
        if found is None:
            raise click.ClickException(f"Step '{step_id}' not found in objective #{issue_number}")
        target_step, target_phase = found
    else:
        if result.next_step is None:
            user_output(
                click.style("All steps completed!", fg="green")
                + f" Objective #{issue_number} has no pending steps."
            )
            return
        # Find the actual step and phase objects from next_step dict
        found = _find_step_by_id(result.phases, result.next_step["id"])
        if found is None:
            raise click.ClickException(
                f"Internal error: next_step '{result.next_step['id']}' not found"
            )
        target_step, target_phase = found

    # Normalize model name
    model = normalize_model_name(model)

    # Build instruction
    instruction = (
        f"Implement step {target_step.id} of objective #{issue_number}: "
        f"{target_step.description} (Phase: {target_phase.name})"
    )

    user_output(
        f"Dispatching step {click.style(target_step.id, bold=True)}: {target_step.description}"
    )
    user_output(f"Phase: {target_phase.name}")
    user_output(f"Instruction: {instruction}")

    params = OneShotDispatchParams(
        instruction=instruction,
        model=model,
        extra_workflow_inputs={
            "objective_issue": str(issue_number),
            "step_id": target_step.id,
        },
    )

    dispatch_result = dispatch_one_shot(ctx, params=params, dry_run=dry_run)

    # After successful dispatch, immediately mark step as "planning" with draft PR
    if dispatch_result is not None:
        _update_objective_step(
            ctx.issues,
            repo.root,
            issue_number=issue_number,
            step_id=target_step.id,
            pr_number=dispatch_result.pr_number,
        )
