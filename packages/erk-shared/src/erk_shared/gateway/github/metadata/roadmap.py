"""Shared parser, serializer, and data types for objective roadmap operations.

This module provides:
- Data types: RoadmapStepStatus, RoadmapStep, RoadmapPhase
- Parsing: parse_roadmap() (frontmatter-first, table fallback)
- Frontmatter: validate, parse, serialize, group, update
- Utilities: compute_summary(), find_next_step(), serialize_phases()

Previously split across objective_roadmap_shared.py and
objective_roadmap_frontmatter.py in the erk package. Consolidated
here to eliminate the circular dependency between erk_shared and erk.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

import yaml

from erk_shared.core.frontmatter import parse_markdown_frontmatter
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


# ---------------------------------------------------------------------------
# Frontmatter validation and parsing
# ---------------------------------------------------------------------------


def validate_roadmap_frontmatter(
    data: Mapping[str, object],
) -> tuple[list[RoadmapStep] | None, list[str]]:
    """Validate parsed frontmatter against the roadmap schema.

    Args:
        data: Parsed YAML dictionary.

    Returns:
        Tuple of (steps, errors). If validation succeeds,
        errors is empty. If validation fails, steps is None.
    """
    errors: list[str] = []

    # Validate schema_version
    schema_version = data.get("schema_version")
    if schema_version is None:
        errors.append("Missing required field: schema_version")
        return None, errors

    if schema_version not in ("1", "2"):
        errors.append(f"Unsupported schema_version: {schema_version}")
        return None, errors

    is_v2 = schema_version == "2"

    # Validate steps is a list
    if "steps" not in data:
        errors.append("Missing required field: steps")
        return None, errors

    steps_data = data["steps"]
    if not isinstance(steps_data, list):
        errors.append("Field 'steps' must be a list")
        return None, errors

    # Parse each step
    steps: list[RoadmapStep] = []
    for i, step_data in enumerate(steps_data):
        if not isinstance(step_data, dict):
            errors.append(f"Step {i} is not a mapping")
            return None, errors

        step_dict = cast(dict[str, object], step_data)

        # Check required fields
        for field in ("id", "description", "status"):
            if field not in step_dict:
                errors.append(f"Step {i} missing required field: {field}")
                return None, errors

        step_id = step_dict["id"]
        description = step_dict["description"]
        status = step_dict["status"]
        raw_plan = step_dict.get("plan")
        raw_pr = step_dict.get("pr")

        # Validate types
        if not isinstance(step_id, str):
            errors.append(f"Step {i} field 'id' must be a string")
            return None, errors
        if not isinstance(description, str):
            errors.append(f"Step {i} field 'description' must be a string")
            return None, errors
        if not isinstance(status, str):
            errors.append(f"Step {i} field 'status' must be a string")
            return None, errors
        if status not in {"pending", "planning", "done", "in_progress", "blocked", "skipped"}:
            valid_statuses = "pending, planning, done, in_progress, blocked, skipped"
            errors.append(f"Step {i} field 'status' must be one of: {valid_statuses}")
            return None, errors
        if raw_plan is not None and not isinstance(raw_plan, str):
            errors.append(f"Step {i} field 'plan' must be a string or null")
            return None, errors
        if raw_pr is not None and not isinstance(raw_pr, str):
            errors.append(f"Step {i} field 'pr' must be a string or null")
            return None, errors

        # v1 migration: "plan #NNN" in pr field → "#NNN" in plan field
        plan_value = raw_plan
        pr_value = raw_pr
        if not is_v2 and isinstance(raw_pr, str) and raw_pr.startswith("plan #"):
            plan_value = "#" + raw_pr[len("plan #") :]
            pr_value = None

        steps.append(
            RoadmapStep(
                id=step_id,
                description=description,
                status=cast(RoadmapStepStatus, status),
                plan=plan_value,
                pr=pr_value,
            )
        )

    return steps, errors


def parse_roadmap_frontmatter(block_content: str) -> list[RoadmapStep] | None:
    """Parse YAML frontmatter from objective-roadmap metadata block content.

    Args:
        block_content: Raw content from inside the metadata block
                      (between the HTML comment markers)

    Returns:
        Flat list of steps if valid frontmatter found, None otherwise

    Uses parse_markdown_frontmatter() for YAML parsing and
    validate_roadmap_frontmatter() for typed validation.
    Returns None on any validation failure (caller falls back to table parsing).
    """
    result = parse_markdown_frontmatter(block_content)

    if not result.is_valid:
        return None

    assert result.metadata is not None
    steps, _errors = validate_roadmap_frontmatter(result.metadata)
    return steps


def serialize_steps_to_frontmatter(steps: list[RoadmapStep]) -> str:
    """Convert step list to YAML frontmatter string.

    Args:
        steps: Flat list of roadmap steps

    Returns:
        YAML frontmatter string with --- delimiters
    """
    data = {
        "schema_version": "2",
        "steps": [
            {
                "id": step.id,
                "description": step.description,
                "status": step.status,
                "plan": step.plan,
                "pr": step.pr,
            }
            for step in steps
        ],
    }

    yaml_content = yaml.safe_dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    # Remove trailing newline from YAML dump
    yaml_content = yaml_content.rstrip("\n")

    return f"---\n{yaml_content}\n---"


def group_steps_by_phase(steps: list[RoadmapStep]) -> list[RoadmapPhase]:
    """Reconstruct RoadmapPhase objects from step ID prefixes.

    Phase membership is derived by convention:
    - "1.1", "1.2" → phase 1
    - "2A.1", "2A.2" → phase 2A
    - "3.1" → phase 3

    Phase names are NOT stored in frontmatter, so this returns
    phases with placeholder names. Callers that need phase names
    must extract them from markdown headers.

    Args:
        steps: Flat list of steps

    Returns:
        List of RoadmapPhase objects grouped by ID prefix
    """
    # Group steps by phase identifier (everything before the last dot)
    phase_map: dict[str, list[RoadmapStep]] = {}

    for step in steps:
        # Extract phase identifier from step ID
        # "1.1" → "1", "2A.1" → "2A", "1.2.3" → "1.2"
        if "." not in step.id:
            # Malformed step ID, skip it
            continue

        phase_id = step.id.rsplit(".", 1)[0]

        if phase_id not in phase_map:
            phase_map[phase_id] = []

        phase_map[phase_id].append(step)

    # Convert to RoadmapPhase objects
    phases: list[RoadmapPhase] = []

    for phase_id, phase_steps in phase_map.items():
        # Parse phase number and suffix from phase_id
        # "1" → (1, ""), "2A" → (2, "A"), "1.2" → error (nested phase)
        match = re.match(r"^(\d+)([A-Z]?)$", phase_id)

        if not match:
            # Malformed phase ID, skip it
            continue

        phase_number = int(match.group(1))
        phase_suffix = match.group(2)

        # Use placeholder name (caller must fill in from markdown)
        phase_name = f"Phase {phase_number}{phase_suffix}"

        phases.append(
            RoadmapPhase(
                number=phase_number,
                suffix=phase_suffix,
                name=phase_name,
                steps=phase_steps,
            )
        )

    # Sort phases by number, then suffix
    phases.sort(key=lambda p: (p.number, p.suffix))

    return phases


def update_step_in_frontmatter(
    block_content: str,
    step_id: str,
    *,
    plan: str | None,
    pr: str | None,
    status: RoadmapStepStatus | None,
) -> str | None:
    """Update a step's plan/PR fields (and optionally status) in frontmatter YAML.

    Args:
        block_content: Raw content from metadata block
        step_id: Step ID to update (e.g., "1.1")
        plan: New plan value. None=preserve existing, ""=clear, "#6464"=set.
        pr: New PR value. None=preserve existing, ""=clear, "#123"=set.
        status: Explicit status to set, or None to infer from resolved values.

    Returns:
        Updated block content with modified YAML, or None if step not found
    """
    steps = parse_roadmap_frontmatter(block_content)

    if steps is None:
        return None

    # Find and update the step
    found = False
    updated_steps: list[RoadmapStep] = []

    for step in steps:
        if step.id == step_id:
            # Resolve PR: None=preserve, ""=clear, "#123"=set
            if pr is None:
                resolved_pr = step.pr
            elif pr:
                resolved_pr = pr
            else:
                resolved_pr = None

            # Resolve plan: None=preserve, ""=clear, "#6464"=set
            # Auto-clear: when pr is explicitly set (non-None, non-empty)
            # and plan is not explicitly provided, clear plan.
            if plan is not None:
                if plan:
                    resolved_plan = plan
                else:
                    resolved_plan = None
            elif pr is not None and pr:
                # Setting --pr auto-clears plan (only when pr is explicitly provided)
                resolved_plan = None
            else:
                resolved_plan = step.plan

            # Determine status: explicit > infer from resolved values > preserve
            new_status: RoadmapStepStatus
            if status is not None:
                new_status = status
            elif resolved_pr:
                new_status = cast(RoadmapStepStatus, "done")
            elif resolved_plan:
                new_status = cast(RoadmapStepStatus, "in_progress")
            else:
                new_status = step.status  # preserve existing status

            updated_steps.append(
                RoadmapStep(
                    id=step.id,
                    description=step.description,
                    status=new_status,
                    plan=resolved_plan,
                    pr=resolved_pr,
                )
            )
            found = True
        else:
            updated_steps.append(step)

    if not found:
        return None

    # Serialize back to frontmatter
    frontmatter_str = serialize_steps_to_frontmatter(updated_steps)

    # Extract non-frontmatter content from original block
    # (there might be markdown after the frontmatter)
    frontmatter_pattern = r"^---\s*\n.*?\n---\s*\n?"
    remainder = re.sub(
        frontmatter_pattern, "", block_content, count=1, flags=re.DOTALL | re.MULTILINE
    )

    # Reconstruct block content
    if remainder:
        return f"{frontmatter_str}\n\n{remainder}"
    else:
        return frontmatter_str


# ---------------------------------------------------------------------------
# Roadmap parsing (frontmatter-first, table fallback)
# ---------------------------------------------------------------------------


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
        steps = parse_roadmap_frontmatter(roadmap_block.body)

        if steps is not None:
            # Successfully parsed frontmatter
            phases = group_steps_by_phase(steps)
            # Extract phase names from markdown headers
            phases = _enrich_phase_names(body, phases)
            return (phases, [])

    # OBJECTIVE_V1_COMPAT: Remove when all objectives use v2
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
            status: RoadmapStepStatus
            if status_col in ("done", "blocked", "skipped", "planning"):
                status = cast(RoadmapStepStatus, status_col)
            elif status_col in ("in-progress", "in_progress"):
                status = cast(RoadmapStepStatus, "in_progress")
            elif status_col == "pending":
                status = cast(RoadmapStepStatus, "pending")
            # Fall back to column inference for "-" or legacy values
            elif pr_value and pr_value.startswith("#"):
                status = cast(RoadmapStepStatus, "done")
            elif plan_value and plan_value.startswith("#"):
                status = cast(RoadmapStepStatus, "in_progress")
            else:
                status = cast(RoadmapStepStatus, "pending")

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


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Roadmap table markers
# ---------------------------------------------------------------------------

ROADMAP_TABLE_MARKER_START = "<!-- erk:roadmap-table -->"
ROADMAP_TABLE_MARKER_END = "<!-- /erk:roadmap-table -->"


def wrap_roadmap_tables_with_markers(content: str) -> str:
    """Wrap the roadmap section (phase headers + tables) with HTML comment markers.

    Finds the first ``### Phase N:`` header through the end of the last table
    and wraps the entire range with ``<!-- erk:roadmap-table -->`` /
    ``<!-- /erk:roadmap-table -->``.

    If markers already exist, replaces them in-place.
    If no phase headers are found, returns content unchanged.

    Args:
        content: Objective markdown content (typically the objective-body comment).

    Returns:
        Content with roadmap section wrapped in markers.
    """
    # Remove any existing markers first
    content = content.replace(ROADMAP_TABLE_MARKER_START + "\n", "")
    content = content.replace("\n" + ROADMAP_TABLE_MARKER_END, "")
    content = content.replace(ROADMAP_TABLE_MARKER_START, "")
    content = content.replace(ROADMAP_TABLE_MARKER_END, "")

    # Find all phase headers
    phase_pattern = re.compile(r"^###\s+Phase\s+\d+[A-Z]?:\s*.+$", re.MULTILINE)
    phase_matches = list(phase_pattern.finditer(content))

    if not phase_matches:
        return content

    # Start of the roadmap section is the first phase header
    roadmap_start = phase_matches[0].start()

    # End is after the last table row following the last phase header
    last_phase_end = phase_matches[-1].end()
    remaining = content[last_phase_end:]

    # Find the last table row (| ... |) after the last phase header
    table_row_pattern = re.compile(r"^\|.+\|$", re.MULTILINE)
    last_row_end = last_phase_end
    for match in table_row_pattern.finditer(remaining):
        last_row_end = last_phase_end + match.end()

    roadmap_end = last_row_end

    # Extract the roadmap section and wrap it
    before = content[:roadmap_start]
    roadmap = content[roadmap_start:roadmap_end]
    after = content[roadmap_end:]

    return f"{before}{ROADMAP_TABLE_MARKER_START}\n{roadmap}\n{ROADMAP_TABLE_MARKER_END}{after}"


def extract_roadmap_table_section(text: str) -> tuple[str, int, int] | None:
    """Extract the roadmap table section bounded by markers.

    Args:
        text: Full text that may contain roadmap table markers.

    Returns:
        Tuple of (section_content, start_offset, end_offset) if markers found,
        None otherwise.
    """
    start_idx = text.find(ROADMAP_TABLE_MARKER_START)
    if start_idx == -1:
        return None

    end_idx = text.find(ROADMAP_TABLE_MARKER_END, start_idx)
    if end_idx == -1:
        return None

    content_start = start_idx + len(ROADMAP_TABLE_MARKER_START)
    section = text[content_start:end_idx]
    return (section, start_idx, end_idx + len(ROADMAP_TABLE_MARKER_END))
