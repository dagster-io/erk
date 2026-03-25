"""Unit tests for is_learn_plan function.

Tests learn plan detection based on plan-ref.json labels.

Note: build_pr_body_footer tests are in tests/unit/github/test_pr_footer.py
"""

import json
from pathlib import Path

from erk_shared.gateway.gt.operations.finalize import is_learn_plan


class TestIsLearnPlan:
    """Tests for is_learn_plan function."""

    def test_returns_false_when_plan_ref_json_does_not_exist(self, tmp_path: Path) -> None:
        """Test that function returns False when plan-ref.json doesn't exist."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        result = is_learn_plan(impl_dir)

        assert result is False

    def test_returns_false_when_impl_dir_does_not_exist(self, tmp_path: Path) -> None:
        """Test that function returns False when .impl/ doesn't exist."""
        impl_dir = tmp_path / ".impl"

        result = is_learn_plan(impl_dir)

        assert result is False

    def test_returns_false_when_labels_field_is_missing(self, tmp_path: Path) -> None:
        """Test returns False when plan-ref.json has no labels field."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_ref_file = impl_dir / "plan-ref.json"
        plan_ref_data = {
            "plan_id": "42",
            "url": "https://github.com/org/repo/pull/123",
            "provider": "github",
            "created_at": "2025-01-01T00:00:00Z",
            "synced_at": "2025-01-01T00:00:00Z",
        }
        plan_ref_file.write_text(json.dumps(plan_ref_data), encoding="utf-8")

        result = is_learn_plan(impl_dir)

        assert result is False

    def test_returns_false_when_labels_is_empty(self, tmp_path: Path) -> None:
        """Test returns False when labels is an empty list."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_ref_file = impl_dir / "plan-ref.json"
        plan_ref_data = {
            "plan_id": "42",
            "url": "https://github.com/org/repo/pull/123",
            "provider": "github",
            "created_at": "2025-01-01T00:00:00Z",
            "synced_at": "2025-01-01T00:00:00Z",
            "labels": [],
        }
        plan_ref_file.write_text(json.dumps(plan_ref_data), encoding="utf-8")

        result = is_learn_plan(impl_dir)

        assert result is False

    def test_returns_false_when_erk_learn_label_not_present(self, tmp_path: Path) -> None:
        """Test returns False when erk-learn label is not in labels."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_ref_file = impl_dir / "plan-ref.json"
        plan_ref_data = {
            "plan_id": "42",
            "url": "https://github.com/org/repo/pull/123",
            "provider": "github",
            "created_at": "2025-01-01T00:00:00Z",
            "synced_at": "2025-01-01T00:00:00Z",
            "labels": ["erk-pr", "bug"],
        }
        plan_ref_file.write_text(json.dumps(plan_ref_data), encoding="utf-8")

        result = is_learn_plan(impl_dir)

        assert result is False

    def test_returns_true_when_erk_learn_label_present(self, tmp_path: Path) -> None:
        """Test returns True when erk-learn label is in labels."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_ref_file = impl_dir / "plan-ref.json"
        plan_ref_data = {
            "plan_id": "42",
            "url": "https://github.com/org/repo/pull/123",
            "provider": "github",
            "created_at": "2025-01-01T00:00:00Z",
            "synced_at": "2025-01-01T00:00:00Z",
            "labels": ["erk-pr", "erk-learn"],
        }
        plan_ref_file.write_text(json.dumps(plan_ref_data), encoding="utf-8")

        result = is_learn_plan(impl_dir)

        assert result is True

    def test_returns_true_when_erk_learn_is_only_label(self, tmp_path: Path) -> None:
        """Test returns True when erk-learn is the only label."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_ref_file = impl_dir / "plan-ref.json"
        plan_ref_data = {
            "plan_id": "42",
            "url": "https://github.com/org/repo/pull/123",
            "provider": "github",
            "created_at": "2025-01-01T00:00:00Z",
            "synced_at": "2025-01-01T00:00:00Z",
            "labels": ["erk-learn"],
        }
        plan_ref_file.write_text(json.dumps(plan_ref_data), encoding="utf-8")

        result = is_learn_plan(impl_dir)

        assert result is True
