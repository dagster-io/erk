"""Unit tests for list_cmd helper functions."""

from datetime import UTC, datetime

from erk.cli.commands.objective.list_cmd import (
    _compute_enriched_fields,
    _compute_next_node_fields,
    _compute_slug,
)
from erk_shared.gateway.github.metadata.dependency_graph import (
    DependencyGraph,
    ObjectiveNode,
)
from erk_shared.gateway.github.metadata.roadmap import RoadmapNode, RoadmapPhase
from erk_shared.plan_store.types import Plan, PlanState

NOW = datetime.now(UTC)


def _make_plan(
    *,
    title: str = "Objective: Test",
    body: str = "",
) -> Plan:
    return Plan(
        plan_identifier="1",
        title=title,
        body=body,
        state=PlanState.OPEN,
        url="https://github.com/test/repo/issues/1",
        labels=["erk-objective"],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        metadata={"author": "testuser"},
        objective_id=None,
    )


HEADER_WITH_SLUG = """\
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml
created_at: '2025-01-01T00:00:00+00:00'
created_by: testuser
slug: enrich-objective-list
```

</details>
<!-- /erk:metadata-block:objective-header -->
"""

HEADER_WITHOUT_SLUG = """\
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml
created_at: '2025-01-01T00:00:00+00:00'
created_by: testuser
```

</details>
<!-- /erk:metadata-block:objective-header -->
"""

ROADMAP_BLOCK = """\
<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infrastructure
  status: done
  plan: null
  pr: '#100'
- id: '1.2'
  description: Add basic tests
  status: pending
  plan: null
  pr: null
  depends_on:
  - '1.1'
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


# --- _compute_slug tests ---


def test_compute_slug_extracts_from_body() -> None:
    plan = _make_plan(body=HEADER_WITH_SLUG)
    assert _compute_slug(plan) == "enrich-objective-list"


def test_compute_slug_truncates_long_slug() -> None:
    long_slug = "a-very-long-slug-that-exceeds-the-limit"
    body = HEADER_WITH_SLUG.replace("enrich-objective-list", long_slug)
    plan = _make_plan(body=body)
    assert len(_compute_slug(plan)) <= 25


def test_compute_slug_falls_back_to_title_without_prefix() -> None:
    plan = _make_plan(title="Objective: My Cool Feature", body=HEADER_WITHOUT_SLUG)
    assert _compute_slug(plan) == "My Cool Feature"


def test_compute_slug_falls_back_to_title_no_body() -> None:
    plan = _make_plan(title="Objective: Something", body="")
    assert _compute_slug(plan) == "Something"


def test_compute_slug_returns_dash_for_empty() -> None:
    plan = _make_plan(title="", body="")
    assert _compute_slug(plan) == "-"


# --- _compute_enriched_fields tests ---


def test_enriched_fields_no_body() -> None:
    plan = _make_plan(body="")
    fields = _compute_enriched_fields(plan)
    assert fields["progress"] == "-"
    assert fields["state"] == "-"
    assert fields["deps_state"] == "-"
    assert fields["deps"] == "-"
    assert fields["next_node"] == "-"


def test_enriched_fields_body_no_roadmap() -> None:
    plan = _make_plan(body="Just some text without a roadmap block.")
    fields = _compute_enriched_fields(plan)
    assert fields["progress"] == "-"
    assert fields["state"] == "-"


def test_enriched_fields_valid_roadmap() -> None:
    body = HEADER_WITH_SLUG + "\n" + ROADMAP_BLOCK
    plan = _make_plan(body=body)
    fields = _compute_enriched_fields(plan)
    assert fields["progress"] == "1/2"
    assert fields["state"] != "-"
    assert fields["next_node"] == "1.2"
    assert fields["deps_state"] == "ready"


# --- _compute_next_node_fields tests ---


def _make_node(
    *,
    id: str,
    status: str = "pending",
    pr: str | None = None,
    depends_on: tuple[str, ...] = (),
) -> ObjectiveNode:
    return ObjectiveNode(
        id=id,
        description=f"Node {id}",
        status=status,
        pr=pr,
        depends_on=depends_on,
        slug=None,
    )


def _make_phases_from_nodes(nodes: list[RoadmapNode]) -> list[RoadmapPhase]:
    return [RoadmapPhase(number=1, suffix="", name="Phase 1", nodes=nodes)]


def _roadmap_node(
    *,
    id: str,
    status: str = "pending",
    pr: str | None = None,
    depends_on: tuple[str, ...] | None = None,
) -> RoadmapNode:
    return RoadmapNode(
        id=id,
        description=f"Node {id}",
        status=status,
        pr=pr,
        depends_on=depends_on,
        slug=None,
    )


def test_next_node_fields_no_next_result() -> None:
    """All nodes done => no next node, returns dashes."""
    nodes = (_make_node(id="1.1", status="done"),)
    graph = DependencyGraph(nodes=nodes)
    phases = _make_phases_from_nodes([_roadmap_node(id="1.1", status="done")])

    next_node, deps_state, deps = _compute_next_node_fields(graph, phases)

    assert next_node == "-"
    assert deps_state == "-"
    assert deps == "-"


def test_next_node_fields_ready_deps() -> None:
    """Next node has deps all done => deps_state is 'ready'."""
    nodes = (
        _make_node(id="1.1", status="done"),
        _make_node(id="1.2", status="pending", depends_on=("1.1",)),
    )
    graph = DependencyGraph(nodes=nodes)
    phases = _make_phases_from_nodes([
        _roadmap_node(id="1.1", status="done"),
        _roadmap_node(id="1.2", status="pending", depends_on=("1.1",)),
    ])

    next_node, deps_state, deps = _compute_next_node_fields(graph, phases)

    assert next_node == "1.2"
    assert deps_state == "ready"
    assert deps == "-"


def test_next_node_fields_blocking_dep_with_pr() -> None:
    """Next node has an in_progress dep with a PR => deps shows the PR."""
    nodes = (
        _make_node(id="1.1", status="in_progress", pr="#200"),
        _make_node(id="1.2", status="pending", depends_on=("1.1",)),
    )
    graph = DependencyGraph(nodes=nodes)
    phases = _make_phases_from_nodes([
        _roadmap_node(id="1.1", status="in_progress", pr="#200"),
        _roadmap_node(id="1.2", status="pending", depends_on=("1.1",)),
    ])

    next_node, deps_state, deps = _compute_next_node_fields(graph, phases)

    assert next_node == "1.2"
    assert deps_state == "in progress"
    assert "#200" in deps


def test_next_node_fields_own_pr_shown() -> None:
    """Next node's own active PR is included in deps."""
    nodes = (
        _make_node(id="1.1", status="done"),
        _make_node(id="1.2", status="in_progress", pr="#300", depends_on=("1.1",)),
    )
    graph = DependencyGraph(nodes=nodes)
    phases = _make_phases_from_nodes([
        _roadmap_node(id="1.1", status="done"),
        _roadmap_node(id="1.2", status="in_progress", pr="#300", depends_on=("1.1",)),
    ])

    next_node, deps_state, deps = _compute_next_node_fields(graph, phases)

    assert next_node == "1.2"
    assert "#300" in deps
