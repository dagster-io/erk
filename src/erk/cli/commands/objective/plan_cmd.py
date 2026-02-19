"""Create a plan from an objective node."""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.update_objective_node import (
    _replace_node_refs_in_body,
    _replace_table_in_text,
)
from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.objective.check_cmd import (
    ObjectiveValidationError,
    ObjectiveValidationSuccess,
    validate_objective,
)
from erk.cli.commands.objective_helpers import get_objective_for_branch
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
from erk_shared.gateway.github.metadata.dependency_graph import (
    ObjectiveNode,
    build_graph,
    phases_from_graph,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    enrich_phase_names,
)
from erk_shared.gateway.github.types import BodyText
from erk_shared.output.output import user_output


def _find_node_in_phases(
    phases: list[RoadmapPhase], node_id: str
) -> tuple[ObjectiveNode, str] | None:
    """Find a node by ID and return it with its phase name.

    Args:
        phases: List of roadmap phases to search
        node_id: Node ID to find (e.g., "1.1", "2.3")

    Returns:
        Tuple of (ObjectiveNode, phase_name) if found, None otherwise
    """
    graph = build_graph(phases)
    node_by_id = {node.id: node for node in graph.nodes}
    node = node_by_id.get(node_id)
    if node is None:
        return None
    for phase in phases:
        if any(n.id == node_id for n in phase.nodes):
            return node, phase.name
    return None


@dataclass(frozen=True)
class ResolvedNext:
    """Result of resolving the next unblocked pending node for an objective.

    Attributes:
        issue_number: The objective issue number
        node: The next unblocked pending node
        phase_name: The phase containing the node
    """

    issue_number: int
    node: ObjectiveNode
    phase_name: str


