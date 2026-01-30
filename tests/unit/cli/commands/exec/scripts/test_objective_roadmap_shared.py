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
    assert phases[0].name == "Foundation"
    assert len(phases[0].steps) == 3

    assert phases[1].number == 2
    assert phases[1].name == "Core"
    assert len(phases[1].steps) == 2


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
            name="Test",
            steps=[
                RoadmapStep(id="1.1", description="A", status="done", pr="#1"),
                RoadmapStep(id="1.2", description="B", status="pending", pr=None),
                RoadmapStep(id="1.3", description="C", status="in_progress", pr="plan #2"),
                RoadmapStep(id="1.4", description="D", status="blocked", pr=None),
                RoadmapStep(id="1.5", description="E", status="skipped", pr=None),
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
            name="Test",
            steps=[
                RoadmapStep(id="1.1", description="A", status="done", pr="#1"),
            ],
        )
    ]
    result = serialize_phases(phases)

    assert len(result) == 1
    assert result[0]["number"] == 1
    assert result[0]["name"] == "Test"
    assert len(result[0]["steps"]) == 1
    assert result[0]["steps"][0]["id"] == "1.1"
    assert result[0]["steps"][0]["status"] == "done"
    assert result[0]["steps"][0]["pr"] == "#1"


def test_find_next_step_returns_first_pending() -> None:
    """Test that find_next_step returns the first pending step."""
    phases = [
        RoadmapPhase(
            number=1,
            name="Phase One",
            steps=[
                RoadmapStep(id="1.1", description="Done", status="done", pr="#1"),
                RoadmapStep(id="1.2", description="Pending", status="pending", pr=None),
                RoadmapStep(id="1.3", description="Also pending", status="pending", pr=None),
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
            name="Done",
            steps=[
                RoadmapStep(id="1.1", description="A", status="done", pr="#1"),
            ],
        )
    ]
    result = find_next_step(phases)

    assert result is None
