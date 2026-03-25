"""Pure validation logic for objective check.

Contains validate_objective() and its helper functions, along with
the ObjectiveValidationSuccess and ObjectiveValidationError types.
"""

from dataclasses import dataclass

from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    find_metadata_block,
    has_metadata_block,
)
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    build_graph,
    compute_graph_summary,
    find_graph_next_node,
)
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_objective_issue,
)
from erk_shared.gateway.github.metadata.roadmap import parse_roadmap
from erk_shared.gateway.github.metadata.types import BlockKeys, MetadataBlock
from erk_shared.gateway.remote_github.abc import RemoteGitHub

ERK_OBJECTIVE_LABEL = "erk-objective"


@dataclass(frozen=True)
class ObjectiveValidationSuccess:
    """Validation completed (may have passed or failed checks).

    Attributes:
        passed: True if all validation checks passed
        checks: List of (passed, description) tuples for each check
        failed_count: Number of failed checks
        graph: Dependency graph of roadmap nodes (empty if parsing failed)
        summary: Step count summary (empty if no graph nodes)
        next_node: First pending step or None
        validation_errors: Parser-level warnings from roadmap parsing
        issue_body: Raw issue body text (for phase name enrichment)
    """

    passed: bool
    checks: list[tuple[bool, str]]
    failed_count: int
    graph: DependencyGraph
    summary: dict[str, int]
    next_node: dict[str, str] | None
    validation_errors: list[str]
    issue_body: str


@dataclass(frozen=True)
class ObjectiveValidationError:
    """Could not complete validation (issue not found, etc.)."""

    error: str


ObjectiveValidationResult = ObjectiveValidationSuccess | ObjectiveValidationError


def _check_roadmap_table_sync(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo: str,
    issue_body: str,
    header_block: MetadataBlock | None,
) -> tuple[bool, str] | None:
    """Check if roadmap table in comment matches YAML source of truth.

    Returns a (passed, description) check tuple, or None if the check
    should be skipped (no header block, no comment ID, or comment not found).
    """
    if header_block is None:
        return None

    comment_id = header_block.data.get("objective_comment_id")
    if comment_id is None:
        return None

    comment_body = remote.get_comment_by_id(owner=owner, repo=repo, comment_id=comment_id)
    if not comment_body:
        return None

    from erk_shared.gateway.github.metadata.roadmap import rerender_comment_roadmap

    rerendered = rerender_comment_roadmap(issue_body, comment_body)
    if rerendered is None:
        return None

    if rerendered == comment_body:
        return (True, "Roadmap table in sync with YAML")
    return (False, "Roadmap table out of sync with YAML source of truth")


def _check_pr_backlinks(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo: str,
    issue_number: int,
    graph: DependencyGraph,
) -> tuple[bool, str] | None:
    """Check that plan PRs have objective_issue backlinks to this objective.

    Returns a (passed, description) check tuple, or None if no PR references found.
    """
    pr_nodes = [node for node in graph.nodes if node.pr and node.pr.startswith("#")]
    if not pr_nodes:
        return None

    backlink_issues: list[str] = []
    for node in pr_nodes:
        assert node.pr is not None
        pr_number = int(node.pr.lstrip("#"))
        pr_issue = remote.get_issue(owner=owner, repo=repo, number=pr_number)
        if isinstance(pr_issue, IssueNotFound):
            continue

        objective_ref = extract_plan_header_objective_issue(pr_issue.body)
        if objective_ref is None:
            if has_metadata_block(pr_issue.body, BlockKeys.PLAN_HEADER):
                backlink_issues.append(
                    f"Step {node.id} PR {node.pr} missing objective_issue backlink"
                )
        elif objective_ref != issue_number:
            backlink_issues.append(
                f"Step {node.id} PR {node.pr} has mismatched objective_issue: {objective_ref}"
            )

    if not backlink_issues:
        return (True, "PR backlinks: all PR references have matching objective_issue backlinks")
    return (False, f"PR backlinks: {backlink_issues[0]}")


