"""Validate an objective's format and roadmap consistency."""

import json
from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext, RepoContext
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    find_metadata_block,
)
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    compute_graph_summary,
    find_graph_next_step,
    graph_from_phases,
    phases_from_graph,
)
from erk_shared.gateway.github.metadata.roadmap import (
    parse_roadmap,
    serialize_phases,
)
from erk_shared.output.output import user_output

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
        next_step: First pending step or None
        validation_errors: Parser-level warnings from roadmap parsing
        issue_body: Raw issue body text (for phase name enrichment)
    """

    passed: bool
    checks: list[tuple[bool, str]]
    failed_count: int
    graph: DependencyGraph
    summary: dict[str, int]
    next_step: dict[str, str] | None
    validation_errors: list[str]
    issue_body: str


@dataclass(frozen=True)
class ObjectiveValidationError:
    """Could not complete validation (issue not found, etc.)."""

    error: str


ObjectiveValidationResult = ObjectiveValidationSuccess | ObjectiveValidationError


def validate_objective(
    github_issues: GitHubIssues,
    repo_root: Path,
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

    This function does not produce output or raise SystemExit.

    Returns:
        ObjectiveValidationSuccess if validation completed
        ObjectiveValidationError if unable to complete validation
    """
    checks: list[tuple[bool, str]] = []

    # Fetch issue
    issue = github_issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return ObjectiveValidationError(error=f"Issue #{issue_number} not found")

    # Check 1: erk-objective label
    has_label = ERK_OBJECTIVE_LABEL in issue.labels
    if has_label:
        checks.append((True, "Issue has erk-objective label"))
    else:
        checks.append((False, "Issue has erk-objective label"))

    # Check 2: Roadmap parses successfully
    phases, validation_errors = parse_roadmap(issue.body)
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
            next_step=None,
            validation_errors=validation_errors,
            issue_body=issue.body,
        )

    graph = graph_from_phases(phases)

    # Check 3: Status/PR consistency (iterate graph nodes)
    consistency_issues: list[str] = []
    for node in graph.nodes:
        # Steps with PR #NNN should be in_progress or done (or planning/skipped)
        if (
            node.pr
            and node.pr.startswith("#")
            and node.status not in ("in_progress", "done", "planning", "skipped")
        ):
            consistency_issues.append(
                f"Step {node.id} has PR {node.pr} but status is '{node.status}' "
                f"(expected 'in_progress' or 'done')"
            )
        # Steps with plan reference should be in_progress or done (or planning/skipped)
        if (
            node.plan
            and node.plan.startswith("#")
            and node.status not in ("in_progress", "done", "planning", "skipped")
        ):
            consistency_issues.append(
                f"Step {node.id} has plan {node.plan} but status is '{node.status}' "
                f"(expected 'in_progress' or 'done')"
            )

    if not consistency_issues:
        checks.append((True, "Status/PR consistency"))
    else:
        checks.append((False, f"Status/PR consistency: {consistency_issues[0]}"))

    # Check 4: No orphaned done statuses (done steps should have PR reference)
    orphaned: list[str] = []
    for node in graph.nodes:
        if node.status == "done" and node.pr is None:
            orphaned.append(f"Step {node.id}")

    if not orphaned:
        checks.append((True, "No orphaned done statuses (done steps have PR references)"))
    else:
        checks.append((False, f"Done step without PR reference: {', '.join(orphaned)}"))

    # Check 5: Phase numbering is sequential (sub-phases like 1A, 1B, 1C are OK)
    phase_keys = [(p.number, p.suffix) for p in phases]
    is_sequential = all(phase_keys[i] < phase_keys[i + 1] for i in range(len(phase_keys) - 1))
    if is_sequential:
        checks.append((True, "Phase numbering is sequential"))
    else:
        phase_labels = [f"{n}{s}" for n, s in phase_keys]
        checks.append((False, f"Phase numbering is not sequential: {phase_labels}"))

    # Check 6: v2 format integrity (if objective-header present, verify objective_comment_id)
    header_block = find_metadata_block(issue.body, "objective-header")
    if header_block is not None:
        comment_id = header_block.data.get("objective_comment_id")
        if comment_id is not None:
            checks.append((True, "objective-header has objective_comment_id"))
        else:
            checks.append((False, "objective-header missing objective_comment_id"))

    # Check 7: Plan/PR references use # prefix (e.g., "#7146" not "7146")
    invalid_refs: list[str] = []
    for node in graph.nodes:
        if node.plan and not node.plan.startswith("#"):
            invalid_refs.append(f"Step {node.id} plan '{node.plan}' missing '#' prefix")
        if node.pr and not node.pr.startswith("#"):
            invalid_refs.append(f"Step {node.id} PR '{node.pr}' missing '#' prefix")

    if not invalid_refs:
        checks.append((True, "Plan/PR references use '#' prefix"))
    else:
        checks.append((False, f"Invalid reference format: {invalid_refs[0]}"))

    summary = compute_graph_summary(graph)
    next_step = find_graph_next_step(graph, phases)
    failed_count = sum(1 for passed, _ in checks if not passed)

    return ObjectiveValidationSuccess(
        passed=failed_count == 0,
        checks=checks,
        failed_count=failed_count,
        graph=graph,
        summary=summary,
        next_step=next_step,
        validation_errors=validation_errors,
        issue_body=issue.body,
    )