def _resolve_next(
    ctx: ErkContext,
    *,
    issue_ref: str | None,
) -> ResolvedNext:
    """Resolve the next unblocked pending node for an objective.

    If issue_ref is provided, uses it directly. Otherwise infers the objective
    from the current branch via plan store metadata.

    Args:
        ctx: ErkContext with git, issues, and plan_store
        issue_ref: Optional issue reference (number or URL)

    Raises:
        click.ClickException: If objective cannot be resolved or has no pending nodes
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        raise click.ClickException("Not in a git repository")
    assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
    repo: RepoContext = ctx.repo

    if issue_ref is not None:
        issue_number = parse_issue_identifier(issue_ref)
    else:
        branch = ctx.git.branch.get_current_branch(repo.root)
        if branch is None:
            raise click.ClickException("Not on a branch")
        objective_id = get_objective_for_branch(ctx, repo.root, branch)
        if objective_id is None:
            raise click.ClickException(
                f"Branch '{branch}' is not linked to an objective. Provide ISSUE_REF explicitly."
            )
        issue_number = objective_id

    result = validate_objective(ctx.issues, repo.root, issue_number)
    if isinstance(result, ObjectiveValidationError):
        raise click.ClickException(result.error)
    assert isinstance(result, ObjectiveValidationSuccess)  # type narrowing

    if not result.graph.nodes:
        raise click.ClickException(f"Objective #{issue_number} has no roadmap phases")

    next_node = result.graph.next_node()
    if next_node is None:
        raise click.ClickException(f"Objective #{issue_number} has no pending unblocked nodes")

    phases = phases_from_graph(result.graph)
    phases = enrich_phase_names(result.issue_body, phases)
    found = _find_node_in_phases(phases, next_node.id)
    if found is None:
        raise click.ClickException(
            f"Internal error: next node '{next_node.id}' not found in phases"
        )

    return ResolvedNext(
        issue_number=issue_number,
        node=found[0],
        phase_name=found[1],
    )


@dataclass(frozen=True)
class ResolvedAllUnblocked:
    """Result of resolving all unblocked pending nodes for an objective.

    Attributes:
        issue_number: The objective issue number
        nodes: List of (node, phase_name) pairs for each pending unblocked node
    """

    issue_number: int
    nodes: list[tuple[ObjectiveNode, str]]


def _resolve_all_unblocked(
    ctx: ErkContext,
    *,
    issue_ref: str | None,
) -> ResolvedAllUnblocked:
    """Resolve all unblocked pending nodes for an objective.

    If issue_ref is provided, uses it directly. Otherwise infers the objective
    from the current branch via plan store metadata.

    Args:
        ctx: ErkContext with git, issues, and plan_store
        issue_ref: Optional issue reference (number or URL)

    Raises:
        click.ClickException: If objective cannot be resolved or has no pending unblocked nodes
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        raise click.ClickException("Not in a git repository")
    assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
    repo: RepoContext = ctx.repo

    if issue_ref is not None:
        issue_number = parse_issue_identifier(issue_ref)
    else:
        branch = ctx.git.branch.get_current_branch(repo.root)
        if branch is None:
            raise click.ClickException("Not on a branch")
        objective_id = get_objective_for_branch(ctx, repo.root, branch)
        if objective_id is None:
            raise click.ClickException(
                f"Branch '{branch}' is not linked to an objective. Provide ISSUE_REF explicitly."
            )
        issue_number = objective_id

    result = validate_objective(ctx.issues, repo.root, issue_number)
    if isinstance(result, ObjectiveValidationError):
        raise click.ClickException(result.error)
    assert isinstance(result, ObjectiveValidationSuccess)  # type narrowing

    if not result.graph.nodes:
        raise click.ClickException(f"Objective #{issue_number} has no roadmap phases")

    pending_nodes = result.graph.pending_unblocked_nodes()
    if not pending_nodes:
        raise click.ClickException(f"Objective #{issue_number} has no pending unblocked nodes")

    phases = phases_from_graph(result.graph)
    phases = enrich_phase_names(result.issue_body, phases)

    node_phase_pairs: list[tuple[ObjectiveNode, str]] = []
    for node in pending_nodes:
        found = _find_node_in_phases(phases, node.id)
        if found is None:
            raise click.ClickException(f"Internal error: node '{node.id}' not found in phases")
        node_phase_pairs.append(found)

    return ResolvedAllUnblocked(
        issue_number=issue_number,
        nodes=node_phase_pairs,
    )


def _handle_all_unblocked(
    ctx: ErkContext,
    *,
    issue_ref: str | None,
    model: str | None,
    dry_run: bool,
) -> None:
    """Dispatch one-shot workflows for all unblocked pending nodes."""
    resolved = _resolve_all_unblocked(ctx, issue_ref=issue_ref)

    # Normalize model name
    model = normalize_model_name(model)

    user_output(
        f"Found {click.style(str(len(resolved.nodes)), bold=True)} "
        f"unblocked pending node(s) in objective #{resolved.issue_number}:"
    )
    for node, phase_name in resolved.nodes:
        user_output(f"  {node.id}: {node.description} (Phase: {phase_name})")
    user_output("")

    dispatched_count = 0
    for node, phase_name in resolved.nodes:
        instruction = (
            f"/erk:objective-plan {resolved.issue_number}\n"
            f"Implement step {node.id} of objective #{resolved.issue_number}: "
            f"{node.description} (Phase: {phase_name})"
        )

        user_output(f"Dispatching node {click.style(node.id, bold=True)}: {node.description}")

        params = OneShotDispatchParams(
            instruction=instruction,
            model=model,
            extra_workflow_inputs={
                "objective_issue": str(resolved.issue_number),
                "node_id": node.id,
            },
        )

        dispatch_result = dispatch_one_shot(ctx, params=params, dry_run=dry_run)

        if dispatch_result is not None:
            assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
            _update_objective_node(
                ctx.issues,
                ctx.repo.root,
                issue_number=resolved.issue_number,
                node_id=node.id,
                pr_number=dispatch_result.pr_number,
            )
            dispatched_count += 1

    if dry_run:
        user_output(
            f"\n{click.style('Dry-run complete:', fg='cyan', bold=True)} "
            f"Would dispatch {len(resolved.nodes)} node(s)"
        )
    else:
        user_output(
            f"\n{click.style('Done!', fg='green', bold=True)} "
            f"Dispatched {dispatched_count}/{len(resolved.nodes)} node(s)"
        )


