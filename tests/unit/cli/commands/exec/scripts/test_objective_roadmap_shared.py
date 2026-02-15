"""Unit tests for objective_roadmap_shared module."""

from erk.cli.commands.exec.scripts.objective_roadmap_shared import (
    RoadmapPhase,
    RoadmapStep,
    compute_summary,
    find_next_step,
    parse_roadmap,
    serialize_phases,
)

WELL_FORMED_BODY_5COL = """# Objective: Test

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Setup infra"
    status: "done"
    plan: null
    pr: "#100"
  - id: "1.2"
    description: "Add tests"
    status: "in_progress"
    plan: "#101"
    pr: null
  - id: "1.3"
    description: "Update docs"
    status: "pending"
    plan: null
    pr: null
  - id: "2.1"
    description: "Build feature"
    status: "blocked"
    plan: null
    pr: null
  - id: "2.2"
    description: "Performance"
    status: "skipped"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | done | - | #100 |
| 1.2 | Add tests | in-progress | #101 | - |
| 1.3 | Update docs | pending | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build feature | blocked | - | - |
| 2.2 | Performance | skipped | - | - |
"""


def test_parse_roadmap_5col_well_formed() -> None:
    """Test parsing a well-formed roadmap body with frontmatter."""
    phases, errors = parse_roadmap(WELL_FORMED_BODY_5COL)

    assert len(phases) == 2
    assert errors == []

    assert phases[0].number == 1
    assert phases[0].suffix == ""
    assert phases[0].name == "Foundation"
    assert len(phases[0].steps) == 3

    assert phases[1].number == 2
    assert phases[1].suffix == ""
    assert phases[1].name == "Core"
    assert len(phases[1].steps) == 2


def test_parse_roadmap_5col_plan_and_pr_values() -> None:
    """Test that plan and PR values are parsed correctly from frontmatter."""
    phases, _ = parse_roadmap(WELL_FORMED_BODY_5COL)
    steps = phases[0].steps

    assert steps[0].plan is None
    assert steps[0].pr == "#100"
    assert steps[1].plan == "#101"
    assert steps[1].pr is None
    assert steps[2].plan is None
    assert steps[2].pr is None


def test_parse_roadmap_5col_status_inference() -> None:
    """Test that statuses are correctly parsed from frontmatter."""
    phases, _ = parse_roadmap(WELL_FORMED_BODY_5COL)
    steps = phases[0].steps + phases[1].steps

    assert steps[0].status == "done"  # PR #100
    assert steps[1].status == "in_progress"  # plan #101
    assert steps[2].status == "pending"  # no refs
    assert steps[3].status == "blocked"  # explicit status
    assert steps[4].status == "skipped"  # explicit status


def test_parse_roadmap_sub_phases() -> None:
    """Test parsing sub-phase headers like Phase 1A, Phase 1B."""
    body = """## Roadmap

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1A.1"
    description: "Step one"
    status: "pending"
    plan: null
    pr: null
  - id: "1B.1"
    description: "Step two"
    status: "pending"
    plan: null
    pr: null
  - id: "2.1"
    description: "Step three"
    status: "pending"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1A: First Part

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1A.1 | Step one | pending | - | - |

### Phase 1B: Second Part

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1B.1 | Step two | pending | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Step three | pending | - | - |
"""
    phases, _errors = parse_roadmap(body)

    assert len(phases) == 3

    assert phases[0].number == 1
    assert phases[0].suffix == "A"
    assert phases[0].name == "First Part"

    assert phases[1].number == 1
    assert phases[1].suffix == "B"
    assert phases[1].name == "Second Part"

    assert phases[2].number == 2
    assert phases[2].suffix == ""
    assert phases[2].name == "Core"


def test_parse_roadmap_no_phases() -> None:
    """Test parsing body with no frontmatter block."""
    phases, errors = parse_roadmap("No roadmap here.")

    assert phases == []
    assert len(errors) == 1
    assert "No objective-roadmap frontmatter block found" in errors[0]


def test_parse_roadmap_missing_table() -> None:
    """Test parsing body without frontmatter block returns error."""
    body = """### Phase 1: No Table

Just some prose here.
"""
    phases, errors = parse_roadmap(body)

    assert phases == []
    assert any("No objective-roadmap frontmatter block found" in e for e in errors)


def test_compute_summary() -> None:
    """Test summary computation from phases."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            steps=[
                RoadmapStep(id="1.1", description="A", status="done", plan=None, pr="#1"),
                RoadmapStep(id="1.2", description="B", status="pending", plan=None, pr=None),
                RoadmapStep(id="1.3", description="C", status="in_progress", plan="#2", pr=None),
                RoadmapStep(id="1.4", description="D", status="blocked", plan=None, pr=None),
                RoadmapStep(id="1.5", description="E", status="skipped", plan=None, pr=None),
            ],
        )
    ]
    summary = compute_summary(phases)

    assert summary["total_steps"] == 5
    assert summary["done"] == 1
    assert summary["pending"] == 1
    assert summary["in_progress"] == 1
    assert summary["blocked"] == 1
    assert summary["skipped"] == 1


def test_compute_summary_empty() -> None:
    """Test summary computation with no phases."""
    summary = compute_summary([])

    assert summary["total_steps"] == 0
    assert summary["done"] == 0


def test_serialize_phases() -> None:
    """Test serialization of phases to JSON-compatible dicts."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            steps=[
                RoadmapStep(id="1.1", description="A", status="done", plan=None, pr="#1"),
            ],
        )
    ]
    result = serialize_phases(phases)

    assert len(result) == 1
    assert result[0]["number"] == 1
    assert result[0]["suffix"] == ""
    assert result[0]["name"] == "Test"
    assert len(result[0]["steps"]) == 1
    assert result[0]["steps"][0]["id"] == "1.1"
    assert result[0]["steps"][0]["status"] == "done"
    assert result[0]["steps"][0]["plan"] is None
    assert result[0]["steps"][0]["pr"] == "#1"


