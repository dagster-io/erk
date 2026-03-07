"""Create a plan from an objective node."""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.update_objective_node import (
    _replace_node_refs_in_body,
)
from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.objective.check_cmd import (
    ObjectiveValidationError,
    ObjectiveValidationSuccess,
    validate_objective,
)
from erk.cli.commands.objective_helpers import get_objective_for_branch
from erk.cli.commands.one_shot import _get_remote_github
from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot_remote,
)
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.branch_slug_generator import generate_branch_slug
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.context.types import InteractiveAgentConfig
from erk_shared.core.prompt_executor import PromptExecutor
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
    rerender_comment_roadmap,
)
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.types import BodyText
from erk_shared.naming import sanitize_worktree_name
from erk_shared.output.output import user_output


def _generate_slug(prompt_executor: PromptExecutor, description: str) -> str:
    """Generate a branch slug from a description, falling back to sanitization.

    Uses the prompt executor to generate a concise slug. On failure,
    falls back to sanitizing the description directly.

    Args:
        prompt_executor: PromptExecutor for slug generation
        description: Text to generate a slug from

    Returns:
        A slug string suitable for branch names
    """
    slug = generate_branch_slug(prompt_executor, description)
    if slug == description:
        return sanitize_worktree_name(description)[:25].rstrip("-")
    return slug


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
    dispatch_ref: str | None,
    ref_current: bool,
) -> None:
    """Dispatch one-shot workflows for all unblocked pending nodes."""
    resolved = _resolve_all_unblocked(ctx, issue_ref=issue_ref)

    # Validate repo context for owner/repo
    if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
        raise click.ClickException(
            "Cannot determine target repository.\n"
            "Run from inside a git repository with a GitHub remote."
        )
    owner, repo_name = ctx.repo.github.owner, ctx.repo.github.repo

    # Normalize model name
    model = normalize_model_name(model)

    user_output(
        f"Found {click.style(len(resolved.nodes), bold=True)} "
        f"unblocked pending node(s) in objective #{resolved.issue_number}:"
    )
    for node, phase_name in resolved.nodes:
        user_output(f"  {node.id}: {node.description} (Phase: {phase_name})")
    user_output("")

    dispatched_count = 0
    successful_dispatches: list[tuple[str, int]] = []

    ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
    remote = _get_remote_github(ctx)

    for node, phase_name in resolved.nodes:
        prompt = (
            f"/erk:objective-plan {resolved.issue_number}\n"
            f"Implement step {node.id} of objective #{resolved.issue_number}: "
            f"{node.description} (Phase: {phase_name})"
        )

        user_output(f"Dispatching node {click.style(node.id, bold=True)}: {node.description}")

        slug = _generate_slug(ctx.prompt_executor, node.description)

        params = OneShotDispatchParams(
            prompt=prompt,
            model=model,
            extra_workflow_inputs={
                "objective_issue": str(resolved.issue_number),
                "node_id": node.id,
            },
            slug=slug,
        )

        dispatch_result = dispatch_one_shot_remote(
            remote=remote,
            owner=owner,
            repo=repo_name,
            params=params,
            dry_run=dry_run,
            ref=ref,
            time_gateway=ctx.time,
            prompt_executor=ctx.prompt_executor,
        )

        if dispatch_result is not None:
            successful_dispatches.append((node.id, dispatch_result.pr_number))
            dispatched_count += 1

    # Single atomic update after all dispatches complete
    if successful_dispatches:
        assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
        user_output("Updating objective roadmap...")
        _batch_update_objective_nodes(
            ctx.issues,
            ctx.repo.root,
            issue_number=resolved.issue_number,
            node_updates=successful_dispatches,
        )

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
        new_pr=f"#{pr_number}",
        explicit_status="planning",
        description=None,
        slug=None,
        reason=None,
    )

    if updated_body is None:
        return

    issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # v2 format: re-render the comment table from updated YAML
    objective_comment_id = extract_metadata_value(
        updated_body, BlockKeys.OBJECTIVE_HEADER, "objective_comment_id"
    )
    if objective_comment_id is not None:
        comment_body = issues.get_comment_by_id(repo_root, objective_comment_id)
        updated_comment = rerender_comment_roadmap(updated_body, comment_body)
        if updated_comment is not None and updated_comment != comment_body:
            issues.update_comment(repo_root, objective_comment_id, updated_comment)


def _batch_update_objective_nodes(
    issues: GitHubIssues,
    repo_root: Path,
    *,
    issue_number: int,
    node_updates: list[tuple[str, int]],
) -> None:
    """Mark multiple nodes as 'planning' with draft PRs in a single API write.

    Fetches the issue body once, applies all node updates in memory, then writes
    back once. Same for the v2 comment if present.

    Args:
        issues: GitHub issues gateway
        repo_root: Repository root path
        issue_number: Objective issue number
        node_updates: List of (node_id, pr_number) pairs to update
    """
    if not node_updates:
        return

    issue = issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return

    # Accumulate all body changes in memory
    updated_body = issue.body
    body_changed = False
    for node_id, pr_number in node_updates:
        new_body = _replace_node_refs_in_body(
            updated_body,
            node_id,
            new_pr=f"#{pr_number}",
            explicit_status="planning",
            description=None,
            slug=None,
            reason=None,
        )
        if new_body is not None:
            updated_body = new_body
            body_changed = True

    # Single write for all body changes
    if body_changed:
        issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # v2 format: re-render comment table from updated YAML (single write)
    objective_comment_id = extract_metadata_value(
        updated_body, BlockKeys.OBJECTIVE_HEADER, "objective_comment_id"
    )
    if objective_comment_id is not None:
        comment_body = issues.get_comment_by_id(repo_root, objective_comment_id)
        updated_comment = rerender_comment_roadmap(updated_body, comment_body)
        if updated_comment is not None and updated_comment != comment_body:
            issues.update_comment(repo_root, objective_comment_id, updated_comment)


