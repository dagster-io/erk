"""YAML frontmatter parser and serializer for objective roadmap data.

This module provides the content-layer parser for roadmap frontmatter,
which lives inside <!-- erk:metadata-block:objective-roadmap --> blocks.

Design:
- Frontmatter stores a flat list of steps (no phase structure)
- Phase membership is derived from step ID prefix (e.g., "1.2" → phase 1)
- Phase names live only in markdown headers, not frontmatter
"""

import re
from collections.abc import Mapping
from typing import cast

import yaml

from erk.cli.commands.exec.scripts.objective_roadmap_shared import (
    RoadmapPhase,
    RoadmapStep,
    RoadmapStepStatus,
)
from erk.core.frontmatter import parse_markdown_frontmatter


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
    frontmatter = serialize_steps_to_frontmatter(updated_steps)

    # Extract non-frontmatter content from original block
    # (there might be markdown after the frontmatter)
    frontmatter_pattern = r"^---\s*\n.*?\n---\s*\n?"
    remainder = re.sub(
        frontmatter_pattern, "", block_content, count=1, flags=re.DOTALL | re.MULTILINE
    )

    # Reconstruct block content
    if remainder:
        return f"{frontmatter}\n\n{remainder}"
    else:
        return frontmatter
