"""Update objective roadmap tables with plan references.

This module provides functions to update the PR column of objective roadmap
tables when a plan is created for a step.

PR column format (erk-specific):
- Empty: step is pending
- #XXXX: step is done (merged PR number)
- plan #XXXX: plan in progress (plan issue number)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoadmapUpdateResult:
    """Result of updating objective roadmap.

    Attributes:
        success: Whether the update succeeded
        updated_body: The updated markdown body if successful, None otherwise
        error: Error message if failed, None otherwise
    """

    success: bool
    updated_body: str | None
    error: str | None


def update_roadmap_with_plan(
    objective_body: str,
    *,
    step_id: str,
    plan_issue_number: int,
) -> RoadmapUpdateResult:
    """Update the PR column of a roadmap step to show 'plan #N'.

    Finds the row matching step_id in the roadmap table and updates
    its PR column from empty to 'plan #<plan_issue_number>'.

    Args:
        objective_body: The full markdown body of the objective issue
        step_id: The step identifier to find (e.g., "1.1", "2A.1")
        plan_issue_number: The plan issue number to add

    Returns:
        RoadmapUpdateResult with updated body on success, error message on failure.

    Notes:
        - Only updates if PR column is currently empty
        - Step ID matching is exact (case-sensitive)
        - Works with markdown tables that have Step and PR columns
    """
    lines = objective_body.split("\n")
    header_idx = _find_table_header_index(lines)

    if header_idx is None:
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error="No roadmap table found in objective body",
        )

    # Parse header to find column indices
    header_line = lines[header_idx]
    column_indices = _parse_table_header(header_line)

    if "step" not in column_indices:
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error="Table missing 'Step' column",
        )

    if "pr" not in column_indices:
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error="Table missing 'PR' column",
        )

    step_col_idx = column_indices["step"]
    pr_col_idx = column_indices["pr"]

    # Skip header and separator lines, find matching row
    # Table format: header line, separator line (---|---|...), then data rows
    separator_idx = header_idx + 1
    if separator_idx >= len(lines) or not _is_table_separator(lines[separator_idx]):
        return RoadmapUpdateResult(
            success=False,
            updated_body=None,
            error="Malformed table: missing separator line",
        )

    # Search for matching step in data rows
    for row_idx in range(separator_idx + 1, len(lines)):
        row_line = lines[row_idx]

        # Stop if we've left the table
        if not row_line.strip() or not row_line.strip().startswith("|"):
            break

        cells = _parse_table_row(row_line)
        if len(cells) <= max(step_col_idx, pr_col_idx):
            continue

        row_step_id = cells[step_col_idx].strip()
        if row_step_id != step_id:
            continue

        # Found matching row - check if PR column is empty
        current_pr = cells[pr_col_idx].strip()
        if current_pr:
            return RoadmapUpdateResult(
                success=False,
                updated_body=None,
                error=f"Step {step_id} PR column already has value: {current_pr}",
            )

        # Update the PR column
        cells[pr_col_idx] = f"plan #{plan_issue_number}"
        lines[row_idx] = _format_table_row(cells)

        updated_body = "\n".join(lines)
        return RoadmapUpdateResult(
            success=True,
            updated_body=updated_body,
            error=None,
        )

    return RoadmapUpdateResult(
        success=False,
        updated_body=None,
        error=f"Step '{step_id}' not found in roadmap table",
    )


def _find_table_header_index(lines: list[str]) -> int | None:
    """Find the index of a roadmap-like table header line.

    Looks for a markdown table header that contains either 'Step' or 'PR'
    column to identify it as a potential roadmap table.

    Args:
        lines: List of lines from the objective body

    Returns:
        Index of the header line, or None if not found
    """
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped.startswith("|"):
            continue

        # Check if this looks like a table header with Step or PR columns
        # We'll validate required columns separately
        line_lower = line_stripped.lower()
        if "step" in line_lower or "pr" in line_lower:
            return idx

    return None


def _parse_table_header(header_line: str) -> dict[str, int]:
    """Parse table header to get column name -> index mapping.

    Args:
        header_line: The markdown table header line (e.g., "| Step | Desc | PR |")

    Returns:
        Dictionary mapping lowercase column names to their indices
    """
    cells = _parse_table_row(header_line)
    return {cell.strip().lower(): idx for idx, cell in enumerate(cells) if cell.strip()}


def _parse_table_row(row_line: str) -> list[str]:
    """Parse a markdown table row into cells.

    Args:
        row_line: A table row (e.g., "| 1.1 | Create type | |")

    Returns:
        List of cell contents (without leading/trailing pipes)
    """
    # Strip leading/trailing whitespace and pipes
    row = row_line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]

    # Split by pipe and preserve cell contents
    return row.split("|")


def _format_table_row(cells: list[str]) -> str:
    """Format cells back into a markdown table row.

    Args:
        cells: List of cell contents

    Returns:
        Formatted table row with proper spacing
    """
    # Add consistent spacing around cell contents
    formatted_cells = [f" {cell.strip()} " for cell in cells]
    return "|" + "|".join(formatted_cells) + "|"


def _is_table_separator(line: str) -> bool:
    """Check if a line is a table separator (---|---|---).

    Args:
        line: Line to check

    Returns:
        True if this looks like a table separator line
    """
    line_stripped = line.strip()
    if not line_stripped.startswith("|"):
        return False

    # Check if cells contain only dashes, colons, and spaces
    cells = _parse_table_row(line_stripped)
    for cell in cells:
        cell = cell.strip()
        if not cell:
            continue
        # Valid separator cell contains only dashes and optional colons for alignment
        if not all(c in "-:" for c in cell):
            return False

    return True
