"""Tests for FakePlanBackend - verifying test infrastructure works correctly."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.plan_store.fake import FakePlanBackend
from erk_shared.plan_store.types import Plan, PlanQuery, PlanState


class TestFakePlanBackendCreate:
    """Tests for plan creation functionality."""

    def test_create_plan_returns_result_with_id_and_url(self, tmp_path: Path) -> None:
        """Create plan and verify result has plan_id and url."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        result = backend.create_plan(
            tmp_path,
            title="Test Plan",
            content="Plan content",
            labels=("label1", "label2"),
            metadata={"key": "value"},
        )

        assert result.plan_id == "1"
        assert "1" in result.url

    def test_create_plan_increments_id(self, tmp_path: Path) -> None:
        """Each created plan gets incrementing ID."""
        backend = FakePlanBackend(plans=None, next_plan_id=10, provider_name="test")

        result1 = backend.create_plan(tmp_path, "First", "content", (), {})
        result2 = backend.create_plan(tmp_path, "Second", "content", (), {})

        assert result1.plan_id == "10"
        assert result2.plan_id == "11"

    def test_create_plan_tracks_mutation(self, tmp_path: Path) -> None:
        """Track created plans for test assertions."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        backend.create_plan(tmp_path, "Title", "Content", ("a", "b"), {})

        assert len(backend.created_plans) == 1
        assert backend.created_plans[0] == ("Title", "Content", ("a", "b"))

    def test_create_plan_stores_in_plans_dict(self, tmp_path: Path) -> None:
        """Created plan is retrievable via get_plan."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        result = backend.create_plan(
            tmp_path,
            title="Stored Plan",
            content="Body text",
            labels=("test",),
            metadata={"number": 42},
        )

        plan = backend.get_plan(tmp_path, result.plan_id)
        assert plan.title == "Stored Plan"
        assert plan.body == "Body text"
        assert plan.labels == ["test"]
        assert plan.state == PlanState.OPEN


