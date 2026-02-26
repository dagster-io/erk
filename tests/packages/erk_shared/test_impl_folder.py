"""Tests for impl_folder utilities.

Layer 3: Pure unit tests (zero dependencies).
"""

import json


def test_build_plan_ref_json_structure() -> None:
    """Verify build_plan_ref_json returns valid JSON with all required fields."""
    from erk_shared.impl_folder import build_plan_ref_json

    result = build_plan_ref_json(
        provider="github",
        plan_id="42",
        url="https://github.com/owner/repo/issues/42",
        labels=("erk-plan", "bug"),
        objective_id=100,
        node_ids=None,
    )

    data = json.loads(result)

    assert data["provider"] == "github"
    assert data["plan_id"] == "42"
    assert data["url"] == "https://github.com/owner/repo/issues/42"
    assert data["labels"] == ["erk-plan", "bug"]
    assert data["objective_id"] == 100
    assert "created_at" in data
    assert "synced_at" in data
    # created_at and synced_at should be equal (both set to now)
    assert data["created_at"] == data["synced_at"]


def test_build_plan_ref_json_none_objective() -> None:
    """Verify build_plan_ref_json handles None objective_id."""
    from erk_shared.impl_folder import build_plan_ref_json

    result = build_plan_ref_json(
        provider="github-draft-pr",
        plan_id="789",
        url="https://github.com/owner/repo/pull/789",
        labels=(),
        objective_id=None,
        node_ids=None,
    )

    data = json.loads(result)

    assert data["provider"] == "github-draft-pr"
    assert data["objective_id"] is None
    assert data["labels"] == []
