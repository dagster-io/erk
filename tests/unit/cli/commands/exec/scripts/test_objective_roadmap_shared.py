"""Unit tests for objective_roadmap_shared module."""

from erk.cli.commands.exec.scripts.objective_roadmap_shared import (
    RoadmapPhase,
    RoadmapStep,
    compute_summary,
    find_next_step,
    parse_roadmap,
    serialize_phases,
)

WELL_FORMED_BODY = """# Objective: Test

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


def test_parse_roadmap_well_formed() -> None:
    """Test parsing a well-formed roadmap body."""
    phases, errors = parse_roadmap(WELL_FORMED_BODY)

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


def test_parse_roadmap_sub_phases() -> None:
    """Test parsing sub-phase headers like Phase 1A, Phase 1B."""
    body = """## Roadmap

### Phase 1A: First Part

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1A.1 | Step one | - | - |

### Phase 1B: Second Part

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1B.1 | Step two | - | - |

### Phase 2: Core

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Step three | - | - |
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


def test_parse_roadmap_status_inference() -> None:
    """Test that statuses are correctly inferred from PR and status columns."""
    phases, _ = parse_roadmap(WELL_FORMED_BODY)
    steps = phases[0].steps + phases[1].steps

    assert steps[0].status == "done"  # #100
    assert steps[1].status == "in_progress"  # plan #101
    assert steps[2].status == "pending"  # -
    assert steps[3].status == "blocked"  # status column
    assert steps[4].status == "skipped"  # status column


