"""Shared parser and data types for objective roadmap operations.

Used by both objective-roadmap-check and objective-roadmap-update commands.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RoadmapStep:
    """A single step in a roadmap phase."""

    id: str
    description: str
    status: str  # "pending", "done", "in_progress", "blocked", "skipped"
    pr: str | None  # None, "#123", or "plan #123"
    step_type: str  # "plan" or "objective"
    issue: str | None  # None or "#123" (GitHub issue for this step)
    depends_on: list[str]  # e.g., ["1.1", "1.2"] - step IDs this step depends on


@dataclass(frozen=True)
class RoadmapPhase:
    """A phase in the objective roadmap."""

    number: int
    suffix: str  # Letter suffix, e.g. "A" for "Phase 1A", "" for "Phase 1"
    name: str
    steps: list[RoadmapStep]


def parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]:
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

    for idx, phase_match in enumerate(phase_matches):
        phase_number = int(phase_match.group(1))
        phase_suffix = phase_match.group(2)  # "" or "A", "B", etc.
        phase_name = phase_match.group(3).strip()

        # Extract the section after this phase header until the next phase header or end
        phase_start = phase_match.end()
        next_match_index = idx + 1
        if next_match_index < len(phase_matches):
            phase_end = phase_matches[next_match_index].start()
        else:
            phase_end = len(body)

        phase_body = body[phase_start:phase_end]

        # Find the table in this phase section
        # Try 7-column header first:
        # | Step | Description | Type | Issue | Depends On | Status | PR |
        table_header_7col_pattern = re.compile(
            r"^\|\s*Step\s*\|\s*Description\s*\|\s*Type\s*\|\s*Issue\s*\|"
            r"\s*Depends On\s*\|\s*Status\s*\|\s*PR\s*\|$",
            re.MULTILINE | re.IGNORECASE,
        )
        header_7col_match = table_header_7col_pattern.search(phase_body)

        # Fall back to 4-column header: | Step | Description | Status | PR |
        table_header_4col_pattern = re.compile(
            r"^\|\s*Step\s*\|\s*Description\s*\|\s*Status\s*\|\s*PR\s*\|$",
            re.MULTILINE | re.IGNORECASE,
        )
        header_4col_match = table_header_4col_pattern.search(phase_body)

        if header_7col_match:
            header_match = header_7col_match
            is_7col_format = True
        elif header_4col_match:
            header_match = header_4col_match
            is_7col_format = False
        else:
            validation_errors.append(
                f"Phase {phase_number} is missing roadmap table "
                f"(expected header: | Step | Description | Status | PR | "
                f"or | Step | Description | Type | Issue | Depends On | Status | PR |)"
            )
            continue

        # Find table rows after the separator line
        # Skip the separator line (matches 4 or 7 columns)
        table_start = header_match.end()
        if is_7col_format:
            separator_pattern = re.compile(
                r"^\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|$",
                re.MULTILINE,
            )
        else:
            separator_pattern = re.compile(
                r"^\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|$", re.MULTILINE
            )

        separator_match = separator_pattern.search(phase_body[table_start:])

        if not separator_match:
            validation_errors.append(f"Phase {phase_number} table is missing separator line")
            continue

        rows_start = table_start + separator_match.end()
        # Extract all rows until we hit a blank line or non-table content
        rows_text = phase_body[rows_start:]

        if is_7col_format:
            # 7 columns: Step | Description | Type | Issue | Depends On | Status | PR
            row_pattern = re.compile(
                r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$", re.MULTILINE
            )
        else:
            # 4 columns: Step | Description | Status | PR
            row_pattern = re.compile(r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$", re.MULTILINE)

        row_matches = row_pattern.finditer(rows_text)

        steps: list[RoadmapStep] = []
        for row_match in row_matches:
            if is_7col_format:
                # 7 columns: Step | Description | Type | Issue | Depends On | Status | PR
                step_id = row_match.group(1).strip()
                description = row_match.group(2).strip()
                type_col = row_match.group(3).strip().lower()
                issue_col = row_match.group(4).strip()
                depends_on_col = row_match.group(5).strip()
                status_col = row_match.group(6).strip().lower()
                pr_col = row_match.group(7).strip()

                # Parse step_type: normalize to "plan" or "objective", default "plan"
                if type_col in ("objective", "obj"):
                    step_type = "objective"
                else:
                    step_type = "plan"

                # Parse issue: store "#NNN" or None (treat "-" and empty as None)
                if issue_col and issue_col != "-":
                    issue = issue_col
                else:
                    issue = None

                # Parse depends_on: split on commas, strip whitespace, treat "-" and empty as []
                if depends_on_col and depends_on_col != "-":
                    depends_on = [dep.strip() for dep in depends_on_col.split(",") if dep.strip()]
                else:
                    depends_on = []
            else:
                # 4 columns: Step | Description | Status | PR
                step_id = row_match.group(1).strip()
                description = row_match.group(2).strip()
                status_col = row_match.group(3).strip().lower()
                pr_col = row_match.group(4).strip()

                # Defaults for 4-column format
                step_type = "plan"
                issue = None
                depends_on = []

            # Explicit status values take priority
            if status_col in ("done", "blocked", "skipped"):
                status = status_col
            elif status_col in ("in-progress", "in_progress"):
                status = "in_progress"
            elif status_col == "pending":
                status = "pending"
            # Fall back to PR-column inference for "-" or legacy values
            elif pr_col and pr_col.startswith("#"):
                status = "done"
            elif pr_col and pr_col.startswith("plan #"):
                status = "in_progress"
            else:
                status = "pending"

            steps.append(
                RoadmapStep(
                    id=step_id,
                    description=description,
                    status=status,
                    pr=pr_col if pr_col and pr_col != "-" else None,
                    step_type=step_type,
                    issue=issue,
                    depends_on=depends_on,
                )
            )

        if not steps:
            validation_errors.append(f"Phase {phase_number} has no table rows")
            continue

        phases.append(
            RoadmapPhase(
                number=phase_number,
                suffix=phase_suffix,
                name=phase_name,
                steps=steps,
            )
        )

    return phases, validation_errors


def compute_summary(phases: list[RoadmapPhase]) -> dict[str, int]:
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


def serialize_phases(phases: list[RoadmapPhase]) -> list[dict[str, object]]:
    """Convert phases to JSON-serializable format."""
    return [
        {
            "number": phase.number,
            "suffix": phase.suffix,
            "name": phase.name,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "status": step.status,
                    "pr": step.pr,
                    "step_type": step.step_type,
                    "issue": step.issue,
                    "depends_on": step.depends_on,
                }
                for step in phase.steps
            ],
        }
        for phase in phases
    ]


def find_next_step(phases: list[RoadmapPhase]) -> dict[str, str] | None:
    """Find the first pending step in phase order."""
    for phase in phases:
        for step in phase.steps:
            if step.status == "pending":
                return {
                    "id": step.id,
                    "description": step.description,
                    "phase": phase.name,
                    "step_type": step.step_type,
                }
    return None
