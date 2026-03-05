"""Fetch, validate, and set up context for objective-plan command.

Consolidates data fetching, validation, marker creation, and roadmap
serialization into a single exec command, eliminating the Task agent.

Usage:
    erk exec objective-plan-setup 3679 --session-id SESSION_ID

Output:
    JSON with objective data, roadmap, validation results, and marker status.

Exit Codes:
    0: Success
    1: Error (not found, wrong label, validation error)
"""

import json
from pathlib import Path

import click

from erk.cli.commands.objective.check_cmd import (
    ERK_OBJECTIVE_LABEL,
    ObjectiveValidationError,
    validate_objective,
)
from erk_shared.context.helpers import require_issues, require_repo_root
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.dependency_graph import phases_from_graph
from erk_shared.gateway.github.metadata.roadmap import serialize_phases
from erk_shared.scratch.scratch import get_scratch_dir

MARKER_EXTENSION = ".marker"
ERK_PLAN_LABEL = "erk-plan"


def _fetch_and_setup(
    *,
    github_issues: GitHubIssues,
    repo_root: Path,
    objective_number: int,
    session_id: str,
) -> tuple[dict[str, object], int]:
    """Core setup logic. Returns (result_dict, exit_code)."""
    # Fetch issue
    issue = github_issues.get_issue(repo_root, objective_number)
    if isinstance(issue, IssueNotFound):
        return (
            {
                "success": False,
                "error": "not_found",
                "message": f"Issue #{objective_number} not found",
            },
            1,
        )

    # Check labels
    warnings: list[str] = []
    if ERK_PLAN_LABEL in issue.labels:
        return (
            {
                "success": False,
                "error": "is_plan",
                "message": f"Issue #{objective_number} is an erk-plan, not an objective",
            },
            1,
        )

    if ERK_OBJECTIVE_LABEL not in issue.labels:
        warnings.append(
            f"Issue #{objective_number} does not have the '{ERK_OBJECTIVE_LABEL}' label"
        )

    # Create marker
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    marker_file = scratch_dir / f"objective-context{MARKER_EXTENSION}"
    marker_file.write_text(str(objective_number), encoding="utf-8")

    # Validate objective (reuse check_cmd logic)
    validation_result = validate_objective(github_issues, repo_root, objective_number)

    if isinstance(validation_result, ObjectiveValidationError):
        return (
            {
                "success": False,
                "error": "validation_error",
                "message": validation_result.error,
            },
            1,
        )

    # Build roadmap data
    phases = phases_from_graph(validation_result.graph)

    result: dict[str, object] = {
        "success": True,
        "objective": {
            "number": objective_number,
            "title": issue.title,
            "state": issue.state,
            "labels": issue.labels,
        },
        "roadmap": {
            "phases": serialize_phases(phases),
            "summary": validation_result.summary,
            "next_node": validation_result.next_node,
            "all_complete": validation_result.graph.is_complete(),
        },
        "validation": {
            "passed": validation_result.passed,
            "checks": [
                {"passed": passed, "description": desc} for passed, desc in validation_result.checks
            ],
        },
        "marker_created": True,
        "warnings": warnings,
    }
    return (result, 0)


@click.command(name="objective-plan-setup")
@click.argument("objective_number", type=int)
@click.option("--session-id", required=True, help="Claude session ID for marker storage")
@click.pass_context
def objective_plan_setup(ctx: click.Context, objective_number: int, session_id: str) -> None:
    """Fetch, validate, and set up context for objective planning.

    OBJECTIVE_NUMBER is the GitHub issue number of the objective.

    Creates an objective-context marker and returns structured JSON with
    objective data, roadmap, and validation results.
    """
    github_issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    result, exit_code = _fetch_and_setup(
        github_issues=github_issues,
        repo_root=repo_root,
        objective_number=objective_number,
        session_id=session_id,
    )
    click.echo(json.dumps(result))
    if exit_code != 0:
        raise SystemExit(exit_code)