def validate_objective(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo: str,
    issue_number: int,
) -> ObjectiveValidationResult:
    """Validate an objective programmatically.

    Checks:
    1. Issue exists and has erk-objective label
    2. Roadmap parses successfully (v2 format required)
    3. Status/PR consistency (done steps should have PRs)
    4. No orphaned statuses (done without PR reference)
    5. Phase numbering is sequential
    6. v2 format integrity (objective-header has objective_comment_id)
    7. Plan/PR references use # prefix
    8. Roadmap table sync (rendered table matches YAML source)
    9. PR backlink consistency (plan PRs have objective_issue backlinks)

    This function does not produce output or raise SystemExit.

    Returns:
        ObjectiveValidationSuccess if validation completed
        ObjectiveValidationError if unable to complete validation
    """
    checks: list[tuple[bool, str]] = []

    # Fetch issue
    issue = remote.get_issue(owner=owner, repo=repo, number=issue_number)
    if isinstance(issue, IssueNotFound):
        return ObjectiveValidationError(error=f"Issue #{issue_number} not found")

    # Check 1: erk-objective label
    has_label = ERK_OBJECTIVE_LABEL in issue.labels
    if has_label:
        checks.append((True, "Issue has erk-objective label"))
    else:
        checks.append((False, "Issue has erk-objective label"))

    # Check 2: Roadmap
    phases, validation_errors = parse_roadmap(issue.body)
    has_roadmap = has_metadata_block(issue.body, BlockKeys.OBJECTIVE_ROADMAP)

    if not has_roadmap:
        checks.append((True, "Roadmap: none (objective has no roadmap)"))
        failed_count = sum(1 for passed, _ in checks if not passed)
        return ObjectiveValidationSuccess(
            passed=failed_count == 0,
            checks=checks,
            failed_count=failed_count,
            graph=DependencyGraph(nodes=()),
            summary={},
            next_node=None,
            validation_errors=[],
            issue_body=issue.body,
        )

    if phases:
        checks.append((True, "Roadmap parses successfully"))
    else:
        checks.append((False, f"Roadmap parses successfully ({'; '.join(validation_errors)})"))
        failed_count = sum(1 for passed, _ in checks if not passed)
        return ObjectiveValidationSuccess(
            passed=False,
            checks=checks,
            failed_count=failed_count,
            graph=DependencyGraph(nodes=()),
            summary={},
            next_node=None,
            validation_errors=validation_errors,
            issue_body=issue.body,
        )

    graph = build_graph(phases)

    # Check 3: Status/PR consistency
    consistency_issues: list[str] = []
    for node in graph.nodes:
        if (
            node.pr
            and node.pr.startswith("#")
            and node.status not in ("in_progress", "done", "planning", "skipped")
        ):
            consistency_issues.append(
                f"Step {node.id} has PR {node.pr} but status is '{node.status}' "
                f"(expected 'in_progress' or 'done')"
            )

    if not consistency_issues:
        checks.append((True, "Status/PR consistency"))
    else:
        checks.append((False, f"Status/PR consistency: {consistency_issues[0]}"))

    # Check 4: No orphaned done statuses
    orphaned: list[str] = []
    for node in graph.nodes:
        if node.status == "done" and node.pr is None:
            orphaned.append(f"Step {node.id}")

    if not orphaned:
        checks.append((True, "No orphaned done statuses (done steps have PR references)"))
    else:
        checks.append((False, f"Done step without PR reference: {', '.join(orphaned)}"))

    # Check 5: Phase numbering is sequential
    phase_keys = [(p.number, p.suffix) for p in phases]
    is_sequential = all(phase_keys[i] < phase_keys[i + 1] for i in range(len(phase_keys) - 1))
    if is_sequential:
        checks.append((True, "Phase numbering is sequential"))
    else:
        phase_labels = [f"{n}{s}" for n, s in phase_keys]
        checks.append((False, f"Phase numbering is not sequential: {phase_labels}"))

    # Check 6: v2 format integrity
    header_block = find_metadata_block(issue.body, BlockKeys.OBJECTIVE_HEADER)
    if header_block is not None:
        comment_id = header_block.data.get("objective_comment_id")
        if comment_id is not None:
            checks.append((True, "objective-header has objective_comment_id"))
        else:
            checks.append((False, "objective-header missing objective_comment_id"))

    # Check 7: PR references use # prefix
    invalid_refs: list[str] = []
    for node in graph.nodes:
        if node.pr and not node.pr.startswith("#"):
            invalid_refs.append(f"Step {node.id} PR '{node.pr}' missing '#' prefix")

    if not invalid_refs:
        checks.append((True, "PR references use '#' prefix"))
    else:
        checks.append((False, f"Invalid reference format: {invalid_refs[0]}"))

    # Check 8: Roadmap table sync
    check8 = _check_roadmap_table_sync(
        remote, owner=owner, repo=repo, issue_body=issue.body, header_block=header_block
    )
    if check8 is not None:
        checks.append(check8)

    # Check 9: PR backlink consistency
    check9 = _check_pr_backlinks(
        remote, owner=owner, repo=repo, issue_number=issue_number, graph=graph
    )
    if check9 is not None:
        checks.append(check9)

    summary = compute_graph_summary(graph)
    next_node = find_graph_next_node(graph, phases)
    failed_count = sum(1 for passed, _ in checks if not passed)

    return ObjectiveValidationSuccess(
        passed=failed_count == 0,
        checks=checks,
        failed_count=failed_count,
        graph=graph,
        summary=summary,
        next_node=next_node,
        validation_errors=validation_errors,
        issue_body=issue.body,
    )
