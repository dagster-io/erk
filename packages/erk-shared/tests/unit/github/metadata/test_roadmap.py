"""Unit tests for roadmap parsing, utility functions, and table rendering."""

from erk_shared.gateway.github.metadata.roadmap import (
    RoadmapNode,
    RoadmapPhase,
    compute_summary,
    find_next_node,
    parse_roadmap,
    parse_v2_roadmap,
    render_roadmap_block_inner,
    render_roadmap_tables,
    serialize_phases,
    validate_roadmap_frontmatter,
)

WELL_FORMED_V2_BODY = """\
# Objective: Test

## Roadmap

### Phase 1: Foundation

### Phase 2: Core

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infra
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Add tests
  status: in_progress
  plan: '#101'
  pr: null
- id: '1.3'
  description: Update docs
  status: pending
  plan: null
  pr: null
- id: '2.1'
  description: Build feature
  status: blocked
  plan: null
  pr: null
- id: '2.2'
  description: Performance
  status: skipped
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


def test_parse_roadmap_v2_well_formed() -> None:
    """Test parsing a well-formed v2 roadmap body."""
    phases, errors = parse_roadmap(WELL_FORMED_V2_BODY)

    assert len(phases) == 2
    assert errors == []

    assert phases[0].number == 1
    assert phases[0].suffix == ""
    assert phases[0].name == "Foundation"
    assert len(phases[0].nodes) == 3

    assert phases[1].number == 2
    assert phases[1].suffix == ""
    assert phases[1].name == "Core"
    assert len(phases[1].nodes) == 2


def test_parse_roadmap_v2_plan_and_pr_values() -> None:
    """Test that plan and PR values are parsed correctly from v2 frontmatter."""
    phases, _ = parse_roadmap(WELL_FORMED_V2_BODY)
    steps = phases[0].nodes

    assert steps[0].plan is None
    assert steps[0].pr == "#100"
    assert steps[1].plan == "#101"
    assert steps[1].pr is None
    assert steps[2].plan is None
    assert steps[2].pr is None


def test_parse_roadmap_v2_statuses() -> None:
    """Test that statuses are correctly read from v2 frontmatter."""
    phases, _ = parse_roadmap(WELL_FORMED_V2_BODY)
    steps = phases[0].nodes + phases[1].nodes

    assert steps[0].status == "done"  # PR #100
    assert steps[1].status == "in_progress"  # plan #101
    assert steps[2].status == "pending"  # no refs
    assert steps[3].status == "blocked"  # explicit status
    assert steps[4].status == "skipped"  # explicit status


def test_parse_roadmap_sub_phases() -> None:
    """Test parsing sub-phase headers like Phase 1A, Phase 1B."""
    body = """\
## Roadmap

### Phase 1A: First Part

### Phase 1B: Second Part

### Phase 2: Core

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: 1A.1
  description: Step one
  status: pending
  plan: null
  pr: null
- id: 1B.1
  description: Step two
  status: pending
  plan: null
  pr: null
- id: '2.1'
  description: Step three
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
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


def test_parse_roadmap_no_metadata_block() -> None:
    """Test parsing body with no metadata block returns legacy format error."""
    phases, errors = parse_roadmap("No roadmap here.")

    assert phases == []
    assert len(errors) == 1
    assert "legacy format" in errors[0]


def test_parse_roadmap_invalid_frontmatter() -> None:
    """Test that invalid frontmatter in metadata block returns legacy format error."""
    body = """\
## Objective

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
invalid: yaml: syntax [
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

    phases, errors = parse_roadmap(body)

    # Invalid YAML inside <details> → parse_roadmap_frontmatter returns None → legacy error
    assert phases == []
    assert len(errors) == 1
    assert "legacy format" in errors[0]


def test_parse_roadmap_legacy_format_returns_error() -> None:
    """Test that legacy --- format metadata block returns legacy format error."""
    body = """\
