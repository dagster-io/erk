"""Tests for PlanDataProvider routing logic.

Tests verify that fetch_plans() routes queries to the correct service:
- Queries with "erk-objective" label use objective_list_service
- All other queries use plan_list_service
"""

from unittest.mock import MagicMock

from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.real import RealPlanDataProvider


def _make_provider(
    objective_service: MagicMock | None = None,
    plan_service: MagicMock | None = None,
) -> RealPlanDataProvider:
    """Create a RealPlanDataProvider with mocked services."""
    mock_ctx = MagicMock()
    mock_ctx.time.monotonic.return_value = 0.0
    mock_objective_service = objective_service or MagicMock()
    mock_plan_service = plan_service or MagicMock()
    mock_ctx.objective_list_service = mock_objective_service
    mock_ctx.plan_list_service = mock_plan_service
    _empty_plan_data = MagicMock(
        plans=[],
        pr_linkages={},
        workflow_runs={},
        api_ms=0.0,
        plan_parsing_ms=0.0,
        workflow_runs_ms=0.0,
    )
    mock_objective_service.get_objective_list_data.return_value = _empty_plan_data
    mock_plan_service.get_plan_list_data.return_value = _empty_plan_data

    return RealPlanDataProvider(
        mock_ctx,
        location=MagicMock(),
        clipboard=MagicMock(),
        browser=MagicMock(),
        http_client=MagicMock(),
    )


class TestPlanDataProviderRouting:
    """Tests for routing logic in RealPlanDataProvider.fetch_plans()."""

    def test_routes_to_objective_service_when_erk_objective_label_present(
        self,
    ) -> None:
        """Routes to objective_list_service when 'erk-objective' is in labels."""
        # Arrange
        mock_objective_service = MagicMock()
        mock_plan_service = MagicMock()
        mock_objective_service.get_objective_list_data.return_value = MagicMock(
            plans=[],
            pr_linkages={},
            workflow_runs={},
            api_ms=0.0,
            plan_parsing_ms=0.0,
            workflow_runs_ms=0.0,
        )
        provider = _make_provider(
            objective_service=mock_objective_service, plan_service=mock_plan_service
        )

        # Query filters with "erk-objective" label
        filters = PlanFilters(
            labels=("erk-objective",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )

        # Act
        provider.fetch_plans(filters)

        # Assert: objective_list_service should be called
        mock_objective_service.get_objective_list_data.assert_called_once()
        # plan_list_service should NOT be called
        mock_plan_service.get_plan_list_data.assert_not_called()

    def test_routes_to_plan_service_when_erk_objective_label_absent(self) -> None:
        """Routes to plan_list_service when 'erk-objective' is NOT in labels."""
        # Arrange
        mock_objective_service = MagicMock()
        mock_plan_service = MagicMock()
        provider = _make_provider(
            objective_service=mock_objective_service, plan_service=mock_plan_service
        )

        # Query filters with "erk-plan" label (NOT objective)
        filters = PlanFilters(
            labels=("erk-plan",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )

        # Act
        provider.fetch_plans(filters)

        # Assert: plan_list_service should be called
        mock_plan_service.get_plan_list_data.assert_called_once()
        # objective_list_service should NOT be called
        mock_objective_service.get_objective_list_data.assert_not_called()

    def test_routes_to_plan_service_for_learn_plans(self) -> None:
        """Routes to plan_list_service for learn plans (erk-learn label)."""
        # Arrange
        mock_objective_service = MagicMock()
        mock_plan_service = MagicMock()
        provider = _make_provider(
            objective_service=mock_objective_service, plan_service=mock_plan_service
        )

        # Query filters with "erk-learn" label
        filters = PlanFilters(
            labels=("erk-learn",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )

        # Act
        provider.fetch_plans(filters)

        # Assert: plan_list_service should be called (not objective service)
        mock_plan_service.get_plan_list_data.assert_called_once()
        mock_objective_service.get_objective_list_data.assert_not_called()

    def test_routes_to_plan_service_for_multi_label_query(self) -> None:
        """Routes to plan_list_service for multi-label queries (erk-planned-pr + erk-learn)."""
        # Arrange
        mock_objective_service = MagicMock()
        mock_plan_service = MagicMock()
        provider = _make_provider(
            objective_service=mock_objective_service, plan_service=mock_plan_service
        )

        # Query filters with multiple labels, but NOT erk-objective
        filters = PlanFilters(
            labels=("erk-planned-pr", "erk-learn"),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )

        # Act
        provider.fetch_plans(filters)

        # Assert: plan_list_service should be called
        mock_plan_service.get_plan_list_data.assert_called_once()
        mock_objective_service.get_objective_list_data.assert_not_called()

    def test_condition_inverts_correctly_objective_vs_plan(self) -> None:
        """Verify the routing condition inverts correctly for objectives vs plans.

        This test explicitly checks the behavior documented in the routing logic:
        - if "erk-objective" in labels → use objective service (inverted check)
        - else → use plan service (all other queries)
        """
        # Arrange
        mock_objective_service = MagicMock()
        mock_plan_service = MagicMock()
        provider = _make_provider(
            objective_service=mock_objective_service, plan_service=mock_plan_service
        )

        # Case 1: WITH erk-objective
        filters_with_objective = PlanFilters(
            labels=("erk-objective",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )
        provider.fetch_plans(filters_with_objective)
        assert mock_objective_service.get_objective_list_data.call_count == 1, (
            "Should route WITH objective to objective service"
        )
        assert mock_plan_service.get_plan_list_data.call_count == 0, (
            "Should NOT route WITH objective to plan service"
        )

        # Reset mocks
        mock_objective_service.reset_mock()
        mock_plan_service.reset_mock()

        # Case 2: WITHOUT erk-objective (plan query)
        filters_without_objective = PlanFilters(
            labels=("erk-plan",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )
        provider.fetch_plans(filters_without_objective)
        assert mock_plan_service.get_plan_list_data.call_count == 1, (
            "Should route WITHOUT objective to plan service"
        )
        assert mock_objective_service.get_objective_list_data.call_count == 0, (
            "Should NOT route WITHOUT objective to objective service"
        )
