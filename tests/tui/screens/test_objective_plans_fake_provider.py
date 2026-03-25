"""Tests for FakePrDataProvider.fetch_prs_for_objective()."""

from tests.fakes.gateway.plan_data_provider import FakePrDataProvider, make_pr_row


def test_fetch_prs_for_objective_filters_by_objective_issue() -> None:
    """Only returns plans matching the given objective_issue."""
    plans = [
        make_pr_row(100, "Plan A", objective_issue=8088),
        make_pr_row(101, "Plan B", objective_issue=8036),
        make_pr_row(102, "Plan C", objective_issue=8088),
        make_pr_row(103, "Plan D"),  # No objective
    ]
    provider = FakePrDataProvider(plans=plans)

    result = provider.fetch_prs_for_objective(8088)

    assert len(result) == 2
    assert {r.pr_number for r in result} == {100, 102}


def test_fetch_prs_for_objective_returns_empty_when_no_match() -> None:
    """Returns empty list when no plans match the objective."""
    plans = [
        make_pr_row(100, "Plan A", objective_issue=8088),
        make_pr_row(101, "Plan B", objective_issue=8036),
    ]
    provider = FakePrDataProvider(plans=plans)

    result = provider.fetch_prs_for_objective(9999)

    assert result == []


def test_fetch_prs_for_objective_returns_empty_when_no_plans() -> None:
    """Returns empty list when provider has no plans at all."""
    provider = FakePrDataProvider()

    result = provider.fetch_prs_for_objective(8088)

    assert result == []