## Objective

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
"""

    phases, errors = parse_roadmap(body)

    # Has metadata block but in legacy --- format → parse_roadmap_frontmatter returns None
    assert phases == []
    assert len(errors) == 1
    assert "legacy format" in errors[0]


def test_compute_summary() -> None:
    """Test summary computation from phases."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            nodes=[
                RoadmapNode(id="1.1", description="A", status="done", plan=None, pr="#1"),
                RoadmapNode(id="1.2", description="B", status="pending", plan=None, pr=None),
                RoadmapNode(id="1.3", description="C", status="in_progress", plan="#2", pr=None),
                RoadmapNode(id="1.4", description="D", status="blocked", plan=None, pr=None),
                RoadmapNode(id="1.5", description="E", status="skipped", plan=None, pr=None),
            ],
        )
    ]
    summary = compute_summary(phases)

    assert summary["total_nodes"] == 5
    assert summary["done"] == 1
    assert summary["pending"] == 1
    assert summary["in_progress"] == 1
    assert summary["blocked"] == 1
    assert summary["skipped"] == 1


def test_compute_summary_empty() -> None:
    """Test summary computation with no phases."""
    summary = compute_summary([])

    assert summary["total_nodes"] == 0
    assert summary["done"] == 0


def test_serialize_phases() -> None:
    """Test serialization of phases to JSON-compatible dicts."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            nodes=[
                RoadmapNode(id="1.1", description="A", status="done", plan=None, pr="#1"),
            ],
        )
    ]
    result = serialize_phases(phases)

    assert len(result) == 1
    assert result[0]["number"] == 1
    assert result[0]["suffix"] == ""
    assert result[0]["name"] == "Test"
    assert len(result[0]["nodes"]) == 1
    assert result[0]["nodes"][0]["id"] == "1.1"
    assert result[0]["nodes"][0]["status"] == "done"
    assert result[0]["nodes"][0]["plan"] is None
    assert result[0]["nodes"][0]["pr"] == "#1"


def test_find_next_node_returns_first_pending() -> None:
    """Test that find_next_node returns the first pending node."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            nodes=[
                RoadmapNode(id="1.1", description="Done", status="done", plan=None, pr="#1"),
                RoadmapNode(id="1.2", description="Pending", status="pending", plan=None, pr=None),
                RoadmapNode(
                    id="1.3", description="Also pending", status="pending", plan=None, pr=None
                ),
            ],
        )
    ]
    result = find_next_node(phases)

    assert result is not None
    assert result["id"] == "1.2"
    assert result["phase"] == "Phase One"


def test_find_next_node_returns_none_when_all_done() -> None:
    """Test that find_next_node returns None when no pending nodes exist."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Done",
            nodes=[
                RoadmapNode(id="1.1", description="A", status="done", plan=None, pr="#1"),
            ],
        )
    ]
    result = find_next_node(phases)

    assert result is None


def test_compute_summary_counts_planning() -> None:
    """Test that compute_summary counts planning steps."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Test",
            nodes=[
                RoadmapNode(id="1.1", description="A", status="planning", plan=None, pr="#200"),
                RoadmapNode(id="1.2", description="B", status="pending", plan=None, pr=None),
                RoadmapNode(id="1.3", description="C", status="done", plan=None, pr="#1"),
            ],
        )
    ]
    summary = compute_summary(phases)

    assert summary["total_nodes"] == 3
    assert summary["planning"] == 1
    assert summary["pending"] == 1
    assert summary["done"] == 1


def test_find_next_node_skips_planning() -> None:
    """Test that find_next_node skips nodes with planning status."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            nodes=[
                RoadmapNode(
                    id="1.1", description="Planning", status="planning", plan=None, pr="#200"
                ),
                RoadmapNode(id="1.2", description="Pending", status="pending", plan=None, pr=None),
            ],
        )
    ]
    result = find_next_node(phases)

    assert result is not None
    assert result["id"] == "1.2"


def test_find_next_node_all_planning_returns_none() -> None:
    """Test that find_next_node returns None when only planning nodes remain."""
    phases = [
        RoadmapPhase(
            number=1,
            suffix="",
            name="Phase One",
            nodes=[
                RoadmapNode(id="1.1", description="Done", status="done", plan=None, pr="#1"),
                RoadmapNode(
                    id="1.2", description="Planning", status="planning", plan=None, pr="#200"
                ),
            ],
        )
    ]
    result = find_next_node(phases)

    assert result is None


# ---------------------------------------------------------------------------
# parse_v2_roadmap tests
# ---------------------------------------------------------------------------

V2_ROADMAP_BODY = """\
## Objective

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infra
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Add tests
  status: in_progress
  plan: '#101'
  pr: null
