"""Parse an objective's roadmap tables and return structured JSON.

Usage:
    erk exec objective-roadmap-check <OBJECTIVE_NUMBER>

Output:
    JSON with {success, issue_number, title, phases, summary, next_step, validation_errors}

Exit Codes:
    0: Success - roadmap parsed (even with validation warnings)
    1: Error - issue not found, API error, or critical validation failure
"""

import json
import re
from dataclasses import dataclass

import click

from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.context.helpers import (
    require_repo_root,
)


@dataclass(frozen=True)
class RoadmapStep:
    """A single step in a roadmap phase."""

    id: str
    description: str
    status: str  # "pending", "done", "in_progress", "blocked", "skipped"
    pr: str | None  # None, "#123", or "plan #123"


@dataclass(frozen=True)
class RoadmapPhase:
    """A phase in the objective roadmap."""

    number: int
    name: str
    steps: list[RoadmapStep]


def _parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]:
    """Parse roadmap markdown tables into phases and steps.

    Returns:
        (phases, validation_errors)
    """
    phases: list[RoadmapPhase] = []
    validation_errors: list[str] = []

    # Find all phase headers: ### Phase N: Name or ### Phase NA: Name
    phase_pattern = re.compile(
        r"^###\s+Phase\s+(\d+)([A-Z]?):\s*(.+?)(?:\s+\(\d+\s+PR\))?$", re.MULTILINE
    )
    phase_matches = list(phase_pattern.finditer(body))

    if not phase_matches:
        validation_errors.append("No phase headers found (expected '### Phase N: Name')")
        return phases, validation_errors

    for phase_match in phase_matches:
        phase_number = int(phase_match.group(1))
        phase_name = phase_match.group(3).strip()

        # Extract the section after this phase header until the next phase header or end
        phase_start = phase_match.end()
        next_match_index = phase_matches.index(phase_match) + 1
        if next_match_index < len(phase_matches):
            phase_end = phase_matches[next_match_index].start()
        else:
            phase_end = len(body)

        phase_body = body[phase_start:phase_end]

        # Find the table in this phase section
        # Table header: | Step | Description | Status | PR |
        table_header_pattern = re.compile(
            r"^\|\s*Step\s*\|\s*Description\s*\|\s*Status\s*\|\s*PR\s*\|$",
            re.MULTILINE | re.IGNORECASE,
        )
        header_match = table_header_pattern.search(phase_body)

        if not header_match:
            validation_errors.append(
                f"Phase {phase_number} is missing roadmap table "
                f"(expected header: | Step | Description | Status | PR |)"
            )
            continue

        # Find table rows after the separator line
        # Skip the separator line (|---|---|---|---|)
        table_start = header_match.end()
        separator_pattern = re.compile(r"^\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|$", re.MULTILINE)
        separator_match = separator_pattern.search(phase_body[table_start:])

        if not separator_match:
            validation_errors.append(f"Phase {phase_number} table is missing separator line")
            continue

        rows_start = table_start + separator_match.end()
        # Extract all rows until we hit a blank line or non-table content
        rows_text = phase_body[rows_start:]
        row_pattern = re.compile(r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$", re.MULTILINE)
        row_matches = row_pattern.finditer(rows_text)

        steps: list[RoadmapStep] = []
        for row_match in row_matches:
            step_id = row_match.group(1).strip()
            description = row_match.group(2).strip()
            status_col = row_match.group(3).strip().lower()
            pr_col = row_match.group(4).strip()

            # Check for letter-format step IDs (warning, not error)
            if re.match(r"^\d+[A-Z]\.\d+$", step_id):
                validation_errors.append(
                    f"Step ID '{step_id}' uses letter format — prefer plain numbers "
                    f"(e.g., {step_id[0]}.{step_id.split('.')[1]})"
                )

            # Infer status based on status column and PR column
            if status_col in ("blocked", "skipped"):
                status = status_col
            elif pr_col and pr_col != "-" and pr_col.startswith("#"):
                status = "done"
            elif pr_col and pr_col.startswith("plan #"):
                status = "in_progress"
            else:
                status = "pending"

            # Parse PR reference
            pr_value: str | None = None
            if pr_col and pr_col != "-":
                pr_value = pr_col

            steps.append(
                RoadmapStep(
                    id=step_id,
                    description=description,
                    status=status,
                    pr=pr_value,
                )
            )

        if not steps:
            validation_errors.append(f"Phase {phase_number} has no table rows")
            continue

        phases.append(
            RoadmapPhase(
                number=phase_number,
                name=phase_name,
                steps=steps,
            )
        )

    return phases, validation_errors


def _compute_summary(phases: list[RoadmapPhase]) -> dict[str, int]:
    """Compute summary statistics from phases."""
    total = 0
    pending = 0
    done = 0
    in_progress = 0
    blocked = 0
    skipped = 0

    for phase in phases:
        for step in phase.steps:
            total += 1
            if step.status == "pending":
                pending += 1
            elif step.status == "done":
                done += 1
            elif step.status == "in_progress":
                in_progress += 1
            elif step.status == "blocked":
                blocked += 1
            elif step.status == "skipped":
                skipped += 1

    return {
        "total_steps": total,
        "pending": pending,
        "done": done,
        "in_progress": in_progress,
        "blocked": blocked,
        "skipped": skipped,
    }


def _find_next_step(phases: list[RoadmapPhase]) -> dict[str, str] | None:
    """Find the first pending step in phase order."""
    for phase in phases:
        for step in phase.steps:
            if step.status == "pending":
                return {
                    "id": step.id,
                    "description": step.description,
                    "phase": phase.name,
                }
    return None


@click.command(name="objective-roadmap-check")
@click.argument("objective_number", type=int)
@click.pass_context
def objective_roadmap_check(ctx: click.Context, objective_number: int) -> None:
    """Parse an objective's roadmap tables and return structured JSON."""
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    try:
        issue = github.get_issue(repo_root, objective_number)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to get issue #{objective_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    # Parse the roadmap
    phases, validation_errors = _parse_roadmap(issue.body)

    # If we have critical errors (no phases parsed), return failure
    has_phases = len(phases) > 0
    success = has_phases

    if not success:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "issue_number": issue.number,
                    "title": issue.title,
                    "validation_errors": validation_errors,
                }
            )
        )
        raise SystemExit(1)

    # Compute summary and next step
    summary = _compute_summary(phases)
    next_step = _find_next_step(phases)

    # Convert phases to JSON-serializable format
    phases_json = [
        {
            "number": phase.number,
            "name": phase.name,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "status": step.status,
                    "pr": step.pr,
                }
                for step in phase.steps
            ],
        }
        for phase in phases
    ]

    click.echo(
        json.dumps(
            {
                "success": True,
                "issue_number": issue.number,
                "title": issue.title,
                "phases": phases_json,
                "summary": summary,
                "next_step": next_step,
                "validation_errors": validation_errors,
            }
        )
    )