@alias("ch")
@click.command("check")
@click.argument("objective_ref", type=str)
@click.option(
    "--json-output", "json_mode", is_flag=True, help="Output structured JSON (for programmatic use)"
)
@click.pass_obj
def check_objective(ctx: ErkContext, objective_ref: str, *, json_mode: bool) -> None:
    """Validate an objective's format and roadmap consistency.

    OBJECTIVE_REF can be an issue number (42) or a full GitHub URL.

    Checks: erk-objective label, roadmap parsing, status/PR consistency,
    orphaned statuses, and phase numbering.

    Use --json-output for structured JSON output (replaces erk exec objective-roadmap-check).
    """
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)
    issue_number = parse_issue_identifier(objective_ref)

    result = validate_objective(ctx.issues, repo.root, issue_number)

    if json_mode:
        _output_json(result, issue_number)
    else:
        _output_human(result, issue_number)


def _output_json(result: ObjectiveValidationResult, issue_number: int) -> None:
    """Output structured JSON for programmatic consumption."""
    if isinstance(result, ObjectiveValidationError):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": result.error,
                }
            )
        )
        raise SystemExit(1)

    phases = phases_from_graph(result.graph)

    click.echo(
        json.dumps(
            {
                "success": result.passed,
                "issue_number": issue_number,
                "checks": [
                    {"passed": passed, "description": desc} for passed, desc in result.checks
                ],
                "phases": serialize_phases(phases),
                "summary": result.summary,
                "next_step": result.next_step,
                "validation_errors": result.validation_errors,
                "all_complete": result.graph.is_complete(),
            }
        )
    )
    if not result.passed:
        raise SystemExit(1)


def _output_human(result: ObjectiveValidationResult, issue_number: int) -> None:
    """Output human-readable [PASS]/[FAIL] format."""
    if isinstance(result, ObjectiveValidationError):
        user_output(
            click.style("Error: ", fg="red") + f"Failed to validate objective: {result.error}"
        )
        raise SystemExit(1)

    user_output(f"Validating objective #{issue_number}...")
    user_output("")

    for passed, description in result.checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    if result.passed:
        summary = result.summary
        user_output(
            click.style("Objective validation passed", fg="green")
            + f" ({summary.get('done', 0)}/{summary.get('total_steps', 0)} done)"
        )
        raise SystemExit(0)
    else:
        check_word = "checks" if result.failed_count > 1 else "check"
        user_output(
            click.style(
                f"Objective validation failed ({result.failed_count} {check_word} failed)", fg="red"
            )
        )
        raise SystemExit(1)
