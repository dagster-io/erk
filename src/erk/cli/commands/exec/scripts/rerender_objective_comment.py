"""Rerender objective comment roadmap tables from YAML source of truth.

Regenerates the markdown roadmap tables in an objective's first comment
from the YAML frontmatter in the issue body (the authoritative source).
This fixes stale or malformed comment tables without modifying the
source-of-truth YAML.

Usage:
    erk exec rerender-objective-comment --issue 7159
    erk exec rerender-objective-comment --all
    erk exec rerender-objective-comment --issue 7159 --dry-run

Output:
    JSON with {success, results: [{issue, status, old_columns, new_columns}]}
    or {success: false, error, message}

Exit Codes:
    0: Success - all objectives processed
    1: Error - missing data or API failure
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import (
    extract_objective_header_comment_id,
)
from erk_shared.gateway.github.metadata.roadmap import (
    ROADMAP_TABLE_MARKER_END,
    ROADMAP_TABLE_MARKER_START,
    enrich_phase_names,
    extract_roadmap_table_section,
    parse_roadmap,
    render_roadmap_tables,
)

ERK_OBJECTIVE_LABEL = "erk-objective"


@dataclass(frozen=True)
class RerenderResult:
    """Result for a single objective rerender."""

    issue: int
    status: str  # "rerendered", "already_current", "skipped", "error"
    message: str
    old_columns: int | None
    new_columns: int | None


@dataclass(frozen=True)
class SuccessResult:
    """Successful rerender operation."""

    success: bool
    results: list[dict[str, object]]
    summary: str


@dataclass(frozen=True)
class ErrorResult:
    """Error during rerender operation."""

    success: bool
    error: str
    message: str


def _count_table_columns(table_text: str) -> int:
    """Count columns in a markdown table by examining the header row.

    Looks for the first row matching ``| ... |`` pattern and counts pipe
    separators. Returns 0 if no table rows found.
    """
    for line in table_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and "---" not in stripped:
            # Count cells by splitting on | and excluding empty edge entries
            cells = [c for c in stripped.split("|") if c.strip()]
            return len(cells)
    return 0


def _rerender_single_objective(
    issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
    *,
    dry_run: bool,
) -> RerenderResult:
    """Rerender roadmap tables for a single objective.

    Fetches the issue body YAML (source of truth), parses it, regenerates
    the markdown tables, and replaces them in the comment.
    """
    # Fetch issue
    issue = issues.get_issue(repo_root, issue_number)
    if isinstance(issue, IssueNotFound):
        return RerenderResult(
            issue=issue_number,
            status="error",
            message=f"Issue #{issue_number} not found",
            old_columns=None,
            new_columns=None,
        )

    # Check label
    if ERK_OBJECTIVE_LABEL not in issue.labels:
        return RerenderResult(
            issue=issue_number,
            status="skipped",
            message=f"Issue #{issue_number} does not have {ERK_OBJECTIVE_LABEL} label",
            old_columns=None,
            new_columns=None,
        )

    # Parse roadmap from issue body YAML (source of truth)
    phases, errors = parse_roadmap(issue.body)
    if not phases:
        return RerenderResult(
            issue=issue_number,
            status="error",
            message=f"Failed to parse roadmap: {'; '.join(errors)}",
            old_columns=None,
            new_columns=None,
        )

    # Get comment ID from objective-header
    comment_id = extract_objective_header_comment_id(issue.body)
    if comment_id is None:
        return RerenderResult(
            issue=issue_number,
            status="skipped",
            message="No objective_comment_id in objective-header (v1 format?)",
            old_columns=None,
            new_columns=None,
        )

    # Fetch current comment body
    comment_body = issues.get_comment_by_id(repo_root, comment_id)

    # Count old columns from existing table
    old_section = extract_roadmap_table_section(comment_body)
    old_columns = _count_table_columns(old_section[0]) if old_section is not None else 0

    # Enrich phase names from comment body (names come from markdown headers)
    enriched_phases = enrich_phase_names(comment_body, phases)

    # Render new tables
    new_tables = render_roadmap_tables(enriched_phases)

    # Count new columns
    new_columns = _count_table_columns(new_tables)

    # Replace the roadmap table section in the comment
    if old_section is not None:
        # Replace content between markers
        new_comment = (
            comment_body[: old_section[1]]
            + ROADMAP_TABLE_MARKER_START
            + "\n"
            + new_tables
            + "\n"
            + ROADMAP_TABLE_MARKER_END
            + comment_body[old_section[2] :]
        )
    else:
        # No markers found - cannot safely replace
        return RerenderResult(
            issue=issue_number,
            status="skipped",
            message="No roadmap table markers found in comment",
            old_columns=old_columns,
            new_columns=new_columns,
        )

    # Check if anything changed
    if new_comment == comment_body:
        return RerenderResult(
            issue=issue_number,
            status="already_current",
            message="Comment tables already match source of truth",
            old_columns=old_columns,
            new_columns=new_columns,
        )

    # Apply update (unless dry-run)
    if not dry_run:
        issues.update_comment(repo_root, comment_id, new_comment)

    return RerenderResult(
        issue=issue_number,
        status="rerendered",
        message="Rerendered roadmap tables from YAML source",
        old_columns=old_columns,
        new_columns=new_columns,
    )


@click.command(name="rerender-objective-comment")
@click.option("--issue", "issue_number", type=int, default=None, help="Objective issue number")
@click.option("--all", "process_all", is_flag=True, help="Process all open objectives")
@click.option("--dry-run", is_flag=True, help="Show what would change without mutating")
@click.pass_context
def rerender_objective_comment(
    ctx: click.Context,
    *,
    issue_number: int | None,
    process_all: bool,
    dry_run: bool,
) -> None:
    """Rerender objective comment roadmap tables from YAML source of truth.

    Regenerates markdown tables in the objective-body comment to match
    the current YAML frontmatter in the issue body. Idempotent: running
    twice produces the same result.
    """
    if issue_number is None and not process_all:
        click.echo(
            json.dumps(
                asdict(
                    ErrorResult(
                        success=False,
                        error="missing_argument",
                        message="Provide --issue <number> or --all",
                    )
                )
            )
        )
        raise SystemExit(1)

    issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Collect issue numbers to process
    issue_numbers: list[int] = []
    if issue_number is not None:
        issue_numbers.append(issue_number)
    else:
        # Fetch all open objectives
        objective_issues = issues.list_issues(
            repo_root=repo_root,
            labels=[ERK_OBJECTIVE_LABEL],
            state="open",
        )
        issue_numbers = [iss.number for iss in objective_issues]

    # Process each objective
    results: list[RerenderResult] = []
    for num in issue_numbers:
        result = _rerender_single_objective(issues, repo_root, num, dry_run=dry_run)
        results.append(result)

    # Build summary
    rerendered = sum(1 for r in results if r.status == "rerendered")
    current = sum(1 for r in results if r.status == "already_current")
    skipped = sum(1 for r in results if r.status == "skipped")
    errored = sum(1 for r in results if r.status == "error")

    summary_parts = [f"{len(results)} objectives checked"]
    if rerendered:
        summary_parts.append(f"{rerendered} rerendered")
    if current:
        summary_parts.append(f"{current} already current")
    if skipped:
        summary_parts.append(f"{skipped} skipped")
    if errored:
        summary_parts.append(f"{errored} errors")
    if dry_run:
        summary_parts.append("(dry-run)")

    click.echo(
        json.dumps(
            asdict(
                SuccessResult(
                    success=True,
                    results=[asdict(r) for r in results],
                    summary=", ".join(summary_parts),
                )
            )
        )
    )
