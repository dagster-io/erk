"""Unit tests for list_cmd helper functions (_compute_slug, _compute_enriched_fields)."""

from datetime import UTC, datetime

from erk.cli.commands.objective.list_cmd import _compute_enriched_fields, _compute_slug
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
