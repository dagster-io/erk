"""Validate an objective's format and roadmap consistency."""

import json
import re
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
    extract_raw_metadata_blocks,
    find_metadata_block,
)
from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapPhase,
    compute_summary,
    find_next_step,
    parse_roadmap,
    serialize_phases,
)
from erk_shared.output.output import user_output

ERK_OBJECTIVE_LABEL = "erk-objective"
# OBJECTIVE_V1_COMPAT: Remove when all objectives use v2
# Match stale status in 4-col and 5-col tables:
# 4-col: | step | desc | - | #123 |  (only matches exactly 4-col rows)
# 5-col: | step | desc | - | plan | #456 |
_STALE_STATUS_4COL = re.compile(
    r"^\|[^|]+\|[^|]+\|\s*-\s*\|\s*(?:#\d+|plan #\d+)\s*\|$", re.MULTILINE
)
_STALE_STATUS_5COL = re.compile(r"^\|[^|]+\|[^|]+\|\s*-\s*\|[^|]*\|\s*#\d+\s*\|$", re.MULTILINE)


@dataclass(frozen=True)
class ObjectiveValidationSuccess:
    """Validation completed (may have passed or failed checks).

    Attributes:
        passed: True if all validation checks passed
        checks: List of (passed, description) tuples for each check
        failed_count: Number of failed checks
        phases: Parsed roadmap phases (empty if parsing failed)
        summary: Step count summary (empty if no phases)
        next_step: First pending step or None
        validation_errors: Parser-level warnings from roadmap parsing
    """

    passed: bool
    checks: list[tuple[bool, str]]
    failed_count: int
    phases: list[RoadmapPhase]
    summary: dict[str, int]
    next_step: dict[str, str] | None
    validation_errors: list[str]


@dataclass(frozen=True)
class ObjectiveValidationError:
    """Could not complete validation (issue not found, etc.)."""

    error: str


ObjectiveValidationResult = ObjectiveValidationSuccess | ObjectiveValidationError


def validate_objective(
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
    *,
    allow_legacy: bool,
) -> ObjectiveValidationResult:
    """Validate an objective programmatically.

    Checks:
    1. Issue exists and has erk-objective label
    2. Roadmap parses successfully
    3. Status/PR consistency (done steps should have PRs)
    4. No orphaned statuses (done without PR reference)
    5. Phase numbering is sequential
    6. No stale display statuses (steps with PRs should have explicit status, not '-')
    7. v2 format integrity (objective-header has objective_comment_id)
    8. Roadmap uses <details> format (unless allow_legacy is True)

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
            phases=[],
            summary={},
            next_step=None,
            validation_errors=validation_errors,
        )

    # Check 3: Status/PR consistency
    consistency_issues: list[str] = []
    for phase in phases:
        for step in phase.steps:
            # Steps with PR #NNN should be done (or planning/skipped)
            if (
                step.pr
                and step.pr.startswith("#")
                and step.status not in ("done", "planning", "skipped")
            ):
                consistency_issues.append(
                    f"Step {step.id} has PR {step.pr} but status is '{step.status}' "
                    f"(expected 'done')"
                )
            # Steps with plan reference should be in_progress (or planning/skipped)
            if (
                step.plan
                and step.plan.startswith("#")
                and step.status not in ("in_progress", "planning", "skipped")
            ):
                consistency_issues.append(
                    f"Step {step.id} has plan {step.plan} but status is '{step.status}' "
                    f"(expected 'in_progress')"
                )

    if not consistency_issues:
        checks.append((True, "Status/PR consistency"))
    else:
        checks.append((False, f"Status/PR consistency: {consistency_issues[0]}"))

    # Check 4: No orphaned done statuses (done steps should have PR reference)
    orphaned: list[str] = []
    for phase in phases:
        for step in phase.steps:
            if step.status == "done" and step.pr is None:
                orphaned.append(f"Step {step.id}")

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

    # Check 6: No stale display statuses (steps with PRs should have explicit status)
    # OBJECTIVE_V1_COMPAT: Remove when all objectives use v2
    # In v2, tables live in comment, not body
    stale_matches = _STALE_STATUS_4COL.findall(issue.body) + _STALE_STATUS_5COL.findall(issue.body)
    if not stale_matches:
        checks.append((True, "No stale display statuses"))
    else:
        checks.append((False, f"Stale '-' status with PR reference: {len(stale_matches)} step(s)"))

    # Check 7: v2 format integrity (if objective-header present, verify objective_comment_id)
    header_block = find_metadata_block(issue.body, "objective-header")
    if header_block is not None:
        comment_id = header_block.data.get("objective_comment_id")
        if comment_id is not None:
            checks.append((True, "objective-header has objective_comment_id"))
        else:
            checks.append((False, "objective-header missing objective_comment_id"))

    # Check 8: Roadmap block uses <details> format (not legacy --- frontmatter)
    raw_blocks = extract_raw_metadata_blocks(issue.body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == "objective-roadmap":
            roadmap_block = block
            break

    if roadmap_block is not None:
        body_stripped = roadmap_block.body.strip()
        uses_details = body_stripped.startswith("<details>")
        if uses_details:
            checks.append((True, "Roadmap block uses <details> format"))
        elif allow_legacy:
            checks.append((True, "Roadmap block uses legacy format (--allow-legacy)"))
        else:
            checks.append(
                (False, "Roadmap block uses legacy --- format (run update-roadmap-step to migrate)")
            )

    summary = compute_summary(phases)
    next_step = find_next_step(phases)
    failed_count = sum(1 for passed, _ in checks if not passed)

    return ObjectiveValidationSuccess(
        passed=failed_count == 0,
        checks=checks,
        failed_count=failed_count,
        phases=phases,
        summary=summary,
        next_step=next_step,
        validation_errors=validation_errors,
    )


@alias("ch")
@click.command("check")
@click.argument("objective_ref", type=str)
@click.option(
    "--json-output", "json_mode", is_flag=True, help="Output structured JSON (for programmatic use)"
)
@click.option(
    "--allow-legacy", is_flag=True, help="Allow legacy --- frontmatter format in roadmap blocks"
)
@click.pass_obj
def check_objective(
    ctx: ErkContext, objective_ref: str, *, json_mode: bool, allow_legacy: bool
) -> None:
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

    result = validate_objective(ctx.issues, repo.root, issue_number, allow_legacy=allow_legacy)

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

    click.echo(
        json.dumps(
            {
                "success": result.passed,
                "issue_number": issue_number,
                "checks": [
                    {"passed": passed, "description": desc} for passed, desc in result.checks
                ],
                "phases": serialize_phases(result.phases),
                "summary": result.summary,
                "next_step": result.next_step,
                "validation_errors": result.validation_errors,
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
