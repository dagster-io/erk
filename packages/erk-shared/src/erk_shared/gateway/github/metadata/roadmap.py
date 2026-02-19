"""Shared parser, serializer, and data types for objective roadmap operations.

This module provides:
- Data types: RoadmapNodeStatus, RoadmapNode, RoadmapPhase
- Parsing: parse_roadmap() (v2 frontmatter only)
- Frontmatter: validate, parse, group, update
- Utilities: compute_summary(), find_next_node(), serialize_phases()

Previously split across objective_roadmap_shared.py and
objective_roadmap_frontmatter.py in the erk package. Consolidated
here to eliminate the circular dependency between erk_shared and erk.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal, cast

import yaml

from erk_shared.gateway.github.metadata.core import (
    extract_raw_metadata_blocks,
    parse_metadata_block_body,
)

RoadmapNodeStatus = Literal["pending", "planning", "done", "in_progress", "blocked", "skipped"]


@dataclass(frozen=True)
class RoadmapNode:
    """A single node in a roadmap phase."""

    id: str
    description: str
    status: RoadmapNodeStatus
    plan: str | None  # None or "#123" (plan issue number)
    pr: str | None  # None or "#456" (landed PR number)
    depends_on: tuple[str, ...] | None  # None = not specified, () = no deps


@dataclass(frozen=True)
class RoadmapPhase:
    """A phase in the objective roadmap."""

    number: int
    suffix: str  # Letter suffix, e.g. "A" for "Phase 1A", "" for "Phase 1"
    name: str
    nodes: list[RoadmapNode]


# ---------------------------------------------------------------------------
# Frontmatter validation and parsing
# ---------------------------------------------------------------------------


def validate_roadmap_frontmatter(
    data: Mapping[str, object],
) -> tuple[list[RoadmapNode] | None, list[str]]:
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

    if schema_version not in ("2", "3"):
        errors.append(f"Unsupported schema_version: {schema_version}")
        return None, errors

    # Validate items list — accept "nodes" (v3) or "steps" (v2)
    if "nodes" in data:
        steps_data = data["nodes"]
    elif "steps" in data:
        steps_data = data["steps"]
    else:
        errors.append("Missing required field: nodes (or steps for v2)")
        return None, errors
    if not isinstance(steps_data, list):
        errors.append("Field 'steps' must be a list")
        return None, errors

    # Parse each step
    steps: list[RoadmapNode] = []
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

        raw_depends_on = step_dict.get("depends_on")
        depends_on: tuple[str, ...] | None = None
        if raw_depends_on is not None:
            if not isinstance(raw_depends_on, list):
                errors.append(f"Step {i} field 'depends_on' must be a list or null")
                return None, errors
            for j, item in enumerate(raw_depends_on):
                if not isinstance(item, str):
                    errors.append(f"Step {i} field 'depends_on' item {j} must be a string")
                    return None, errors
            depends_on = tuple(cast(list[str], raw_depends_on))

        steps.append(
            RoadmapNode(
                id=step_id,
                description=description,
                status=cast(RoadmapNodeStatus, status),
                plan=raw_plan,
                pr=raw_pr,
                depends_on=depends_on,
            )
        )

    return steps, errors


def parse_roadmap_frontmatter(block_content: str) -> list[RoadmapNode] | None:
    """Parse YAML from objective-roadmap metadata block content.

    Only supports ``<details>`` + code block format (v2).

    Args:
        block_content: Raw content from inside the metadata block
                      (between the HTML comment markers)

    Returns:
        Flat list of steps if valid YAML found, None otherwise
    """
    if not block_content.strip().startswith("<details>"):
        return None

    try:
        data = parse_metadata_block_body(block_content)
    except ValueError:
        return None
    steps, _errors = validate_roadmap_frontmatter(data)
    return steps


def render_roadmap_block_inner(nodes: list[RoadmapNode]) -> str:
    """Render roadmap nodes as <details> wrapped YAML code block.

    This produces the same format as other metadata blocks (plan-header,
    objective-header), making roadmap blocks collapsible and well-formatted
    on GitHub.

    Args:
        nodes: Flat list of roadmap nodes to render.

    Returns:
        Inner content for an objective-roadmap metadata block, wrapped in
        ``<details>`` with a YAML code block.
    """
    any_has_depends_on = any(s.depends_on is not None for s in nodes)
    node_dicts: list[dict[str, object]] = []
    for s in nodes:
        node_dict: dict[str, object] = {
            "id": s.id,
            "description": s.description,
            "status": s.status,
            "plan": s.plan,
            "pr": s.pr,
        }
        if any_has_depends_on:
            node_dict["depends_on"] = list(s.depends_on) if s.depends_on is not None else []
        node_dicts.append(node_dict)
    data: dict[str, object] = {
        "schema_version": "3",
        "nodes": node_dicts,
    }
    yaml_content = yaml.safe_dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    yaml_content = yaml_content.rstrip("\n")
    return (
        "<details>\n"
        "<summary><code>objective-roadmap</code></summary>\n"
        "\n"
        "```yaml\n"
        f"{yaml_content}\n"
        "```\n"
        "\n"
        "</details>"
    )


def group_nodes_by_phase(nodes: list[RoadmapNode]) -> list[RoadmapPhase]:
    """Reconstruct RoadmapPhase objects from node ID prefixes.

    Phase membership is derived by convention:
    - "1.1", "1.2" → phase 1
    - "2A.1", "2A.2" → phase 2A
    - "3.1" → phase 3

    Phase names are NOT stored in frontmatter, so this returns
    phases with placeholder names. Callers that need phase names
    must extract them from markdown headers.

    Args:
        nodes: Flat list of nodes

    Returns:
        List of RoadmapPhase objects grouped by ID prefix
    """
    # Group nodes by parsed phase key (number, suffix) to merge equivalent phases.
    # Raw phase_id strings like "1" and "1.2" both resolve to phase (1, ""),
    # so we group by the resolved key rather than the raw string.
    phase_map: dict[tuple[int, str], list[RoadmapNode]] = {}

    for node in nodes:
        # Extract phase identifier from node ID
        # "1.1" → "1", "2A.1" → "2A", "1.2.3" → "1.2"
        # "1", "2", "A" (no dot) → default to phase (1, "")
        if "." not in node.id:
            phase_key = (1, "")
        else:
            phase_id = node.id.rsplit(".", 1)[0]
            match = re.match(r"^(\d+)([A-Z]*)", phase_id)
            if match:
                phase_key = (int(match.group(1)), match.group(2))
            else:
                # Non-numeric phase ID (e.g., "A") — assign to phase 1
                phase_key = (1, "")

        if phase_key not in phase_map:
            phase_map[phase_key] = []

        phase_map[phase_key].append(node)

    # Convert to RoadmapPhase objects
    phases: list[RoadmapPhase] = []

    for (phase_number, phase_suffix), phase_steps in phase_map.items():
        phase_name = f"Phase {phase_number}{phase_suffix}"

        phases.append(
            RoadmapPhase(
                number=phase_number,
                suffix=phase_suffix,
                name=phase_name,
                nodes=phase_steps,
            )
        )

    # Sort phases by number, then suffix
    phases.sort(key=lambda p: (p.number, p.suffix))

    return phases


def update_node_in_frontmatter(
    block_content: str,
    node_id: str,
    *,
    plan: str | None,
    pr: str | None,
    status: RoadmapNodeStatus | None,
) -> str | None:
    """Update a node's plan/PR fields (and optionally status) in frontmatter YAML.

    Args:
        block_content: Raw content from metadata block
        node_id: Node ID to update (e.g., "1.1")
        plan: New plan value. None=preserve existing, ""=clear, "#6464"=set.
        pr: New PR value. None=preserve existing, ""=clear, "#123"=set.
        status: Explicit status to set, or None to infer from resolved values.

    Returns:
        Updated block content with modified YAML, or None if node not found
    """
    steps = parse_roadmap_frontmatter(block_content)

    if steps is None:
        return None

    # Find and update the node
    found = False
    updated_steps: list[RoadmapNode] = []

    for step in steps:
        if step.id == node_id:
            # Resolve PR: None=preserve, ""=clear, "#123"=set
            if pr is None:
                resolved_pr = step.pr
            elif pr:
                resolved_pr = pr
            else:
                resolved_pr = None

            # Resolve plan: None=preserve, ""=clear, "#6464"=set
            if plan is None:
                resolved_plan = step.plan
            else:
                resolved_plan = plan or None

            # Determine status: explicit > infer from resolved values > preserve
            new_status: RoadmapNodeStatus
            if status is not None:
                new_status = status
            elif resolved_pr:
                new_status = cast(RoadmapNodeStatus, "in_progress")
            elif resolved_plan:
                new_status = cast(RoadmapNodeStatus, "in_progress")
            else:
                new_status = step.status  # preserve existing status

            updated_steps.append(
                replace(step, status=new_status, plan=resolved_plan, pr=resolved_pr)
            )
            found = True
        else:
            updated_steps.append(step)

    if not found:
        return None

    return render_roadmap_block_inner(updated_steps)


# ---------------------------------------------------------------------------
# Roadmap parsing (frontmatter-first, table fallback)
# ---------------------------------------------------------------------------


def enrich_phase_names(body: str, phases: list[RoadmapPhase]) -> list[RoadmapPhase]:
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
            enriched_phases.append(replace(phase, name=phase_name_map[key]))
        else:
            # Keep placeholder name if no markdown header found
            enriched_phases.append(phase)

    return enriched_phases


def parse_v2_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]] | None:
    """Parse roadmap strictly from v2 ``<details>`` format.

    Unlike :func:`parse_roadmap`, this function does **not** fall back to
    legacy table parsing.  It returns ``None`` when the body does not
    contain a v2-format ``objective-roadmap`` metadata block, signalling
    the caller that the objective uses a legacy format.

    Returns:
        ``(phases, validation_errors)`` on success, or ``None`` when the
        body is not in v2 format.
    """
    raw_blocks = extract_raw_metadata_blocks(body)
    matching_blocks = [block for block in raw_blocks if block.key == "objective-roadmap"]

    if not matching_blocks:
        return None

    roadmap_block = matching_blocks[0]

    if not roadmap_block.body.strip().startswith("<details>"):
        return None

    data = parse_metadata_block_body(roadmap_block.body)

    if data.get("schema_version") not in ("2", "3"):
        return None

    steps, errors = validate_roadmap_frontmatter(data)
    if steps is None:
        return None

    phases = group_nodes_by_phase(steps)
    phases = enrich_phase_names(body, phases)
    return (phases, errors)


_LEGACY_FORMAT_ERROR = (
    "This objective uses a legacy format that is no longer supported. "
    "To migrate, open Claude Code and use /erk:objective-create to "
    "recreate this objective with the same content."
)


def parse_roadmap(body: str) -> tuple[list[RoadmapPhase], list[str]]:
    """Parse roadmap from v2 YAML frontmatter in objective-roadmap metadata block.

    Returns:
        (phases, validation_errors)
    """
    raw_blocks = extract_raw_metadata_blocks(body)
    matching_blocks = [block for block in raw_blocks if block.key == "objective-roadmap"]

    if matching_blocks:
        roadmap_block = matching_blocks[0]
        try:
            steps = parse_roadmap_frontmatter(roadmap_block.body)
        except ValueError:
            steps = None

        if steps is not None:
            phases = group_nodes_by_phase(steps)
            phases = enrich_phase_names(body, phases)
            return (phases, [])

    # No valid v2 metadata block found — legacy format or missing
    return ([], [_LEGACY_FORMAT_ERROR])


def _format_depends_on(depends_on: tuple[str, ...] | None) -> str:
    """Format depends_on for table display.

    None or empty tuple renders as ``-``, non-empty tuple as comma-separated IDs.
    """
    if depends_on is None or len(depends_on) == 0:
        return "-"
    return ", ".join(depends_on)


def render_roadmap_tables(phases: list[RoadmapPhase]) -> str:
    """Render phases as markdown tables matching the objective-body display format.

    Format per phase:
        ### Phase {number}{suffix}: {name} ({N} PR)
        | Node | Description | Status | Plan | PR |
        |------|-------------|--------|------|----|
        | {id} | {desc}      | {status} | {plan} | {pr} |

    When any node across all phases has ``depends_on`` specified, a "Depends On"
    column is inserted between Description and Status.

    Status display: underscores are replaced with hyphens (in_progress → in-progress).
    Null values render as ``-``.
    """
    any_has_depends_on = any(
        step.depends_on is not None for phase in phases for step in phase.nodes
    )
    sections: list[str] = []

    for phase in phases:
        pr_count = sum(1 for step in phase.nodes if step.pr is not None)
        header = f"### Phase {phase.number}{phase.suffix}: {phase.name} ({pr_count} PR)"

        rows: list[str] = []
        if any_has_depends_on:
            rows.append("| Node | Description | Depends On | Status | Plan | PR |")
            rows.append("|------|-------------|------------|--------|------|----|")
        else:
            rows.append("| Node | Description | Status | Plan | PR |")
            rows.append("|------|-------------|--------|------|----|")

        for step in phase.nodes:
            status_display = step.status.replace("_", "-")
            cells = [
                step.id,
                step.description,
            ]
            if any_has_depends_on:
                cells.append(_format_depends_on(step.depends_on))
            cells.extend(
                [
                    status_display,
                    step.plan if step.plan is not None else "-",
                    step.pr if step.pr is not None else "-",
                ]
            )
            rows.append("| " + " | ".join(cells) + " |")

        sections.append(header + "\n" + "\n".join(rows))

    return "\n\n".join(sections)


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
        for step in phase.nodes:
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
        "total_nodes": total,
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
            "nodes": [
                {
                    "id": step.id,
                    "description": step.description,
                    "status": step.status,
                    "plan": step.plan,
                    "pr": step.pr,
                    "depends_on": list(step.depends_on) if step.depends_on is not None else None,
                }
                for step in phase.nodes
            ],
        }
        for phase in phases
    ]


def find_next_node(phases: list[RoadmapPhase]) -> dict[str, str] | None:
    """Find the first pending step in phase order."""
    for phase in phases:
        for step in phase.nodes:
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