def test_find_next_step_returns_first_pending() -> None:
    """Test that find_next_step returns the first pending step."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            steps=[
                RoadmapStep(id="1.1", description="Done", status="done", plan=None, pr="#1"),
                RoadmapStep(id="1.2", description="Pending", status="pending", plan=None, pr=None),
                RoadmapStep(
                    id="1.3", description="Also pending", status="pending", plan=None, pr=None
                ),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is not None
    assert result["id"] == "1.2"
    assert result["phase"] == "Phase One"


def test_find_next_step_returns_none_when_all_done() -> None:
    """Test that find_next_step returns None when no pending steps exist."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Done",
            steps=[
                RoadmapStep(id="1.1", description="A", status="done", plan=None, pr="#1"),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is None


def test_parse_roadmap_explicit_done_status() -> None:
    """Test that explicit 'done' status in frontmatter is recognized."""
    body = """## Roadmap

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Step one"
    status: "done"
    plan: null
    pr: "#100"
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | done | - | #100 |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].status == "done"
    assert phases[0].steps[0].pr == "#100"


def test_parse_roadmap_explicit_in_progress_status() -> None:
    """Test that explicit 'in_progress' status in frontmatter is recognized."""
    body = """## Roadmap

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Step one"
    status: "in_progress"
    plan: "#101"
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | in-progress | #101 | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].status == "in_progress"
    assert phases[0].steps[0].plan == "#101"


def test_parse_roadmap_explicit_pending_status() -> None:
    """Test that explicit 'pending' status in frontmatter is recognized."""
    body = """## Roadmap

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Step one"
    status: "pending"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | pending | - | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].status == "pending"
    assert phases[0].steps[0].pr is None


def test_parse_roadmap_explicit_status_overrides_inference() -> None:
    """Test that explicit status values are preserved from frontmatter."""
    body = """## Roadmap

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Explicit done"
    status: "done"
    plan: null
    pr: "#100"
  - id: "1.2"
    description: "Explicit in-progress"
    status: "in_progress"
    plan: "#101"
    pr: null
  - id: "1.3"
    description: "Explicit pending"
    status: "pending"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Explicit done | done | - | #100 |
| 1.2 | Explicit in-progress | in-progress | #101 | - |
| 1.3 | Explicit pending | pending | - | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 3
    assert phases[0].steps[0].status == "done"
    assert phases[0].steps[1].status == "in_progress"
    assert phases[0].steps[2].status == "pending"


def test_parse_roadmap_frontmatter_preferred() -> None:
    """Test that frontmatter is used when metadata block is present."""
    body = """## Objective

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "From frontmatter"
    status: "done"
    plan: null
    pr: "#999"
  - id: "1.2"
    description: "Also from frontmatter"
    status: "pending"
    plan: null
    pr: null
---
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Test Phase

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | From table (ignored) | - | - | #100 |
| 1.2 | Also from table (ignored) | - | - | - |
"""

    phases, errors = parse_roadmap(body)

    # Should use frontmatter data, not table data
    assert errors == []
    assert len(phases) == 1
    assert phases[0].name == "Test Phase"  # Extracted from markdown header
    assert len(phases[0].steps) == 2
    # Values come from frontmatter, not table
    assert phases[0].steps[0].description == "From frontmatter"
    assert phases[0].steps[0].pr == "#999"
    assert phases[0].steps[1].description == "Also from frontmatter"


def test_parse_roadmap_planning_status_recognized() -> None:
    """Test that explicit 'planning' status in frontmatter is recognized."""
    body = """## Roadmap

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "2"
steps:
  - id: "1.1"
    description: "Step one"
    status: "planning"
    plan: null
    pr: "#200"
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | planning | - | #200 |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].status == "planning"
    assert phases[0].steps[0].pr == "#200"


def test_compute_summary_counts_planning() -> None:
    """Test that compute_summary counts planning steps."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            steps=[
                RoadmapStep(id="1.1", description="A", status="planning", plan=None, pr="#200"),
                RoadmapStep(id="1.2", description="B", status="pending", plan=None, pr=None),
                RoadmapStep(id="1.3", description="C", status="done", plan=None, pr="#1"),
            ],
        )
    ]
    summary = compute_summary(phases)

    assert summary["total_steps"] == 3
    assert summary["planning"] == 1
    assert summary["pending"] == 1
    assert summary["done"] == 1


def test_find_next_step_skips_planning() -> None:
    """Test that find_next_step skips steps with planning status."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            steps=[
                RoadmapStep(
                    id="1.1", description="Planning", status="planning", plan=None, pr="#200"
                ),
                RoadmapStep(id="1.2", description="Pending", status="pending", plan=None, pr=None),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is not None
    assert result["id"] == "1.2"


def test_find_next_step_all_planning_returns_none() -> None:
    """Test that find_next_step returns None when only planning steps remain."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            steps=[
                RoadmapStep(id="1.1", description="Done", status="done", plan=None, pr="#1"),
                RoadmapStep(
                    id="1.2", description="Planning", status="planning", plan=None, pr="#200"
                ),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is None
