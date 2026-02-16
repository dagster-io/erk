"""Tests for roadmap frontmatter parser and serializer."""

from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapStep,
    group_steps_by_phase,
    parse_roadmap_frontmatter,
    render_roadmap_block_inner,
    update_step_in_frontmatter,
    validate_roadmap_frontmatter,
)


def _details_block(yaml_content: str) -> str:
    """Wrap YAML content in <details> format for parse_roadmap_frontmatter."""
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


def test_parse_v2_details_frontmatter() -> None:
    """Parse valid v2 <details> frontmatter with separate plan and pr fields."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "- id: '1.2'\n"
        "  description: Second step\n"
        "  status: in_progress\n"
        "  plan: '#456'\n"
        "  pr: null\n"
        "- id: '1.3'\n"
        "  description: Third step\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#789'"
    )

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is not None
    assert len(steps) == 3
    assert steps[0].plan is None
    assert steps[0].pr is None
    assert steps[1].plan == "#456"
    assert steps[1].pr is None
    assert steps[2].plan is None
    assert steps[2].pr == "#789"


def test_parse_legacy_format_returns_none() -> None:
    """Parse returns None for legacy --- frontmatter format."""
    block_content = """---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Step"
    status: "pending"
    plan: null
    pr: null
---"""

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_parse_no_frontmatter() -> None:
    """Parse returns None when no frontmatter markers found."""
    block_content = """Some content without frontmatter markers"""

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_parse_invalid_yaml() -> None:
    """Parse returns None when YAML is malformed."""
    block_content = _details_block("invalid: yaml: content: [")

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_parse_missing_schema_version() -> None:
    """Parse returns None when schema_version field is missing."""
    block_content = _details_block(
        "steps:\n- id: '1.1'\n  description: Step\n  status: pending\n  pr: null"
    )

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_parse_wrong_schema_version() -> None:
    """Parse returns None when schema_version is not '2'."""
    block_content = _details_block(
        "schema_version: '99'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: Step\n"
        "  status: pending\n"
        "  pr: null"
    )

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_parse_steps_not_list() -> None:
    """Parse returns None when steps is not a list."""
    block_content = _details_block("schema_version: '2'\nsteps: not a list")

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_parse_missing_required_field() -> None:
    """Parse returns None when step is missing required field."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: Step\n"
        "  # missing status field\n"
        "  pr: null"
    )

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is None


def test_render_roundtrip() -> None:
    """Render then parse returns same step data."""
    original_steps = [
        RoadmapStep(id="1.1", description="First", status="pending", plan=None, pr=None),
        RoadmapStep(id="1.2", description="Second", status="done", plan=None, pr="#456"),
        RoadmapStep(id="1.3", description="Third", status="in_progress", plan="#789", pr=None),
    ]

    rendered = render_roadmap_block_inner(original_steps)
    parsed_steps = parse_roadmap_frontmatter(rendered)

    assert parsed_steps is not None
    assert len(parsed_steps) == 3
    assert parsed_steps[0].id == "1.1"
    assert parsed_steps[0].plan is None
    assert parsed_steps[0].pr is None
    assert parsed_steps[1].id == "1.2"
    assert parsed_steps[1].plan is None
    assert parsed_steps[1].pr == "#456"
    assert parsed_steps[2].id == "1.3"
    assert parsed_steps[2].plan == "#789"
    assert parsed_steps[2].pr is None


def test_group_steps_by_phase() -> None:
    """Group steps by phase prefix creates correct phases."""
    steps = [
        RoadmapStep(id="1.1", description="Step 1.1", status="pending", plan=None, pr=None),
        RoadmapStep(id="1.2", description="Step 1.2", status="done", plan=None, pr="#123"),
        RoadmapStep(id="2.1", description="Step 2.1", status="pending", plan=None, pr=None),
    ]

    phases = group_steps_by_phase(steps)

    assert len(phases) == 2
    assert phases[0].number == 1
    assert phases[0].suffix == ""
    assert len(phases[0].steps) == 2
    assert phases[0].steps[0].id == "1.1"
    assert phases[0].steps[1].id == "1.2"
    assert phases[1].number == 2
    assert phases[1].suffix == ""
    assert len(phases[1].steps) == 1
    assert phases[1].steps[0].id == "2.1"


def test_group_steps_sub_phases() -> None:
    """Group steps handles sub-phases with letter suffixes."""
    steps = [
        RoadmapStep(id="1A.1", description="Step 1A.1", status="pending", plan=None, pr=None),
        RoadmapStep(id="1A.2", description="Step 1A.2", status="done", plan=None, pr="#123"),
        RoadmapStep(id="1B.1", description="Step 1B.1", status="pending", plan=None, pr=None),
    ]

    phases = group_steps_by_phase(steps)

    assert len(phases) == 2
    assert phases[0].number == 1
    assert phases[0].suffix == "A"
    assert len(phases[0].steps) == 2
    assert phases[1].number == 1
    assert phases[1].suffix == "B"
    assert len(phases[1].steps) == 1


