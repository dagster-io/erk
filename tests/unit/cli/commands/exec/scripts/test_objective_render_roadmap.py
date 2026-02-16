"""Unit tests for objective-render-roadmap command."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.objective_render_roadmap import (
    _render_roadmap,
    _validate_input,
    objective_render_roadmap,
)
from erk_shared.gateway.github.metadata.roadmap import parse_roadmap_frontmatter

# --- Validation tests ---


def test_validate_input_valid_minimal() -> None:
    """Validate accepts minimal valid input."""
    data = {
        "phases": [
            {
                "name": "Steelthread",
                "steps": [
                    {"id": "1.1", "description": "First step"},
                ],
            },
        ],
    }
    phases, error = _validate_input(data)
    assert error is None
    assert len(phases) == 1


def test_validate_input_valid_full() -> None:
    """Validate accepts full input with all optional fields."""
    data = {
        "phases": [
            {
                "name": "Steelthread",
                "description": "Minimal vertical slice.",
                "pr_count": "1 PR",
                "steps": [
                    {"id": "1.1", "description": "Minimal infrastructure"},
                    {"id": "1.2", "description": "Wire into one path"},
                ],
                "test": "End-to-end acceptance test",
            },
            {
                "name": "Complete Feature",
                "description": "Fill out remaining functionality.",
                "pr_count": "2 PRs",
                "steps": [
                    {"id": "2.1", "description": "Extend to remaining commands"},
                ],
                "test": "Full acceptance criteria",
            },
        ],
    }
    phases, error = _validate_input(data)
    assert error is None
    assert len(phases) == 2


def test_validate_input_not_dict() -> None:
    """Validate rejects non-dict input."""
    _, error = _validate_input("not a dict")
    assert error == "Input must be a JSON object"


def test_validate_input_missing_phases() -> None:
    """Validate rejects input without phases field."""
    _, error = _validate_input({})
    assert error == "Missing required field: phases"


def test_validate_input_phases_not_list() -> None:
    """Validate rejects phases that is not a list."""
    _, error = _validate_input({"phases": "not a list"})
    assert error == "Field 'phases' must be a list"


def test_validate_input_empty_phases() -> None:
    """Validate rejects empty phases list."""
    _, error = _validate_input({"phases": []})
    assert error == "Field 'phases' must not be empty"


def test_validate_input_phase_missing_name() -> None:
    """Validate rejects phase without name."""
    data = {"phases": [{"steps": [{"id": "1.1", "description": "Step"}]}]}
    _, error = _validate_input(data)
    assert "missing required field: name" in error


def test_validate_input_phase_missing_steps() -> None:
    """Validate rejects phase without steps."""
    data = {"phases": [{"name": "Phase"}]}
    _, error = _validate_input(data)
    assert "missing required field: steps" in error


def test_validate_input_empty_steps() -> None:
    """Validate rejects phase with empty steps list."""
    data = {"phases": [{"name": "Phase", "steps": []}]}
    _, error = _validate_input(data)
    assert "must not be empty" in error


def test_validate_input_step_missing_id() -> None:
    """Validate rejects step without id."""
    data = {"phases": [{"name": "Phase", "steps": [{"description": "Step"}]}]}
    _, error = _validate_input(data)
    assert "missing required field: id" in error


def test_validate_input_step_missing_description() -> None:
    """Validate rejects step without description."""
    data = {"phases": [{"name": "Phase", "steps": [{"id": "1.1"}]}]}
    _, error = _validate_input(data)
    assert "missing required field: description" in error


# --- Render tests ---


def test_render_roadmap_single_phase() -> None:
    """Render produces correct markdown for a single phase."""
    phases: list[dict[str, object]] = [
        {
            "name": "Foundation",
            "description": "Set up infrastructure.",
            "pr_count": "1 PR",
            "steps": [
                {"id": "1.1", "description": "Create base module"},
                {"id": "1.2", "description": "Add core types"},
            ],
            "test": "Module imports and types are available",
        },
    ]

    result = _render_roadmap(phases)

    assert "## Roadmap" in result
    assert "### Phase 1: Foundation (1 PR)" in result
    assert "Set up infrastructure." in result
    assert "| 1.1 | Create base module | pending | - | - |" in result
    assert "| 1.2 | Add core types | pending | - | - |" in result
    assert "**Test:** Module imports and types are available" in result
    assert "erk:metadata-block:objective-roadmap" in result


def test_render_roadmap_multiple_phases() -> None:
    """Render produces correct markdown for multiple phases."""
    phases: list[dict[str, object]] = [
        {
            "name": "Steelthread",
            "steps": [{"id": "1.1", "description": "Minimal slice"}],
        },
        {
            "name": "Complete Feature",
            "steps": [
                {"id": "2.1", "description": "Extend"},
                {"id": "2.2", "description": "Polish"},
            ],
        },
    ]

    result = _render_roadmap(phases)

    assert "### Phase 1: Steelthread (1 PR)" in result
    assert "### Phase 2: Complete Feature (1 PR)" in result
    assert "| 1.1 |" in result
    assert "| 2.1 |" in result
    assert "| 2.2 |" in result


def test_render_roadmap_metadata_block_parseable() -> None:
    """Rendered metadata block is parseable by the shared parser."""
    phases: list[dict[str, object]] = [
        {
            "name": "Foundation",
            "steps": [
                {"id": "1.1", "description": "First step"},
                {"id": "1.2", "description": "Second step"},
            ],
        },
        {
            "name": "Complete",
            "steps": [
                {"id": "2.1", "description": "Third step"},
            ],
        },
    ]

    result = _render_roadmap(phases)

    # Extract the metadata block content (between the markers)
    start_marker = "<!-- erk:metadata-block:objective-roadmap -->"
    end_marker = "<!-- /erk:metadata-block:objective-roadmap -->"
    start_idx = result.index(start_marker) + len(start_marker) + 1
    end_idx = result.index(end_marker)
    block_content = result[start_idx:end_idx].strip()

    # Parse with the shared parser
    steps = parse_roadmap_frontmatter(block_content)
    assert steps is not None
    assert len(steps) == 3
    assert steps[0].id == "1.1"
    assert steps[0].description == "First step"
    assert steps[0].status == "pending"
    assert steps[0].plan is None
    assert steps[0].pr is None
    assert steps[1].id == "1.2"
    assert steps[2].id == "2.1"


def test_render_roadmap_custom_pr_count() -> None:
    """Render uses custom pr_count when provided."""
    phases: list[dict[str, object]] = [
        {
            "name": "Implementation",
            "pr_count": "2-3 PRs",
            "steps": [{"id": "1.1", "description": "Step"}],
        },
    ]

    result = _render_roadmap(phases)

    assert "### Phase 1: Implementation (2-3 PRs)" in result


def test_render_roadmap_no_optional_fields() -> None:
    """Render works without optional fields (description, pr_count, test)."""
    phases: list[dict[str, object]] = [
        {
            "name": "Phase",
            "steps": [{"id": "1.1", "description": "Do thing"}],
        },
    ]

    result = _render_roadmap(phases)

    assert "### Phase 1: Phase (1 PR)" in result
    assert "| 1.1 | Do thing | pending | - | - |" in result
    assert "**Test:**" not in result


# --- CLI integration tests ---


def test_cli_valid_input() -> None:
    """CLI produces roadmap output for valid JSON input."""
    input_data = json.dumps(
        {
            "phases": [
                {
                    "name": "Steelthread",
                    "steps": [{"id": "1.1", "description": "First step"}],
                    "test": "Acceptance test",
                },
            ],
        }
    )

    runner = CliRunner()
    result = runner.invoke(objective_render_roadmap, input=input_data)

    assert result.exit_code == 0
    assert "## Roadmap" in result.output
    assert "### Phase 1: Steelthread (1 PR)" in result.output
    assert "| 1.1 | First step | pending | - | - |" in result.output
    assert "erk:metadata-block:objective-roadmap" in result.output


def test_cli_empty_input() -> None:
    """CLI exits with error for empty input."""
    runner = CliRunner()
    result = runner.invoke(objective_render_roadmap, input="")

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No input" in output["error"]


def test_cli_invalid_json() -> None:
    """CLI exits with error for invalid JSON."""
    runner = CliRunner()
    result = runner.invoke(objective_render_roadmap, input="not json")

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Invalid JSON" in output["error"]


def test_cli_invalid_structure() -> None:
    """CLI exits with error for valid JSON but invalid structure."""
    runner = CliRunner()
    result = runner.invoke(
        objective_render_roadmap,
        input=json.dumps({"phases": "not a list"}),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "must be a list" in output["error"]
