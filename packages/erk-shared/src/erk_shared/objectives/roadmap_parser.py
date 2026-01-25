# SPDX-License-Identifier: Apache-2.0
"""Parser for objective roadmap tables."""

import re
from dataclasses import dataclass
from typing import Literal

StepStatus = Literal["pending", "done", "blocked", "skipped", "plan-in-progress"]


@dataclass(frozen=True)
class RoadmapStep:
    """A single step from an objective roadmap table."""

    step_id: str
    description: str
    status: StepStatus
    pr_number: int | None
    plan_number: int | None


@dataclass(frozen=True)
class RoadmapParseResult:
    """Result of parsing roadmap tables from an objective body."""

    steps: tuple[RoadmapStep, ...]
    errors: tuple[str, ...]


# Regex patterns for PR column parsing
_PR_DONE_PATTERN = re.compile(r"^\s*#(\d+)\s*$")
_PLAN_IN_PROGRESS_PATTERN = re.compile(r"^\s*plan\s+#(\d+)\s*$", re.IGNORECASE)

# Pattern to find markdown table rows (pipe-delimited)
_TABLE_ROW_PATTERN = re.compile(r"^\s*\|(.+)\|\s*$")


def _parse_pr_column(
    pr_cell: str, status_cell: str
) -> tuple[StepStatus, int | None, int | None]:
    """Parse PR column to determine status, pr_number, and plan_number.

    Args:
        pr_cell: The content of the PR column
        status_cell: The content of the Status column (for overrides)

    Returns:
        Tuple of (status, pr_number, plan_number)
    """
    # Status column overrides take precedence
    status_lower = status_cell.strip().lower()
    if status_lower == "blocked":
        return "blocked", None, None
    if status_lower == "skipped":
        return "skipped", None, None

    pr_cell_stripped = pr_cell.strip()

    # Check for done (merged PR): #123
    done_match = _PR_DONE_PATTERN.match(pr_cell_stripped)
    if done_match:
        return "done", int(done_match.group(1)), None

    # Check for plan-in-progress: plan #456
    plan_match = _PLAN_IN_PROGRESS_PATTERN.match(pr_cell_stripped)
    if plan_match:
        return "plan-in-progress", None, int(plan_match.group(1))

    # Empty or whitespace means pending
    if not pr_cell_stripped:
        return "pending", None, None

    # Anything else is treated as pending (could log a warning)
    return "pending", None, None


def _find_column_indices(
    header_cells: list[str],
) -> tuple[int | None, int | None, int | None, int | None]:
    """Find indices of Step, Description, Status, PR columns.

    Returns:
        Tuple of (step_idx, description_idx, status_idx, pr_idx), any may be None if not found
    """
    step_idx: int | None = None
    description_idx: int | None = None
    status_idx: int | None = None
    pr_idx: int | None = None

    for i, cell in enumerate(header_cells):
        cell_lower = cell.strip().lower()
        if cell_lower == "step":
            step_idx = i
        elif cell_lower == "description":
            description_idx = i
        elif cell_lower == "status":
            status_idx = i
        elif cell_lower == "pr":
            pr_idx = i

    return step_idx, description_idx, status_idx, pr_idx


def _parse_table_row(row: str) -> list[str] | None:
    """Parse a markdown table row into cells.

    Returns:
        List of cell contents, or None if not a valid table row
    """
    match = _TABLE_ROW_PATTERN.match(row)
    if not match:
        return None
    # Split by | and strip each cell
    cells = [cell.strip() for cell in match.group(1).split("|")]
    return cells


def _is_separator_row(cells: list[str]) -> bool:
    """Check if a row is a table separator (all dashes/colons)."""
    for cell in cells:
        stripped = cell.strip()
        # Separator cells contain only dashes and optional colons for alignment
        if stripped and not all(c in "-:" for c in stripped):
            return False
    return True


def parse_roadmap_tables(body: str) -> RoadmapParseResult:
    """Parse roadmap tables from an objective issue body.

    Extracts all steps from markdown tables that have Step, Description, Status, PR columns.

    Args:
        body: The markdown body of an objective issue

    Returns:
        RoadmapParseResult with steps and any parse errors
    """
    if not body:
        return RoadmapParseResult(steps=(), errors=())

    lines = body.split("\n")
    steps: list[RoadmapStep] = []
    errors: list[str] = []

    i = 0
    while i < len(lines):
        # Look for a table header row
        cells = _parse_table_row(lines[i])
        if cells is None:
            i += 1
            continue

        # Check if this looks like a roadmap table header
        step_idx, description_idx, status_idx, pr_idx = _find_column_indices(cells)

        # We need at least Step column to consider this a roadmap table
        if step_idx is None:
            i += 1
            continue

        # Next line should be separator
        i += 1
        if i >= len(lines):
            break

        separator_cells = _parse_table_row(lines[i])
        if separator_cells is None or not _is_separator_row(separator_cells):
            # Not a valid table, continue searching
            continue

        # Parse data rows until we hit a non-table line
        i += 1
        while i < len(lines):
            row_cells = _parse_table_row(lines[i])
            if row_cells is None:
                break

            # Skip if this looks like another separator (malformed table)
            if _is_separator_row(row_cells):
                i += 1
                continue

            # Extract step ID
            if step_idx >= len(row_cells):
                errors.append(f"Row missing Step column: {lines[i]}")
                i += 1
                continue

            step_id = row_cells[step_idx].strip()
            if not step_id:
                i += 1
                continue

            # Extract description (optional)
            description = ""
            if description_idx is not None and description_idx < len(row_cells):
                description = row_cells[description_idx].strip()

            # Extract status and PR columns
            status_cell = ""
            if status_idx is not None and status_idx < len(row_cells):
                status_cell = row_cells[status_idx]

            pr_cell = ""
            if pr_idx is not None and pr_idx < len(row_cells):
                pr_cell = row_cells[pr_idx]

            status, pr_number, plan_number = _parse_pr_column(pr_cell, status_cell)

            steps.append(
                RoadmapStep(
                    step_id=step_id,
                    description=description,
                    status=status,
                    pr_number=pr_number,
                    plan_number=plan_number,
                )
            )

            i += 1

    return RoadmapParseResult(steps=tuple(steps), errors=tuple(errors))


def get_next_actionable_step(steps: tuple[RoadmapStep, ...]) -> RoadmapStep | None:
    """Find the first step ready for planning.

    Returns the first step where:
    - Previous step (if any) is done
    - This step is pending (not done, not blocked, not plan-in-progress)

    Args:
        steps: Tuple of roadmap steps in document order

    Returns:
        The next actionable step, or None if no step is ready
    """
    if not steps:
        return None

    # First step is actionable if pending
    if steps[0].status == "pending":
        return steps[0]

    # For subsequent steps, check if previous step was done
    for i in range(1, len(steps)):
        current = steps[i]
        previous = steps[i - 1]

        if previous.status == "done" and current.status == "pending":
            return current

    return None
