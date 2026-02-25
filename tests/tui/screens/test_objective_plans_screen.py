"""Tests for ObjectivePlansScreen formatting and behavior."""

from erk.tui.screens.objective_plans_screen import (
    _extract_plan_ids_from_roadmap,
    _format_plan_rows,
)
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


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


def test_format_plan_rows_empty_list() -> None:
    """Empty list returns no formatted lines."""
    result = _format_plan_rows([])
    assert result == []


def test_format_plan_rows_plan_without_pr() -> None:
    """Plan without PR shows only plan ID and title."""
    row = make_plan_row(7911, "Delete issue plan backend")
    result = _format_plan_rows([row])
    assert len(result) == 1
    assert "#7911" in result[0]
    assert "Delete issue plan backend" in result[0]
    assert "PR" not in result[0]


def test_format_plan_rows_plan_with_pr() -> None:
    """Plan with PR shows plan ID, title, PR display, and state."""
    row = make_plan_row(
        7911,
        "Delete issue plan backend",
        pr_number=8141,
        pr_state="OPEN",
    )
    result = _format_plan_rows([row])
    assert len(result) == 1
    assert "#7911" in result[0]
    assert "Delete issue plan backend" in result[0]
    assert "PR #8141" in result[0]
    assert "OPEN" in result[0]


def test_format_plan_rows_multiple_plans() -> None:
    """Multiple plans each get their own formatted line."""
    rows = [
        make_plan_row(7911, "Delete issue plan backend", pr_number=8141, pr_state="OPEN"),
        make_plan_row(7813, "Eliminate git checkouts", pr_number=7991, pr_state="MERGED"),
        make_plan_row(7724, "Rename issue to plan"),
    ]
    result = _format_plan_rows(rows)
    assert len(result) == 3
    assert "#7911" in result[0]
    assert "#7813" in result[1]
    assert "#7724" in result[2]


def test_format_plan_rows_plan_with_pr_no_state() -> None:
    """Plan with PR but no state omits state display."""
    row = make_plan_row(
        7911,
        "Some plan",
        pr_number=8141,
    )
    result = _format_plan_rows([row])
    assert len(result) == 1
    assert "PR #8141" in result[0]
    # pr_state is None, so no state suffix
    assert "OPEN" not in result[0]
    assert "MERGED" not in result[0]
