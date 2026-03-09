"""Tests for FakePlanDataProvider.fetch_plans_for_objective()."""

from erk_shared.fakes.plan_data_provider import FakePlanDataProvider, make_plan_row


def test_fetch_plans_for_objective_filters_by_objective_issue() -> None:
    """Only returns plans matching the given objective_issue."""
    plans = [
        make_plan_row(100, "Plan A", objective_issue=8088),
        make_plan_row(101, "Plan B", objective_issue=8036),
        make_plan_row(102, "Plan C", objective_issue=8088),
        make_plan_row(103, "Plan D"),  # No objective
    ]
    provider = FakePlanDataProvider(plans=plans)

    result = provider.fetch_plans_for_objective(8088)

    assert len(result) == 2
    assert {r.plan_id for r in result} == {100, 102}


def test_fetch_plans_for_objective_returns_empty_when_no_match() -> None:
    """Returns empty list when no plans match the objective."""
    plans = [
        make_plan_row(100, "Plan A", objective_issue=8088),
        make_plan_row(101, "Plan B", objective_issue=8036),
    ]
    provider = FakePlanDataProvider(plans=plans)

    result = provider.fetch_plans_for_objective(9999)

    assert result == []


def test_fetch_plans_for_objective_returns_empty_when_no_plans() -> None:
    """Returns empty list when provider has no plans at all."""
    provider = FakePlanDataProvider()

    result = provider.fetch_plans_for_objective(8088)

    assert result == []