def test_parse_roadmap_pr_values() -> None:
    """Test that PR values are parsed correctly."""
    phases, _ = parse_roadmap(WELL_FORMED_BODY)
    steps = phases[0].steps

    assert steps[0].pr == "#100"
    assert steps[1].pr == "plan #101"
    assert steps[2].pr is None  # dash means no PR


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
                RoadmapStep(
                    id="1.1",
                    description="A",
                    status="done",
                    pr="#1",
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
                RoadmapStep(
                    id="1.2",
                    description="B",
                    status="pending",
                    pr=None,
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
                RoadmapStep(
                    id="1.3",
                    description="C",
                    status="in_progress",
                    pr="plan #2",
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
                RoadmapStep(
                    id="1.4",
                    description="D",
                    status="blocked",
                    pr=None,
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
                RoadmapStep(
                    id="1.5",
                    description="E",
                    status="skipped",
                    pr=None,
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
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
                RoadmapStep(
                    id="1.1",
                    description="A",
                    status="done",
                    pr="#1",
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
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
    assert result[0]["steps"][0]["pr"] == "#1"
    assert result[0]["steps"][0]["step_type"] == "plan"
    assert result[0]["steps"][0]["issue"] is None
    assert result[0]["steps"][0]["depends_on"] == []


def test_find_next_step_returns_first_pending() -> None:
    """Test that find_next_step returns the first pending step."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            steps=[
                RoadmapStep(
                    id="1.1",
                    description="Done",
                    status="done",
                    pr="#1",
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
                RoadmapStep(
                    id="1.2",
                    description="Pending",
                    status="pending",
                    pr=None,
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
                RoadmapStep(
                    id="1.3",
                    description="Also pending",
                    status="pending",
                    pr=None,
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is not None
    assert result["id"] == "1.2"
    assert result["phase"] == "Phase One"
    assert result["step_type"] == "plan"


def test_find_next_step_returns_none_when_all_done() -> None:
    """Test that find_next_step returns None when no pending steps exist."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Done",
            steps=[
                RoadmapStep(
                    id="1.1",
                    description="A",
                    status="done",
                    pr="#1",
                    step_type="plan",
                    issue=None,
                    depends_on=[],
                ),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is None


def test_parse_roadmap_explicit_done_status() -> None:
    """Test that explicit 'done' status in Status column is recognized."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Step one | done | #100 |
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

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Step one | in-progress | plan #101 |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].status == "in_progress"
    assert phases[0].steps[0].pr == "plan #101"


def test_parse_roadmap_explicit_pending_status() -> None:
    """Test that explicit 'pending' status in Status column is recognized."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Step one | pending | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 1
    assert phases[0].steps[0].status == "pending"
    assert phases[0].steps[0].pr is None


def test_parse_roadmap_explicit_status_overrides_pr_inference() -> None:
    """Test that explicit status values take priority over PR-based inference."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Explicit done | done | #100 |
| 1.2 | Explicit in-progress | in-progress | plan #101 |
| 1.3 | Fallback to inference | - | #102 |
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


def test_parse_roadmap_7col_format() -> None:
    """Test parsing a 7-column roadmap table."""
    body = """## Roadmap

### Phase 1: Setup

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Setup infra | plan | #6630 | - | - | #6631 |
| 1.2 | Add module | objective | #7001 | - | pending | - |
| 1.3 | Wire together | plan | - | 1.1, 1.2 | pending | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 3

    # Check step 1.1
    assert phases[0].steps[0].id == "1.1"
    assert phases[0].steps[0].description == "Setup infra"
    assert phases[0].steps[0].step_type == "plan"
    assert phases[0].steps[0].issue == "#6630"
    assert phases[0].steps[0].depends_on == []
    assert phases[0].steps[0].status == "done"  # inferred from #6631
    assert phases[0].steps[0].pr == "#6631"

    # Check step 1.2
    assert phases[0].steps[1].id == "1.2"
    assert phases[0].steps[1].description == "Add module"
    assert phases[0].steps[1].step_type == "objective"
    assert phases[0].steps[1].issue == "#7001"
    assert phases[0].steps[1].depends_on == []
    assert phases[0].steps[1].status == "pending"
    assert phases[0].steps[1].pr is None

    # Check step 1.3
    assert phases[0].steps[2].id == "1.3"
    assert phases[0].steps[2].description == "Wire together"
    assert phases[0].steps[2].step_type == "plan"
    assert phases[0].steps[2].issue is None
    assert phases[0].steps[2].depends_on == ["1.1", "1.2"]
    assert phases[0].steps[2].status == "pending"
    assert phases[0].steps[2].pr is None


def test_parse_roadmap_4col_backwards_compatibility() -> None:
    """Test that 4-column tables parse with default values for new fields."""
    body = """## Roadmap

### Phase 1: Foundation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Setup infra | - | #100 |
| 1.2 | Add tests | - | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 2

    # Check defaults for 4-column format
    assert phases[0].steps[0].step_type == "plan"
    assert phases[0].steps[0].issue is None
    assert phases[0].steps[0].depends_on == []

    assert phases[0].steps[1].step_type == "plan"
    assert phases[0].steps[1].issue is None
    assert phases[0].steps[1].depends_on == []


def test_parse_roadmap_7col_status_inference() -> None:
    """Test that 7-column format correctly infers status from PR column."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | Done step | plan | - | - | - | #100 |
| 1.2 | In progress | plan | - | - | - | plan #101 |
| 1.3 | Pending step | plan | - | - | - | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert len(phases) == 1
    assert len(phases[0].steps) == 3

    assert phases[0].steps[0].status == "done"
    assert phases[0].steps[1].status == "in_progress"
    assert phases[0].steps[2].status == "pending"


def test_parse_roadmap_7col_empty_depends_on() -> None:
    """Test that dash and empty in Depends On yields empty list."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | With dash | plan | - | - | pending | - |
| 1.2 | With empty | plan | - |  | pending | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert phases[0].steps[0].depends_on == []
    assert phases[0].steps[1].depends_on == []


def test_parse_roadmap_7col_empty_issue() -> None:
    """Test that dash and empty in Issue yields None."""
    body = """## Roadmap

### Phase 1: Test

| Step | Description | Type | Issue | Depends On | Status | PR |
|------|-------------|------|-------|------------|--------|-----|
| 1.1 | With dash | plan | - | - | pending | - |
| 1.2 | With empty | plan |  | - | pending | - |
"""
    phases, errors = parse_roadmap(body)

    assert errors == []
    assert phases[0].steps[0].issue is None
    assert phases[0].steps[1].issue is None


def test_serialize_phases_includes_new_fields() -> None:
    """Test that serialize includes step_type, issue, and depends_on fields."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            steps=[
                RoadmapStep(
                    id="1.1",
                    description="Setup",
                    status="done",
                    pr="#100",
                    step_type="plan",
                    issue="#6630",
                    depends_on=["1.0"],
                ),
                RoadmapStep(
                    id="1.2",
                    description="Module",
                    status="pending",
                    pr=None,
                    step_type="objective",
                    issue="#7001",
                    depends_on=[],
                ),
            ],
        )
    ]
    result = serialize_phases(phases)

    assert len(result) == 1
    assert len(result[0]["steps"]) == 2

    assert result[0]["steps"][0]["step_type"] == "plan"
    assert result[0]["steps"][0]["issue"] == "#6630"
    assert result[0]["steps"][0]["depends_on"] == ["1.0"]

    assert result[0]["steps"][1]["step_type"] == "objective"
    assert result[0]["steps"][1]["issue"] == "#7001"
    assert result[0]["steps"][1]["depends_on"] == []