def test_group_steps_sorts_phases() -> None:
    """Group steps sorts phases by number then suffix."""
    steps = [
        RoadmapStep(id="2.1", description="Step 2.1", status="pending", plan=None, pr=None),
        RoadmapStep(id="1B.1", description="Step 1B.1", status="pending", plan=None, pr=None),
        RoadmapStep(id="1A.1", description="Step 1A.1", status="pending", plan=None, pr=None),
    ]

    phases = group_steps_by_phase(steps)

    assert len(phases) == 3
    assert phases[0].number == 1
    assert phases[0].suffix == "A"
    assert phases[1].number == 1
    assert phases[1].suffix == "B"
    assert phases[2].number == 2
    assert phases[2].suffix == ""


def test_update_step_in_frontmatter() -> None:
    """Update step PR field returns updated frontmatter."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "- id: '1.2'\n"
        "  description: Second step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.2", plan=None, pr="#789", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert len(steps) == 2
    # First step unchanged
    assert steps[0].id == "1.1"
    assert steps[0].pr is None
    # Second step updated (--pr auto-clears plan, status inferred as done)
    assert steps[1].id == "1.2"
    assert steps[1].pr == "#789"
    assert steps[1].plan is None
    assert steps[1].status == "done"


def test_update_step_in_frontmatter_not_found() -> None:
    """Update step returns None when step ID not found."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(
        block_content, "999.999", plan=None, pr="#123", status=None
    )

    assert updated is None


def test_update_step_preserves_other_steps() -> None:
    """Update step leaves non-target steps unchanged."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#111'\n"
        "- id: '1.2'\n"
        "  description: Second\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "- id: '1.3'\n"
        "  description: Third\n"
        "  status: in_progress\n"
        "  plan: '#222'\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.2", plan=None, pr="#333", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert len(steps) == 3
    # First step unchanged
    assert steps[0].id == "1.1"
    assert steps[0].status == "done"
    assert steps[0].pr == "#111"
    # Second step updated
    assert steps[1].id == "1.2"
    assert steps[1].pr == "#333"
    # Third step unchanged
    assert steps[2].id == "1.3"
    assert steps[2].status == "in_progress"
    assert steps[2].plan == "#222"


def test_parse_handles_extra_fields() -> None:
    """Parse ignores extra fields in step data (forward compatibility)."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: Step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "  extra_field: ignored"
    )

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is not None
    assert len(steps) == 1
    assert steps[0].id == "1.1"


def test_validate_roadmap_frontmatter_valid() -> None:
    """Validate returns steps and no errors for valid data."""
    data: dict[str, object] = {
        "schema_version": "2",
        "steps": [
            {
                "id": "1.1",
                "description": "First",
                "status": "pending",
                "plan": None,
                "pr": None,
            },
            {
                "id": "1.2",
                "description": "Second",
                "status": "done",
                "plan": None,
                "pr": "#123",
            },
        ],
    }

    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is not None
    assert errors == []
    assert len(steps) == 2
    assert steps[0].id == "1.1"
    assert steps[1].pr == "#123"


def test_validate_roadmap_frontmatter_missing_schema_version() -> None:
    """Validate returns error when schema_version is missing."""
    data: dict[str, object] = {
        "steps": [{"id": "1.1", "description": "Step", "status": "pending", "pr": None}],
    }

    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is None
    assert len(errors) == 1
    assert "schema_version" in errors[0]


def test_validate_roadmap_frontmatter_wrong_schema_version() -> None:
    """Validate returns error for unsupported schema version."""
    data: dict[str, object] = {
        "schema_version": "99",
        "steps": [],
    }

    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is None
    assert len(errors) == 1
    assert "99" in errors[0]


def test_validate_roadmap_frontmatter_v1_rejected() -> None:
    """Validate returns error for schema_version '1' (no longer supported)."""
    data: dict[str, object] = {
        "schema_version": "1",
        "steps": [{"id": "1.1", "description": "Step", "status": "pending"}],
    }

    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is None
    assert len(errors) == 1
    assert "1" in errors[0]


def test_validate_roadmap_frontmatter_missing_step_field() -> None:
    """Validate returns error when step is missing required field."""
    data: dict[str, object] = {
        "schema_version": "2",
        "steps": [{"id": "1.1", "description": "Step"}],  # missing status
    }

    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is None
    assert len(errors) == 1
    assert "status" in errors[0]


def test_validate_roadmap_frontmatter_steps_not_list() -> None:
    """Validate returns error when steps is not a list."""
    data: dict[str, object] = {
        "schema_version": "2",
        "steps": "not a list",
    }

    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is None
    assert len(errors) == 1
    assert "list" in errors[0]


def test_update_step_with_explicit_status() -> None:
    """Update step with explicit status sets that status instead of pending."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan=None, pr="#123", status="done")

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].status == "done"
    assert steps[0].pr == "#123"


def test_update_step_status_none_infers_from_pr() -> None:
    """Update step with status=None infers status from resolved PR value."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#100'"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan=None, pr="#200", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].status == "done"  # Inferred from PR value
    assert steps[0].pr == "#200"