class TestFakePlanBackendGet:
    """Tests for get_plan functionality."""

    def test_get_plan_returns_configured_plan(self, tmp_path: Path) -> None:
        """Return plan from pre-configured state."""
        now = datetime.now(UTC)
        existing_plan = Plan(
            plan_identifier="42",
            title="Existing Plan",
            body="Existing body",
            state=PlanState.OPEN,
            url="https://example.com/42",
            labels=["bug"],
            assignees=["user1"],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(
            plans={"42": existing_plan}, next_plan_id=100, provider_name="test"
        )

        result = backend.get_plan(tmp_path, "42")

        assert result.plan_identifier == "42"
        assert result.title == "Existing Plan"

    def test_get_plan_raises_for_unknown_id(self, tmp_path: Path) -> None:
        """Raise RuntimeError for non-existent plan_id."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        with pytest.raises(RuntimeError, match="Plan #999 not found"):
            backend.get_plan(tmp_path, "999")


class TestFakePlanBackendList:
    """Tests for list_plans functionality."""

    def test_list_plans_returns_all_when_no_filters(self, tmp_path: Path) -> None:
        """Return all plans when query has no filters."""
        now = datetime.now(UTC)
        plan1 = Plan(
            plan_identifier="1",
            title="Plan 1",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        plan2 = Plan(
            plan_identifier="2",
            title="Plan 2",
            body="",
            state=PlanState.CLOSED,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(
            plans={"1": plan1, "2": plan2}, next_plan_id=100, provider_name="test"
        )

        result = backend.list_plans(tmp_path, PlanQuery())

        assert len(result) == 2

    def test_list_plans_filters_by_labels_and_logic(self, tmp_path: Path) -> None:
        """Filter by labels using AND logic - plan must have ALL labels."""
        now = datetime.now(UTC)
        plan_with_both = Plan(
            plan_identifier="1",
            title="Has both",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=["a", "b", "c"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        plan_with_one = Plan(
            plan_identifier="2",
            title="Has one",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=["a"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(
            plans={"1": plan_with_both, "2": plan_with_one},
            next_plan_id=100,
            provider_name="test",
        )

        result = backend.list_plans(tmp_path, PlanQuery(labels=["a", "b"]))

        assert len(result) == 1
        assert result[0].plan_identifier == "1"

    def test_list_plans_filters_by_state(self, tmp_path: Path) -> None:
        """Filter by plan state."""
        now = datetime.now(UTC)
        open_plan = Plan(
            plan_identifier="1",
            title="Open",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        closed_plan = Plan(
            plan_identifier="2",
            title="Closed",
            body="",
            state=PlanState.CLOSED,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(
            plans={"1": open_plan, "2": closed_plan},
            next_plan_id=100,
            provider_name="test",
        )

        result = backend.list_plans(tmp_path, PlanQuery(state=PlanState.OPEN))

        assert len(result) == 1
        assert result[0].plan_identifier == "1"

    def test_list_plans_respects_limit(self, tmp_path: Path) -> None:
        """Respect limit parameter."""
        now = datetime.now(UTC)
        plans = {
            str(i): Plan(
                plan_identifier=str(i),
                title=f"Plan {i}",
                body="",
                state=PlanState.OPEN,
                url="",
                labels=[],
                assignees=[],
                created_at=now,
                updated_at=now,
                metadata={},
            )
            for i in range(10)
        }
        backend = FakePlanBackend(plans=plans, next_plan_id=100, provider_name="test")

        result = backend.list_plans(tmp_path, PlanQuery(limit=3))

        assert len(result) == 3


class TestFakePlanBackendClose:
    """Tests for close_plan functionality."""

    def test_close_plan_updates_state(self, tmp_path: Path) -> None:
        """Close plan changes state to CLOSED."""
        now = datetime.now(UTC)
        plan = Plan(
            plan_identifier="1",
            title="Open Plan",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(plans={"1": plan}, next_plan_id=100, provider_name="test")

        backend.close_plan(tmp_path, "1")

        updated = backend.get_plan(tmp_path, "1")
        assert updated.state == PlanState.CLOSED

    def test_close_plan_tracks_mutation(self, tmp_path: Path) -> None:
        """Track closed plans for test assertions."""
        now = datetime.now(UTC)
        plan = Plan(
            plan_identifier="1",
            title="Plan",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(plans={"1": plan}, next_plan_id=100, provider_name="test")

        backend.close_plan(tmp_path, "1")

        assert backend.closed_plans == ["1"]

    def test_close_plan_raises_for_unknown_id(self, tmp_path: Path) -> None:
        """Raise RuntimeError for non-existent plan_id."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        with pytest.raises(RuntimeError, match="Plan #999 not found"):
            backend.close_plan(tmp_path, "999")


class TestFakePlanBackendComment:
    """Tests for add_comment functionality."""

    def test_add_comment_returns_generated_id(self, tmp_path: Path) -> None:
        """Return generated comment ID."""
        now = datetime.now(UTC)
        plan = Plan(
            plan_identifier="1",
            title="Plan",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(plans={"1": plan}, next_plan_id=100, provider_name="test")

        comment_id = backend.add_comment(tmp_path, "1", "Comment body")

        assert comment_id == "1000"  # starts at 1000

    def test_add_comment_increments_id(self, tmp_path: Path) -> None:
        """Each comment gets incrementing ID."""
        now = datetime.now(UTC)
        plan = Plan(
            plan_identifier="1",
            title="Plan",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(plans={"1": plan}, next_plan_id=100, provider_name="test")

        id1 = backend.add_comment(tmp_path, "1", "First")
        id2 = backend.add_comment(tmp_path, "1", "Second")

        assert id1 == "1000"
        assert id2 == "1001"

    def test_add_comment_tracks_mutation(self, tmp_path: Path) -> None:
        """Track added comments for test assertions."""
        now = datetime.now(UTC)
        plan = Plan(
            plan_identifier="1",
            title="Plan",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(plans={"1": plan}, next_plan_id=100, provider_name="test")

        backend.add_comment(tmp_path, "1", "Test comment")

        assert len(backend.added_comments) == 1
        assert backend.added_comments[0] == ("1", "Test comment", "1000")

    def test_add_comment_raises_for_unknown_plan(self, tmp_path: Path) -> None:
        """Raise RuntimeError for non-existent plan_id."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        with pytest.raises(RuntimeError, match="Plan #999 not found"):
            backend.add_comment(tmp_path, "999", "Comment")


class TestFakePlanBackendMetadata:
    """Tests for update_metadata functionality."""

    def test_update_metadata_tracks_mutation(self, tmp_path: Path) -> None:
        """Track metadata updates for test assertions."""
        now = datetime.now(UTC)
        plan = Plan(
            plan_identifier="1",
            title="Plan",
            body="",
            state=PlanState.OPEN,
            url="",
            labels=[],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={},
        )
        backend = FakePlanBackend(plans={"1": plan}, next_plan_id=100, provider_name="test")

        backend.update_metadata(tmp_path, "1", {"key": "value"})

        assert len(backend.updated_metadata) == 1
        assert backend.updated_metadata[0] == ("1", {"key": "value"})

    def test_update_metadata_raises_for_unknown_plan(self, tmp_path: Path) -> None:
        """Raise RuntimeError for non-existent plan_id."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        with pytest.raises(RuntimeError, match="Plan #999 not found"):
            backend.update_metadata(tmp_path, "999", {})


class TestFakePlanBackendProviderName:
    """Tests for get_provider_name functionality."""

    def test_get_provider_name_returns_configured_value(self) -> None:
        """Return provider name from constructor."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="custom-provider")

        assert backend.get_provider_name() == "custom-provider"


class TestFakePlanBackendInitialization:
    """Tests for constructor and initial state."""

    def test_mutation_trackers_start_empty(self) -> None:
        """All mutation tracking lists start empty."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        assert backend.created_plans == []
        assert backend.updated_metadata == []
        assert backend.closed_plans == []
        assert backend.added_comments == []

    def test_none_plans_creates_empty_dict(self, tmp_path: Path) -> None:
        """Passing plans=None creates empty dict, not error."""
        backend = FakePlanBackend(plans=None, next_plan_id=1, provider_name="test")

        # list_plans should return empty, not error
        result = backend.list_plans(tmp_path, PlanQuery())
        assert result == []
