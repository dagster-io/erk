"""Render a complete roadmap section from structured JSON input.

Takes structured JSON from stdin describing phases/steps and outputs
a complete ## Roadmap markdown section with phase headers, tables,
test sections, and a machine-readable metadata block.

Usage:
    echo '<json>' | erk exec objective-render-roadmap

Input JSON:
    {
      "phases": [
        {
          "name": "Steelthread",
          "description": "Minimal vertical slice.",
          "pr_count": "1 PR",
          "steps": [
            {"id": "1.1", "description": "Minimal infrastructure"},
            {"id": "1.2", "description": "Wire into one path"}
          ],
          "test": "End-to-end acceptance test"
        }
      ]
    }

Output:
    Complete ## Roadmap section including:
    - Phase headers (### Phase 1: Name (1 PR))
    - Phase descriptions
    - 5-column markdown tables (Step | Description | Status | Plan | PR)
    - Test sections per phase
    - Metadata block (auto-generated, guaranteed in sync)

Exit Codes:
    0: Success
    1: Invalid input
"""

import json
import sys
from typing import Any

import click

from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapNode,
    render_roadmap_block_inner,
)


def _validate_input(data: Any) -> tuple[list[dict[str, Any]], str | None]:
    """Validate input JSON structure.

    Returns:
        Tuple of (phases_list, error_message). If valid, error is None.
    """
    if not isinstance(data, dict):
        return [], "Input must be a JSON object"

    if "phases" not in data:
        return [], "Missing required field: phases"

    phases = data["phases"]
    if not isinstance(phases, list):
        return [], "Field 'phases' must be a list"

    if not phases:
        return [], "Field 'phases' must not be empty"

    for i, phase in enumerate(phases):
        if not isinstance(phase, dict):
            return [], f"Phase {i} must be a JSON object"

        for field in ("name", "steps"):
            if field not in phase:
                return [], f"Phase {i} missing required field: {field}"

        steps = phase["steps"]
        if not isinstance(steps, list):
            return [], f"Phase {i} field 'steps' must be a list"

        if not steps:
            return [], f"Phase {i} field 'steps' must not be empty"

        for j, step in enumerate(steps):
            if not isinstance(step, dict):
                return [], f"Phase {i} step {j} must be a JSON object"

            for field in ("id", "description"):
                if field not in step:
                    return [], f"Phase {i} step {j} missing required field: {field}"

    return phases, None


def _render_roadmap(phases: list[dict[str, Any]]) -> str:
    """Render a complete ## Roadmap markdown section from validated phases.

    Args:
        phases: Validated list of phase dicts from input JSON.

    Returns:
        Complete markdown string for the roadmap section.
    """
    all_steps: list[RoadmapNode] = []
    sections: list[str] = []

    sections.append("## Roadmap")
    sections.append("")

    for phase_index, phase in enumerate(phases):
        phase_number = phase_index + 1
        name = phase["name"]
        pr_count = phase.get("pr_count", "1 PR")

        # Phase header
        sections.append(f"### Phase {phase_number}: {name} ({pr_count})")
        sections.append("")

        # Phase description
        if description := phase.get("description"):
            sections.append(description)
            sections.append("")

        # Table header
        sections.append("| Step | Description | Status | Plan | PR |")
        sections.append("|------|-------------|--------|------|----|")

        # Table rows
        for step_data in phase["steps"]:
            step_id = step_data["id"]
            step_desc = step_data["description"]
            sections.append(f"| {step_id} | {step_desc} | pending | - | - |")

            all_steps.append(
                RoadmapNode(
                    id=step_id,
                    description=step_desc,
                    status="pending",
                    plan=None,
                    pr=None,
                )
            )

        sections.append("")

        # Test section
        if test := phase.get("test"):
            sections.append(f"**Test:** {test}")
            sections.append("")

    # Metadata block
    metadata_inner = render_roadmap_block_inner(all_steps)
    sections.append("<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->")
    sections.append("<!-- erk:metadata-block:objective-roadmap -->")
    sections.append(metadata_inner)
    sections.append("<!-- /erk:metadata-block:objective-roadmap -->")

    return "\n".join(sections)


@click.command(name="objective-render-roadmap")
def objective_render_roadmap() -> None:
    """Render a complete roadmap section from JSON input on stdin.

    Reads structured JSON from stdin describing phases and steps,
    outputs a complete ## Roadmap markdown section with tables and
    a machine-readable metadata block.
    """
    stdin_input = sys.stdin.read()

    if not stdin_input.strip():
        click.echo(
            json.dumps({"success": False, "error": "No input provided on stdin"}),
        )
        raise SystemExit(1)

    try:
        data = json.loads(stdin_input)
    except json.JSONDecodeError as e:
        click.echo(
            json.dumps({"success": False, "error": f"Invalid JSON: {e}"}),
        )
        raise SystemExit(1) from None

    phases, error = _validate_input(data)
    if error is not None:
        click.echo(json.dumps({"success": False, "error": error}))
        raise SystemExit(1)

    roadmap_markdown = _render_roadmap(phases)
    click.echo(roadmap_markdown)
