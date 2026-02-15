"""Shared parser and data types for objective roadmap operations.

Parses objective roadmaps from YAML frontmatter within
<!-- erk:metadata-block:objective-roadmap --> blocks. Table rendering
is maintained for human readability but is not parsed.

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
    """Parse roadmap from YAML frontmatter within objective-roadmap metadata block.

    Returns:
        (phases, validation_errors)
    """
    raw_blocks = extract_raw_metadata_blocks(body)
    roadmap_block = None
    for block in raw_blocks:
        if block.key == "objective-roadmap":
            roadmap_block = block
            break

    if roadmap_block is None:
        return ([], ["No objective-roadmap frontmatter block found"])

    # Import here to avoid circular dependency
    from erk.cli.commands.exec.scripts.objective_roadmap_frontmatter import (
        group_steps_by_phase,
        parse_roadmap_frontmatter,
    )

    steps = parse_roadmap_frontmatter(roadmap_block.body)

    if steps is None:
        return ([], ["No objective-roadmap frontmatter block found"])

    phases = group_steps_by_phase(steps)
    phases = _enrich_phase_names(body, phases)
    return (phases, [])


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
