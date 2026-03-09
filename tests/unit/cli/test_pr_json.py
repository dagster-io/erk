"""Tests for erk pr list/view --json output and --schema."""

from __future__ import annotations

from datetime import UTC, datetime

from erk.cli.commands.pr.list_cmd import PrListResult
from erk.cli.commands.pr.view_cmd import PrViewResult, _serialize_header_fields


class TestPrListResult:
    """Tests for PrListResult JSON serialization."""

    def test_to_json_dict_structure(self) -> None:
        result = PrListResult(
            plans=[{"plan_id": 42, "full_title": "My Plan"}],
            count=1,
        )

        data = result.to_json_dict()

        assert data == {
            "plans": [{"plan_id": 42, "full_title": "My Plan"}],
            "count": 1,
        }

    def test_empty_plans(self) -> None:
        result = PrListResult(plans=[], count=0)

        data = result.to_json_dict()

        assert data == {"plans": [], "count": 0}


class TestPrViewResult:
    """Tests for PrViewResult JSON serialization."""

    def test_to_json_dict_includes_all_fields(self) -> None:
        result = PrViewResult(
            plan_id="42",
            title="My Plan",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-pr"],
            assignees=["user1"],
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-02T00:00:00+00:00",
            objective_id=100,
            branch="plnd/my-feature",
            header_fields={"created_by": "user1"},
            body="# Plan content",
        )

        data = result.to_json_dict()

        assert data["plan_id"] == "42"
        assert data["title"] == "My Plan"
        assert data["state"] == "OPEN"
        assert data["url"] == "https://github.com/owner/repo/issues/42"
        assert data["labels"] == ["erk-pr"]
        assert data["assignees"] == ["user1"]
        assert data["created_at"] == "2024-01-01T00:00:00+00:00"
        assert data["updated_at"] == "2024-01-02T00:00:00+00:00"
        assert data["objective_id"] == 100
        assert data["branch"] == "plnd/my-feature"
        assert data["header_fields"] == {"created_by": "user1"}
        assert data["body"] == "# Plan content"

    def test_to_json_dict_omits_body_when_none(self) -> None:
        result = PrViewResult(
            plan_id="42",
            title="My Plan",
            state="OPEN",
            url=None,
            labels=[],
            assignees=[],
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-02T00:00:00+00:00",
            objective_id=None,
            branch=None,
            header_fields={},
            body=None,
        )

        data = result.to_json_dict()

        assert "body" not in data

    def test_to_json_dict_nullable_fields(self) -> None:
        result = PrViewResult(
            plan_id="42",
            title="My Plan",
            state="CLOSED",
            url=None,
            labels=[],
            assignees=[],
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-02T00:00:00+00:00",
            objective_id=None,
            branch=None,
            header_fields={},
            body=None,
        )

        data = result.to_json_dict()

        assert data["url"] is None
        assert data["objective_id"] is None
        assert data["branch"] is None


class TestSerializeHeaderFields:
    """Tests for _serialize_header_fields helper."""

    def test_converts_datetime_to_iso(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        fields: dict[str, object] = {"last_local_impl_at": dt, "created_by": "user1"}

        result = _serialize_header_fields(fields)

        assert result["last_local_impl_at"] == "2024-01-15T10:30:00+00:00"
        assert result["created_by"] == "user1"

    def test_passes_through_non_datetime_values(self) -> None:
        fields: dict[str, object] = {
            "schema_version": 2,
            "worktree_name": "my-wt",
            "objective_issue": 100,
        }

        result = _serialize_header_fields(fields)

        assert result == fields

    def test_empty_fields(self) -> None:
        result = _serialize_header_fields({})

        assert result == {}