- id: '2.1'
  description: Build feature
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

### Phase 1: Foundation

### Phase 2: Core
"""


def test_parse_v2_roadmap_success() -> None:
    """Full v2 body with phases returns (phases, errors)."""
    result = parse_v2_roadmap(V2_ROADMAP_BODY)

    assert result is not None
    phases, errors = result
    assert errors == []
    assert len(phases) == 2

    assert phases[0].number == 1
    assert phases[0].suffix == ""
    assert phases[0].name == "Foundation"
    assert len(phases[0].nodes) == 2
    assert phases[0].nodes[0].id == "1.1"
    assert phases[0].nodes[0].status == "done"
    assert phases[0].nodes[0].pr == "#100"
    assert phases[0].nodes[1].id == "1.2"
    assert phases[0].nodes[1].plan == "#101"

    assert phases[1].number == 2
    assert phases[1].name == "Core"
    assert len(phases[1].nodes) == 1
    assert phases[1].nodes[0].id == "2.1"
    assert phases[1].nodes[0].status == "pending"


def test_parse_v2_roadmap_no_metadata_block() -> None:
    """Body with no objective-roadmap block returns None."""
    body = "# Objective\n\nJust some text, no metadata blocks."

    result = parse_v2_roadmap(body)

    assert result is None


def test_parse_v2_roadmap_no_details_format() -> None:
    """Has metadata block but uses legacy frontmatter (not <details>) returns None."""
    body = """\
## Objective

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
"""

    result = parse_v2_roadmap(body)

    assert result is None


def test_parse_v2_roadmap_wrong_schema_version() -> None:
    """Has <details> block but schema_version '1' returns None."""
    body = """\
## Objective

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '1'
steps:
- id: '1.1'
  description: Step one
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

    result = parse_v2_roadmap(body)

    assert result is None


def test_parse_v2_roadmap_validation_failure() -> None:
    """Has v2 format but invalid step data (missing required field) returns None."""
    body = """\
## Objective

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Step one
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""

    result = parse_v2_roadmap(body)

    assert result is None


# ---------------------------------------------------------------------------
# v3 schema tests (nodes key, schema_version "3")
# ---------------------------------------------------------------------------

WELL_FORMED_V3_BODY = """\
# Objective: Test

## Roadmap

### Phase 1: Foundation

### Phase 2: Core

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '3'
nodes:
- id: '1.1'
  description: Setup infra
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Add tests
  status: in_progress
  plan: '#101'
  pr: null
- id: '2.1'
  description: Build feature
  status: pending
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


def test_parse_roadmap_v3_well_formed() -> None:
    """Test parsing a well-formed v3 roadmap body with 'nodes' key."""
    phases, errors = parse_roadmap(WELL_FORMED_V3_BODY)

    assert len(phases) == 2
    assert errors == []

    assert phases[0].number == 1
    assert phases[0].name == "Foundation"
    assert len(phases[0].steps) == 2

    assert phases[1].number == 2
    assert phases[1].name == "Core"
    assert len(phases[1].steps) == 1


def test_parse_v2_roadmap_accepts_v3() -> None:
    """parse_v2_roadmap accepts v3 schema bodies."""
    result = parse_v2_roadmap(WELL_FORMED_V3_BODY)

    assert result is not None
    phases, errors = result
    assert errors == []
    assert len(phases) == 2


def test_validate_roadmap_frontmatter_v3_nodes_key() -> None:
    """validate_roadmap_frontmatter accepts v3 with 'nodes' key."""
    data = {
        "schema_version": "3",
        "nodes": [
            {"id": "1.1", "description": "Test", "status": "pending", "plan": None, "pr": None},
        ],
    }
    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is not None
    assert errors == []
    assert len(steps) == 1
    assert steps[0].id == "1.1"


def test_validate_roadmap_frontmatter_v2_steps_key_still_works() -> None:
    """validate_roadmap_frontmatter still accepts v2 with 'steps' key."""
    data = {
        "schema_version": "2",
        "steps": [
            {"id": "1.1", "description": "Test", "status": "pending", "plan": None, "pr": None},
        ],
    }
    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is not None
    assert errors == []
    assert len(steps) == 1


