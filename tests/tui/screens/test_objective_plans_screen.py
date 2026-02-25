"""Tests for ObjectivePlansScreen formatting and behavior."""

from erk.tui.screens.objective_plans_screen import (
    _extract_plan_ids_from_roadmap,
)


def _make_roadmap_body(nodes_yaml: str) -> str:
    """Build a minimal objective body with roadmap metadata block.

    Args:
        nodes_yaml: YAML string for the nodes section (indented by caller)

    Returns:
        Complete objective body with roadmap metadata block
    """
    return (
        "# Objective: Test\n\n"
        "### Phase 1: Foundation\n\n"
        "<!-- erk:metadata-block:objective-roadmap -->\n"
        "<details>\n"
        "<summary><code>objective-roadmap</code></summary>\n\n"
        "```yaml\n"
        "schema_version: '4'\n"
        "nodes:\n"
        f"{nodes_yaml}"
        "```\n\n"
        "</details>\n"
        "<!-- /erk:metadata-block:objective-roadmap -->\n"
    )


def test_extract_plan_ids_empty_body() -> None:
    """Empty body returns empty set."""
    result = _extract_plan_ids_from_roadmap("")
    assert result == set()


def test_extract_plan_ids_no_roadmap_block() -> None:
    """Body without roadmap metadata returns empty set."""
    result = _extract_plan_ids_from_roadmap("# Objective: Test\n\nSome text.")
    assert result == set()


def test_extract_plan_ids_single_pr() -> None:
    """Single node with pr field extracts one ID."""
    body = _make_roadmap_body(
        "- id: '1.1'\n"
        "  slug: setup\n"
        "  description: Setup\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#100'\n"
        "  depends_on: []\n"
    )
    result = _extract_plan_ids_from_roadmap(body)
    assert result == {100}


def test_extract_plan_ids_multiple_prs() -> None:
    """Multiple nodes with pr fields extracts all IDs."""
    body = _make_roadmap_body(
        "- id: '1.1'\n"
        "  slug: step-one\n"
        "  description: Step one\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#100'\n"
        "  depends_on: []\n"
        "- id: '1.2'\n"
        "  slug: step-two\n"
        "  description: Step two\n"
        "  status: done\n"
        "  plan: null\n"
        "  pr: '#200'\n"
        "  depends_on: ['1.1']\n"
        "- id: '1.3'\n"
        "  slug: step-three\n"
        "  description: Step three\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "  depends_on: ['1.2']\n"
    )
    result = _extract_plan_ids_from_roadmap(body)
    assert result == {100, 200}


def test_extract_plan_ids_null_pr_skipped() -> None:
    """Nodes with null pr are not included."""
    body = _make_roadmap_body(
        "- id: '1.1'\n"
        "  slug: pending-step\n"
        "  description: Pending step\n"
        "  status: pending\n"
        "  plan: null\n"
        "  pr: null\n"
        "  depends_on: []\n"
    )
    result = _extract_plan_ids_from_roadmap(body)
    assert result == set()
