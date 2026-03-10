"""Unit tests for pr list helper functions."""

import pytest

from erk.cli.commands.pr.list_cmd import _build_pr_list_request
from erk.cli.commands.pr.list_operation import PrListRequest
from erk.cli.ensure import UserFacingCliError


def test_build_pr_list_request_narrows_click_choice_values() -> None:
    request = _build_pr_list_request(
        label=("erk-plan",),
        state="open",
        run_state="queued",
        stage="impl",
        limit=5,
        all_users=True,
        sort="activity",
        repo="owner/repo",
    )

    assert request == PrListRequest(
        labels=("erk-plan",),
        state="open",
        run_state="queued",
        stage="impl",
        limit=5,
        all_users=True,
        sort="activity",
        repo="owner/repo",
    )


def test_build_pr_list_request_rejects_invalid_sort_value() -> None:
    with pytest.raises(UserFacingCliError, match="Invalid sort value: newest"):
        _build_pr_list_request(
            label=(),
            state=None,
            run_state=None,
            stage=None,
            limit=None,
            all_users=False,
            sort="newest",
            repo="owner/repo",
        )