def test_validate_roadmap_frontmatter_missing_both_keys() -> None:
    """validate_roadmap_frontmatter fails when neither 'nodes' nor 'steps' present."""
    data = {
        "schema_version": "3",
        "items": [],
    }
    steps, errors = validate_roadmap_frontmatter(data)

    assert steps is None
    assert len(errors) == 1
    assert "nodes" in errors[0]


def test_render_roadmap_block_inner_emits_v3() -> None:
    """render_roadmap_block_inner emits schema_version '3' and 'nodes' key."""
    steps = [
        RoadmapNode(id="1.1", description="Test", status="pending", plan=None, pr=None),
    ]
    result = render_roadmap_block_inner(steps)

    assert "schema_version: '3'" in result
    assert "nodes:" in result
    assert "steps:" not in result


def test_v2_body_round_trips_through_v3_render() -> None:
    """Parsing a v2 body and re-rendering produces v3 output."""
    phases, errors = parse_roadmap(WELL_FORMED_V2_BODY)
    assert errors == []

    all_steps = [step for phase in phases for step in phase.steps]
    rendered = render_roadmap_block_inner(all_steps)

    assert "schema_version: '3'" in rendered
    assert "nodes:" in rendered


# ---------------------------------------------------------------------------
# render_roadmap_tables tests
# ---------------------------------------------------------------------------


class TestRenderRoadmapTables:
    def test_single_phase_basic(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="",
                name="Foundation",
                nodes=[
                    RoadmapNode(id="1.1", description="Setup", status="done", plan=None, pr="#10"),
                    RoadmapNode(
                        id="1.2", description="Build", status="pending", plan=None, pr=None
                    ),
                ],
            )
        ]
        result = render_roadmap_tables(phases)

        assert "### Phase 1: Foundation (1 PR)" in result
        assert "| 1.1 | Setup | done | - | #10 |" in result
        assert "| 1.2 | Build | pending | - | - |" in result

    def test_status_hyphenation(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="",
                name="Test",
                nodes=[
                    RoadmapNode(
                        id="1.1",
                        description="Working",
                        status="in_progress",
                        plan="#50",
                        pr=None,
                    ),
                ],
            )
        ]
        result = render_roadmap_tables(phases)

        assert "in-progress" in result
        assert "in_progress" not in result

    def test_null_values_render_as_dash(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="",
                name="Test",
                nodes=[
                    RoadmapNode(id="1.1", description="Step", status="pending", plan=None, pr=None),
                ],
            )
        ]
        result = render_roadmap_tables(phases)

        assert "| 1.1 | Step | pending | - | - |" in result

    def test_multi_phase(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="",
                name="Foundation",
                nodes=[
                    RoadmapNode(id="1.1", description="A", status="done", plan=None, pr="#1"),
                ],
            ),
            RoadmapPhase(
                number=2,
                suffix="",
                name="Core",
                nodes=[
                    RoadmapNode(id="2.1", description="B", status="pending", plan=None, pr=None),
                ],
            ),
        ]
        result = render_roadmap_tables(phases)

        assert "### Phase 1: Foundation (1 PR)" in result
        assert "### Phase 2: Core (0 PR)" in result

    def test_sub_phase_suffix(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="A",
                name="First Part",
                nodes=[
                    RoadmapNode(
                        id="1A.1", description="Step", status="pending", plan=None, pr=None
                    ),
                ],
            )
        ]
        result = render_roadmap_tables(phases)

        assert "### Phase 1A: First Part (0 PR)" in result

    def test_table_header_format(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="",
                name="Test",
                nodes=[
                    RoadmapNode(id="1.1", description="Step", status="pending", plan=None, pr=None),
                ],
            )
        ]
        result = render_roadmap_tables(phases)
        lines = result.split("\n")

        assert lines[1] == "| Node | Description | Status | Plan | PR |"
        assert lines[2] == "|------|-------------|--------|------|----|"

    def test_plan_and_pr_values(self) -> None:
        phases = [
            RoadmapPhase(
                number=1,
                suffix="",
                name="Test",
                nodes=[
                    RoadmapNode(
                        id="1.1", description="Done", status="done", plan="#100", pr="#200"
                    ),
                ],
            )
        ]
        result = render_roadmap_tables(phases)

        assert "| 1.1 | Done | done | #100 | #200 |" in result
