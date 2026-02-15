"""Shared parser and data types for objective roadmap operations.

Used by erk objective check (check_cmd.py) and erk exec update-roadmap-step.
"""

import re
from dataclasses import dataclass
from typing import Literal

from erk_shared.gateway.github.metadata.core import extract_raw_metadata_blocks

RoadmapStepStatus = Literal["pending", "planning", "done", "in_progress", "blocked", "skipped"]


@dataclass(frozen=True)
class RoadmapStep:
    """A single step in a roadmap phase."""

    id: str
    description: str
    status: RoadmapStepStatus
    plan: str | None  # None or "#123" (plan issue number)
    pr: str | None  # None or "#456" (landed PR number)


@dataclass(frozen=True)
class RoadmapPhase:
    """A phase in the objective roadmap."""

    number: int
    suffix: str  # Letter suffix, e.g. "A" for "Phase 1A", "" for "Phase 1"
    name: str
    steps: list[RoadmapStep]


def _enrich_phase_names(body: str, phases: list[RoadmapPhase]) -> list[RoadmapPhase]:
    """Extract phase names from markdown headers and enrich phase objects.

    Frontmatter doesn't store phase names, so we extract them from
    markdown headers like "### Phase 1: Planning".

    Args:
        body: Full objective body with markdown headers
        phases: List of phases with placeholder names

    Returns:
        List of phases with actual names from markdown headers
    """
    # Build map of phase identifiers to names from markdown
    phase_pattern = re.compile(
        r"^###\s+Phase\s+(\d+)([A-Z]?):\s*(.+?)(?:\s+\(\d+\s+PR\))?$", re.MULTILINE
    )
    phase_name_map: dict[tuple[int, str], str] = {}

    for match in phase_pattern.finditer(body):
        number = int(match.group(1))
        suffix = match.group(2)
        name = match.group(3).strip()
        phase_name_map[(number, suffix)] = name

    # Enrich phases with actual names
    enriched_phases: list[RoadmapPhase] = []

    for phase in phases:
        key = (phase.number, phase.suffix)
        if key in phase_name_map:
            # Replace placeholder name with actual name from markdown
            enriched_phases.append(
                RoadmapPhase(
                    number=phase.number,
                    suffix=phase.suffix,
                    name=phase_name_map[key],
                    steps=phase.steps,
                )
            )
        else:
            # Keep placeholder name if no markdown header found
            enriched_phases.append(phase)

    return enriched_phases


def parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]:
    """Parse roadmap from YAML frontmatter or markdown tables.

    Tries frontmatter first (within objective-roadmap metadata block),
    falls back to table parsing for backward compatibility.

    Returns:
        (phases, validation_errors)
    """
    # Try frontmatter-first parsing
    raw_blocks = extract_raw_metadata_blocks(body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == "objective-roadmap":
            roadmap_block = block
            break

    if roadmap_block is not None:
        # Import here to avoid circular dependency
        from erk.cli.commands.exec.scripts.objective_roadmap_frontmatter import (
            group_steps_by_phase,
            parse_roadmap_frontmatter,
        )

        steps = parse_roadmap_frontmatter(roadmap_block.body)

        if steps is not None:
            # Successfully parsed frontmatter
            phases = group_steps_by_phase(steps)
            # Extract phase names from markdown headers
            phases = _enrich_phase_names(body, phases)
            return (phases, [])

    # Fall back to table parsing for backward compatibility
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
        # Try 5-col header first: | Step | Description | Status | Plan | PR |
        five_col_header = re.compile(
            r"^\|\s*Step\s*\|\s*Description\s*\|\s*Status\s*\|\s*Plan\s*\|\s*PR\s*\|$",
            re.MULTILINE | re.IGNORECASE,
        )
        four_col_header = re.compile(
            r"^\|\s*Step\s*\|\s*Description\s*\|\s*Status\s*\|\s*PR\s*\|$",
            re.MULTILINE | re.IGNORECASE,
        )

        header_match = five_col_header.search(phase_body)
        is_five_col = header_match is not None
        if header_match is None:
            header_match = four_col_header.search(phase_body)

        if header_match is None:
            validation_errors.append(
                f"Phase {phase_number} is missing roadmap table "
                f"(expected header: | Step | Description | Status | Plan | PR |)"
            )
            continue

        # Find table rows after the separator line
        table_start = header_match.end()
        sep_cell = r"[\s:-]+"
        if is_five_col:
            separator_pattern = re.compile(
                r"^\|" + r"\|".join([sep_cell] * 5) + r"\|$", re.MULTILINE
            )
        else:
            separator_pattern = re.compile(
                r"^\|" + r"\|".join([sep_cell] * 4) + r"\|$", re.MULTILINE
            )
        separator_match = separator_pattern.search(phase_body[table_start:])

        if not separator_match:
            validation_errors.append(f"Phase {phase_number} table is missing separator line")
            continue

        rows_start = table_start + separator_match.end()
        rows_text = phase_body[rows_start:]

        if is_five_col:
            row_pattern = re.compile(r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$", re.MULTILINE)
        else:
            row_pattern = re.compile(r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$", re.MULTILINE)
        row_matches = row_pattern.finditer(rows_text)

        steps: list[RoadmapStep] = []
        for row_match in row_matches:
            step_id = row_match.group(1).strip()
            description = row_match.group(2).strip()
            status_col = row_match.group(3).strip().lower()

            if is_five_col:
                plan_col = row_match.group(4).strip()
                pr_col = row_match.group(5).strip()
            else:
                # 4-col: migrate "plan #NNN" from PR column to plan field
                raw_pr = row_match.group(4).strip()
                if raw_pr.startswith("plan #"):
                    plan_col = "#" + raw_pr[len("plan #") :]
                    pr_col = "-"
                else:
                    plan_col = "-"
                    pr_col = raw_pr

            plan_value = plan_col if plan_col and plan_col != "-" else None
            pr_value = pr_col if pr_col and pr_col != "-" else None

            # Explicit status values take priority
            if status_col in ("done", "blocked", "skipped", "planning"):
                status = status_col
            elif status_col in ("in-progress", "in_progress"):
                status = "in_progress"
            elif status_col == "pending":
                status = "pending"
            # Fall back to column inference for "-" or legacy values
            elif pr_value and pr_value.startswith("#"):
                status = "done"
            elif plan_value and plan_value.startswith("#"):
                status = "in_progress"
            else:
                status = "pending"

            steps.append(
                RoadmapStep(
                    id=step_id,
                    description=description,
                    status=status,
                    plan=plan_value,
                    pr=pr_value,
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
    planning = 0
    done = 0
    in_progress = 0
    blocked = 0
    skipped = 0

    for phase in phases:
        for step in phase.steps:
            total += 1
            if step.status == "pending":
                pending += 1
            elif step.status == "planning":
                planning += 1
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
        "planning": planning,
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
                    "plan": step.plan,
                    "pr": step.pr,
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
                }
    return None