def _mark_node_planning(
    issues: GitHubIssues,
    repo_root: Path,
    *,
    issue_number: int,
    node_id: str,
) -> None:
    """Best-effort mark a node as 'planning' in the objective roadmap.

    Unlike _update_objective_node, this does a status-only update without
    requiring a PR number. Used by the interactive flow to mark nodes
    before launching Claude, so parallel sessions skip them.

    Silently catches all errors — the inner skill will retry if needed.
    """
    issue = issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return

    updated_body = _replace_node_refs_in_body(
        issue.body,
        node_id,
        new_pr=None,
        explicit_status="planning",
        description=None,
        slug=None,
        reason=None,
    )

    if updated_body is None:
        return

    issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))

    # v2 format: re-render the comment table from updated YAML
    objective_comment_id = extract_metadata_value(
        updated_body, BlockKeys.OBJECTIVE_HEADER, "objective_comment_id"
    )
    if objective_comment_id is not None:
        comment_body = issues.get_comment_by_id(repo_root, objective_comment_id)
        updated_comment = rerender_comment_roadmap(updated_body, comment_body)
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
@click.option(
    "--ref",
    "dispatch_ref",
    type=str,
    default=None,
    help="Branch to dispatch workflow from (overrides config dispatch_ref)",
)
@click.option(
    "--ref-current",
    is_flag=True,
    default=False,
    help="Dispatch workflow from the current branch",
)
@click.pass_obj
def plan_objective(
    ctx: ErkContext,
    *,
    issue_ref: str | None,
    dangerous: bool,
    one_shot_mode: bool,
    model: str | None,
    dry_run: bool,
    node_id: str | None,
    use_next: bool,
    all_unblocked: bool,
    dispatch_ref: str | None,
    ref_current: bool,
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
            dispatch_ref=dispatch_ref,
            ref_current=ref_current,
        )
    elif one_shot_mode:
        _handle_one_shot(
            ctx,
            issue_ref=issue_ref,
            model=model,
            dry_run=dry_run,
            node_id=node_id,
            use_next=use_next,
            dispatch_ref=dispatch_ref,
            ref_current=ref_current,
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
    # Determine if we have a known node (from --next or --node)
    known_issue_number: int | None = None
    known_node_id: str | None = None

    if use_next:
        resolved = _resolve_next(ctx, issue_ref=issue_ref)
        user_output(f"Next node: {resolved.node.id}: {resolved.node.description}")
        known_issue_number = resolved.issue_number
        known_node_id = resolved.node.id
    elif node_id is not None:
        assert issue_ref is not None  # type narrowing: validated in plan_objective
        known_issue_number = parse_issue_identifier(issue_ref)
        known_node_id = node_id

    if known_issue_number is not None and known_node_id is not None:
        # Known node: pre-mark as planning in Python, then launch inner command
        assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
        _mark_node_planning(
            ctx.issues,
            ctx.repo.root,
            issue_number=known_issue_number,
            node_id=known_node_id,
        )
        command = f"/erk:system:objective-plan-node {known_issue_number} --node {known_node_id}"
    else:
        # No known node: launch outer command for interactive selection
        assert issue_ref is not None  # type narrowing: validated in plan_objective
        command = f"/erk:objective-plan {issue_ref}"

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
    dispatch_ref: str | None,
    ref_current: bool,
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

    # Validate repo context for owner/repo
    if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
        raise click.ClickException(
            "Cannot determine target repository.\n"
            "Run from inside a git repository with a GitHub remote."
        )
    owner, repo_name = ctx.repo.github.owner, ctx.repo.github.repo

    # Normalize model name
    model = normalize_model_name(model)

    # Resolve dispatch ref
    ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)

    # Build prompt
    prompt = (
        f"/erk:objective-plan {issue_number}\n"
        f"Implement step {target_node.id} of objective #{issue_number}: "
        f"{target_node.description} (Phase: {phase_name})"
    )

    user_output(
        f"Dispatching node {click.style(target_node.id, bold=True)}: {target_node.description}"
    )
    user_output(f"Phase: {phase_name}")
    user_output(f"Prompt: {prompt}")

    slug = _generate_slug(ctx.prompt_executor, target_node.description)

    params = OneShotDispatchParams(
        prompt=prompt,
        model=model,
        extra_workflow_inputs={
            "objective_issue": str(issue_number),
            "node_id": target_node.id,
        },
        slug=slug,
    )

    remote = _get_remote_github(ctx)

    dispatch_result = dispatch_one_shot_remote(
        remote=remote,
        owner=owner,
        repo=repo_name,
        params=params,
        dry_run=dry_run,
        ref=ref,
        time_gateway=ctx.time,
        prompt_executor=ctx.prompt_executor,
    )

    # After successful dispatch, immediately mark node as "planning" with draft PR
    if dispatch_result is not None:
        # repo is guaranteed to be RepoContext here (validated above)
        assert not isinstance(ctx.repo, NoRepoSentinel)  # type narrowing
        user_output("Updating objective roadmap...")
        _update_objective_node(
            ctx.issues,
            ctx.repo.root,
            issue_number=issue_number,
            node_id=target_node.id,
            pr_number=dispatch_result.pr_number,
        )