def _update_objective_node(
    issues: GitHubIssues,
    repo_root: Path,
    *,
    issue_number: int,
    node_id: str,
    pr_number: int,
) -> None:
    """Mark a node as 'planning' with the draft PR in the objective roadmap.

    Fetches the current issue body, updates the node's status to 'planning'
    and sets the PR column to the draft PR number, then writes back.

    Args:
        issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Objective issue number
        node_id: Node ID to update (e.g., "1.1")
        pr_number: Draft PR number from one-shot dispatch
    """
    issue = issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return

    updated_body = _replace_node_refs_in_body(
        issue.body,
        node_id,
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
            node_id,
            new_plan=None,
            new_pr=f"#{pr_number}",
            explicit_status="planning",
        )
        if updated_comment is not None and updated_comment != comment_body:
            issues.update_comment(repo_root, objective_comment_id, updated_comment)


@click.command("plan")
@click.argument("issue_ref", required=False, default=None)
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
    "--node",
    "node_id",
    type=str,
    default=None,
    help="Specific node ID to implement (e.g., --node 2.1)",
)
@click.option(
    "--next",
    "use_next",
    is_flag=True,
    default=False,
    help="Auto-select next unblocked pending node (infers objective from branch if omitted)",
)
@click.option(
    "--all-unblocked",
    "all_unblocked",
    is_flag=True,
    default=False,
    help="Dispatch all unblocked pending nodes via one-shot (one workflow per node)",
)
@click.pass_obj
def plan_objective(
    ctx: ErkContext,
    issue_ref: str | None,
    dangerous: bool,
    one_shot_mode: bool,
    model: str | None,
    dry_run: bool,
    node_id: str | None,
    use_next: bool,
    all_unblocked: bool,
) -> None:
    """Create a plan from an objective node.

    ISSUE_REF is an objective issue number or GitHub URL.

    By default, launches Claude interactively in plan mode to plan
    the next unblocked node.

    With --one-shot, dispatches via the one-shot CI workflow for
    fully autonomous planning and implementation.

    With --next, auto-selects the next unblocked pending node.
    If ISSUE_REF is omitted with --next, infers the objective from the current branch.

    With --all-unblocked, dispatches one-shot workflows for all unblocked
    pending nodes simultaneously.

    \b
    Examples:
      erk objective plan 42
      erk objective plan 42 --node 2.1
      erk objective plan 42 --one-shot
      erk objective plan 42 --one-shot --node 1.2
      erk objective plan 42 --one-shot --dry-run
      erk objective plan 42 --next
      erk objective plan --next
      erk objective plan --next --one-shot
      erk objective plan 42 --all-unblocked
      erk objective plan 42 --all-unblocked --dry-run
    """
    # Validate flag combinations
    if all_unblocked and node_id is not None:
        raise click.ClickException("--all-unblocked and --node are mutually exclusive")
    if all_unblocked and use_next:
        raise click.ClickException("--all-unblocked and --next are mutually exclusive")
    if use_next and node_id is not None:
        raise click.ClickException("--next and --node are mutually exclusive")

    if issue_ref is None and not use_next and not all_unblocked:
        raise click.ClickException("ISSUE_REF is required unless --next or --all-unblocked is used")

    # --all-unblocked implies --one-shot
    if all_unblocked:
        one_shot_mode = True

    # Validate flag dependencies: --model, --dry-run require --one-shot
    if not one_shot_mode:
        if model is not None:
            raise click.ClickException("--model requires --one-shot")
        if dry_run:
            raise click.ClickException("--dry-run requires --one-shot")

    if all_unblocked:
        _handle_all_unblocked(
            ctx,
            issue_ref=issue_ref,
            model=model,
            dry_run=dry_run,
        )
    elif one_shot_mode:
        _handle_one_shot(
            ctx,
            issue_ref=issue_ref,
            model=model,
            dry_run=dry_run,
            node_id=node_id,
            use_next=use_next,
        )
    else:
        _handle_interactive(
            ctx, issue_ref=issue_ref, dangerous=dangerous, node_id=node_id, use_next=use_next
        )


