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

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | - | - | #100 |
| 1.2 | Add tests | - | #101 | - |
| 1.3 | Update docs | - | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build feature | blocked | - | - |
| 2.2 | Performance | skipped | - | - |
"""

WELL_FORMED_BODY_4COL = """# Objective: Test

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Setup infra | - | #100 |
| 1.2 | Add tests | - | plan #101 |
| 1.3 | Update docs | - | - |

### Phase 2: Core

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Build feature | blocked | - |
| 2.2 | Performance | skipped | - |
"""


def test_parse_roadmap_5col_well_formed() -> None:
    """Test parsing a well-formed 5-col roadmap body."""
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
    """Test that plan and PR values are parsed correctly from 5-col tables."""
    phases, _ = parse_roadmap(WELL_FORMED_BODY_5COL)
    steps = phases[0].steps

    assert steps[0].plan is None
    assert steps[0].pr == "#100"
    assert steps[1].plan == "#101"
    assert steps[1].pr is None
    assert steps[2].plan is None
    assert steps[2].pr is None


def test_parse_roadmap_5col_status_inference() -> None:
    """Test that statuses are correctly inferred from plan/PR columns."""
    phases, _ = parse_roadmap(WELL_FORMED_BODY_5COL)
    steps = phases[0].steps + phases[1].steps

    assert steps[0].status == "done"  # PR #100
    assert steps[1].status == "in_progress"  # plan #101
    assert steps[2].status == "pending"  # no refs
    assert steps[3].status == "blocked"  # explicit status
    assert steps[4].status == "skipped"  # explicit status


def test_parse_roadmap_4col_backward_compat() -> None:
    """Test that 4-col tables parse correctly with plan migration."""
    phases, errors = parse_roadmap(WELL_FORMED_BODY_4COL)

    assert len(phases) == 2
    assert errors == []

    steps = phases[0].steps
    # "plan #101" in PR column → plan="#101", pr=None
    assert steps[1].plan == "#101"
    assert steps[1].pr is None
    assert steps[1].status == "in_progress"

    # "#100" in PR column stays as pr
    assert steps[0].plan is None
    assert steps[0].pr == "#100"
    assert steps[0].status == "done"


def test_parse_roadmap_sub_phases() -> None:
    """Test parsing sub-phase headers like Phase 1A, Phase 1B."""
    body = """## Roadmap

### Phase 1A: First Part

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1A.1 | Step one | - | - | - |

### Phase 1B: Second Part

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1B.1 | Step two | - | - | - |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Step three | - | - | - |
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
    """Test parsing body with no phase headers."""
    phases, errors = parse_roadmap("No roadmap here.")

    assert phases == []
    assert len(errors) == 1
    assert "No phase headers found" in errors[0]


def test_parse_roadmap_missing_table() -> None:
    """Test parsing a phase with no table produces validation error."""
    body = """### Phase 1: No Table

Just some prose here.
"""
    phases, errors = parse_roadmap(body)

    assert phases == []
    assert any("missing roadmap table" in e for e in errors)


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
    """Test that explicit 'done' status in Status column is recognized."""
    body = """## Roadmap

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
    """Test that explicit 'in-progress' status in Status column is recognized."""
    body = """## Roadmap

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
    """Test that explicit 'pending' status in Status column is recognized."""
    body = """## Roadmap

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
    """Test that explicit status values take priority over column inference."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Explicit done | done | - | #100 |
| 1.2 | Explicit in-progress | in-progress | #101 | - |
| 1.3 | Fallback to inference | - | - | #102 |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 3
    # Explicit statuses should be preserved
    assert phases[0].steps[0].status == "done"
    assert phases[0].steps[1].status == "in_progress"
    # Legacy "-" should fall back to PR inference
    assert phases[0].steps[2].status == "done"


def test_parse_roadmap_frontmatter_preferred() -> None:
    """Test that frontmatter is used when metadata block is present."""
    body = """## Objective

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "1"
steps:
  - id: "1.1"
    description: "From frontmatter"
    status: "done"
    pr: "#999"
  - id: "1.2"
    description: "Also from frontmatter"
    status: "pending"
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


def test_parse_roadmap_no_frontmatter_fallback() -> None:
    """Test that table parsing works when no frontmatter is present."""
    # WELL_FORMED_BODY_5COL has no metadata block
    phases, errors = parse_roadmap(WELL_FORMED_BODY_5COL)

    # Should fall back to table parsing
    assert errors == []
    assert len(phases) == 2
    assert phases[0].name == "Foundation"
    assert len(phases[0].steps) == 3
    # Values come from table
    assert phases[0].steps[0].pr == "#100"
    assert phases[0].steps[1].plan == "#101"


def test_parse_roadmap_invalid_frontmatter_fallback() -> None:
    """Test that invalid frontmatter falls back to table parsing."""
    body = """## Objective

<!-- erk:metadata-block:objective-roadmap -->
---
invalid: yaml: syntax [
---
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Fallback Phase

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | From table | - | - | #200 |
"""

    phases, errors = parse_roadmap(body)

    # Should fall back to table parsing when frontmatter is invalid
    assert errors == []
    assert len(phases) == 1
    assert phases[0].name == "Fallback Phase"
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].pr == "#200"


def test_parse_roadmap_v1_frontmatter_migrates_plan() -> None:
    """Test that v1 frontmatter migrates 'plan #NNN' from pr to plan field."""
    body = """## Objective

<!-- erk:metadata-block:objective-roadmap -->
---
schema_version: "1"
steps:
  - id: "1.1"
    description: "Has plan ref"
    status: "in_progress"
    pr: "plan #6464"
  - id: "1.2"
    description: "Has real PR"
    status: "done"
    pr: "#999"
---
<!-- /erk:metadata-block:objective-roadmap -->

### Phase 1: Test

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Ignored | - | - | - |
| 1.2 | Ignored | - | - | - |
"""

    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    # "plan #6464" migrated → plan="#6464", pr=None
    assert phases[0].steps[0].plan == "#6464"
    assert phases[0].steps[0].pr is None
    # "#999" stays as pr
    assert phases[0].steps[1].plan is None
    assert phases[0].steps[1].pr == "#999"
