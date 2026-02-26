"""Tests for impl_folder utilities.

Layer 3: Pure unit tests (zero dependencies).
"""

import json
from pathlib import Path


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


def test_read_plan_ref_ignores_issue_json(tmp_path: Path) -> None:
    """read_plan_ref does not fall back to legacy issue.json."""
    from erk_shared.impl_folder import read_plan_ref

    impl_dir = tmp_path / "impl"
    impl_dir.mkdir()
    issue_data = {
        "issue_number": 42,
        "issue_url": "https://github.com/owner/repo/issues/42",
        "created_at": "2025-01-01T00:00:00Z",
        "synced_at": "2025-01-01T00:00:00Z",
    }
    (impl_dir / "issue.json").write_text(json.dumps(issue_data), encoding="utf-8")

    result = read_plan_ref(impl_dir)

    assert result is None


def test_resolve_impl_dir_ignores_legacy_impl_folder(tmp_path: Path) -> None:
    """resolve_impl_dir does not return the legacy .impl/ directory."""
    from erk_shared.impl_folder import resolve_impl_dir

    legacy_dir = tmp_path / ".impl"
    legacy_dir.mkdir()
    (legacy_dir / "plan.md").write_text("# Plan", encoding="utf-8")

    result = resolve_impl_dir(tmp_path, branch_name=None)

    assert result is None


def test_has_plan_ref_ignores_issue_json(tmp_path: Path) -> None:
    """has_plan_ref returns False when only issue.json exists."""
    from erk_shared.impl_folder import has_plan_ref

    impl_dir = tmp_path / "impl"
    impl_dir.mkdir()
    (impl_dir / "issue.json").write_text("{}", encoding="utf-8")

    assert has_plan_ref(impl_dir) is False