def test_update_step_with_plan() -> None:
    """Update step with explicit plan reference."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan="#6464", pr="", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].plan == "#6464"
    assert steps[0].pr is None


def test_update_step_status_inferred_from_pr() -> None:
    """Update step with status=None and PR set infers 'done' status."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan=None, pr="#999", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].status == "done"
    assert steps[0].pr == "#999"


def test_update_step_status_inferred_from_plan() -> None:
    """Update step with status=None and plan set infers 'in_progress' status."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan="#6464", pr="", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].status == "in_progress"
    assert steps[0].plan == "#6464"


def test_update_step_preserves_status_when_both_none() -> None:
    """Update step with status=None and both plan/pr=None preserves existing status."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: planning\n"
        "  plan: null\n"
        "  pr: '#200'"
    )

    # Both plan and pr are None → preserve existing values
    updated = update_step_in_frontmatter(block_content, "1.1", plan=None, pr=None, status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    # Status should be inferred from preserved pr="#200" → "done"
    assert steps[0].status == "done"
    assert steps[0].pr == "#200"


def test_update_step_none_pr_preserves_existing() -> None:
    """Update step with pr=None preserves existing PR value."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: in_progress\n"
        "  plan: '#6464'\n"
        "  pr: '#200'"
    )

    # Set plan only, preserve PR
    updated = update_step_in_frontmatter(
        block_content, "1.1", plan="#7777", pr=None, status="planning"
    )

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].plan == "#7777"
    assert steps[0].pr == "#200"  # preserved
    assert steps[0].status == "planning"


def test_update_step_pr_auto_clears_plan() -> None:
    """Setting --pr auto-clears plan reference."""
    block_content = _details_block(
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: in_progress\n"
        "  plan: '#6464'\n"
        "  pr: null"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan=None, pr="#999", status=None)

    assert updated is not None
    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    # Plan should be auto-cleared when PR is set
    assert steps[0].plan is None
    assert steps[0].pr == "#999"


def test_parse_roadmap_frontmatter_details_format() -> None:
    """Parse the <details> + code block format used by new roadmap blocks."""
    block_content = (
        "<details>\n"
        "<summary><code>objective-roadmap</code></summary>\n"
        "\n"
        "```yaml\n"
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: First step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "- id: '1.2'\n"
        "  description: Second step\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#123'\n"
        "```\n"
        "\n"
        "</details>"
    )

    steps = parse_roadmap_frontmatter(block_content)

    assert steps is not None
    assert len(steps) == 2
    assert steps[0].id == "1.1"
    assert steps[0].status == "pending"
    assert steps[0].plan is None
    assert steps[0].pr is None
    assert steps[1].id == "1.2"
    assert steps[1].status == "done"
    assert steps[1].pr == "#123"


def test_render_roadmap_block_inner() -> None:
    """Render roadmap block inner produces <details> + code block format."""
    steps = [
        RoadmapStep(id="1.1", description="First", status="pending", plan=None, pr=None),
        RoadmapStep(id="1.2", description="Second", status="done", plan=None, pr="#456"),
    ]

    result = render_roadmap_block_inner(steps)

    assert result.startswith("<details>\n")
    assert "<summary><code>objective-roadmap</code></summary>" in result
    assert "```yaml" in result
    assert "```\n" in result
    assert result.endswith("</details>")
    assert "schema_version: '2'" in result
    assert "id: '1.1'" in result or 'id: "1.1"' in result

    # Verify the rendered output is parseable
    parsed = parse_roadmap_frontmatter(result)
    assert parsed is not None
    assert len(parsed) == 2
    assert parsed[0].id == "1.1"
    assert parsed[1].pr == "#456"


def test_render_roundtrip_via_update_details() -> None:
    """update_step_in_frontmatter preserves <details> format on <details> input."""
    block_content = (
        "<details>\n"
        "<summary><code>objective-roadmap</code></summary>\n"
        "\n"
        "```yaml\n"
        "schema_version: '2'\n"
        "steps:\n"
        "- id: '1.1'\n"
        "  description: Step one\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "```\n"
        "\n"
        "</details>"
    )

    updated = update_step_in_frontmatter(block_content, "1.1", plan="#100", pr="", status=None)

    assert updated is not None
    assert "<details>" in updated
    assert "</details>" in updated
    assert "---" not in updated

    steps = parse_roadmap_frontmatter(updated)
    assert steps is not None
    assert steps[0].plan == "#100"
    assert steps[0].status == "in_progress"

    # Second update also stays <details>
    updated2 = update_step_in_frontmatter(updated, "1.1", plan=None, pr="#200", status=None)
    assert updated2 is not None
    assert "<details>" in updated2
    steps2 = parse_roadmap_frontmatter(updated2)
    assert steps2 is not None
    assert steps2[0].pr == "#200"
    assert steps2[0].plan is None
    assert steps2[0].status == "done"
