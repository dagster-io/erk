"""Tests for CLI EnsureIdeal utility class."""

import pytest

from erk.cli.ensure_ideal import EnsureIdeal
from erk_shared.gateway.github.types import PRDetails, PRNotFound


class TestEnsureIdealUnwrapPr:
    """Tests for EnsureIdeal.unwrap_pr method."""

    def test_returns_pr_details_when_valid(self) -> None:
        """EnsureIdeal.unwrap_pr returns PRDetails unchanged when valid."""
        pr = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Test PR",
            body="Test body",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )

        result = EnsureIdeal.unwrap_pr(pr, "PR not found")

        assert result is pr

    def test_exits_when_pr_not_found(self) -> None:
        """EnsureIdeal.unwrap_pr raises SystemExit when PRNotFound sentinel."""
        not_found = PRNotFound(branch="feature")

        with pytest.raises(SystemExit) as exc_info:
            EnsureIdeal.unwrap_pr(not_found, "No PR exists for branch 'feature'")

        assert exc_info.value.code == 1

    def test_error_message_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """EnsureIdeal.unwrap_pr outputs custom error message to stderr."""
        not_found = PRNotFound(pr_number=42)

        with pytest.raises(SystemExit):
            EnsureIdeal.unwrap_pr(not_found, "Could not find PR #42")

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Could not find PR #42" in captured.err