def _handle_interactive(
    ctx: ErkContext,
    *,
    issue_ref: str | None,
    dangerous: bool,
    node_id: str | None,
    use_next: bool,
) -> None:
    """Launch Claude interactively to create a plan."""
    if use_next:
        resolved = _resolve_next(ctx, issue_ref=issue_ref)
        user_output(f"Next node: {resolved.node.id}: {resolved.node.description}")
        command = f"/erk:objective-plan {resolved.issue_number} --node {resolved.node.id}"
    else:
        assert issue_ref is not None  # type narrowing: validated in plan_objective
        node_suffix = f" --node {node_id}" if node_id is not None else ""
        command = f"/erk:objective-plan {issue_ref}{node_suffix}"

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
    issue_ref: str | None,
    model: str | None,
    dry_run: bool,
    node_id: str | None,
    use_next: bool,
) -> None:
    """Dispatch objective node via one-shot workflow."""
    if use_next:
        resolved = _resolve_next(ctx, issue_ref=issue_ref)
        issue_number = resolved.issue_number
        target_node = resolved.node
        phase_name = resolved.phase_name
    else:
        assert issue_ref is not None  # type narrowing: validated in plan_objective
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

        if not result.graph.nodes:
            raise click.ClickException(f"Objective #{issue_number} has no roadmap phases")

        phases = phases_from_graph(result.graph)
        phases = enrich_phase_names(result.issue_body, phases)

        if node_id is not None:
            found = _find_node_in_phases(phases, node_id)
            if found is None:
                raise click.ClickException(
                    f"Node '{node_id}' not found in objective #{issue_number}"
                )
            target_node, phase_name = found
        else:
            # Use next_node from validation (finds first pending node by position)
            if result.next_node is None:
                user_output(
                    click.style("All nodes completed!", fg="green")
                    + f" Objective #{issue_number} has no pending nodes."
                )
                return
            found = _find_node_in_phases(phases, result.next_node["id"])
            if found is None:
                raise click.ClickException(
                    f"Internal error: next_node '{result.next_node['id']}' not found"
                )
            target_node, phase_name = found

    # Normalize model name
    model = normalize_model_name(model)

    # Build instruction
    instruction = (
        f"/erk:objective-plan {issue_number}\n"
        f"Implement step {target_node.id} of objective #{issue_number}: "
        f"{target_node.description} (Phase: {phase_name})"
    )

    user_output(
        f"Dispatching node {click.style(target_node.id, bold=True)}: {target_node.description}"
    )
    user_output(f"Phase: {phase_name}")
    user_output(f"Instruction: {instruction}")

    params = OneShotDispatchParams(
        instruction=instruction,
        model=model,
        extra_workflow_inputs={
            "objective_issue": str(issue_number),
            "node_id": target_node.id,
        },
    )

    dispatch_result = dispatch_one_shot(ctx, params=params, dry_run=dry_run)

    # After successful dispatch, immediately mark node as "planning" with draft PR
    if dispatch_result is not None:
        # repo is guaranteed to be RepoContext here:
        # - use_next path: _resolve_next validates repo
        # - non-use_next path: repo is assigned above
        assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
        _update_objective_node(
            ctx.issues,
            ctx.repo.root,
            issue_number=issue_number,
            node_id=target_node.id,
            pr_number=dispatch_result.pr_number,
        )
