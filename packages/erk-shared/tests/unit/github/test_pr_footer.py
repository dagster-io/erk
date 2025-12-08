"""Unit tests for PR body footer generation.

Tests the canonical build_pr_body_footer and build_remote_execution_note functions.
"""

from erk_shared.github.pr_footer import build_pr_body_footer, build_remote_execution_note


def test_build_pr_body_footer_without_issue_number() -> None:
    """Test footer generation without issue number."""
    result = build_pr_body_footer(pr_number=1895)

    assert "---" in result
    assert "erk pr checkout 1895 && erk pr sync" in result
    assert "Closes #" not in result


def test_build_pr_body_footer_with_issue_number() -> None:
    """Test footer includes Closes #N when issue_number is provided."""
    result = build_pr_body_footer(pr_number=1895, issue_number=123)

    assert "---" in result
    assert "Closes #123" in result
    assert "erk pr checkout 1895 && erk pr sync" in result


def test_build_pr_body_footer_issue_number_before_checkout() -> None:
    """Test that Closes #N appears before the checkout command."""
    result = build_pr_body_footer(pr_number=456, issue_number=789)

    closes_pos = result.find("Closes #789")
    checkout_pos = result.find("erk pr checkout 456")

    assert closes_pos != -1
    assert checkout_pos != -1
    assert closes_pos < checkout_pos


def test_build_pr_body_footer_includes_sync_command() -> None:
    """Test that footer includes '&& erk pr sync' in checkout command."""
    result = build_pr_body_footer(pr_number=100)

    assert "&& erk pr sync" in result
    assert "erk pr checkout 100 && erk pr sync" in result


# ============================================================================
# build_remote_execution_note Tests
# ============================================================================


def test_build_remote_execution_note_includes_run_id_and_url() -> None:
    """Test that remote execution note includes run ID and URL."""
    result = build_remote_execution_note(
        workflow_run_id="12345678",
        workflow_run_url="https://github.com/owner/repo/actions/runs/12345678",
    )

    assert "12345678" in result
    assert "https://github.com/owner/repo/actions/runs/12345678" in result
    assert "Remotely executed" in result


def test_build_remote_execution_note_is_markdown_link() -> None:
    """Test that the run link is a proper markdown link."""
    result = build_remote_execution_note(
        workflow_run_id="99999",
        workflow_run_url="https://github.com/test/repo/actions/runs/99999",
    )

    assert "[Run #99999](https://github.com/test/repo/actions/runs/99999)" in result


def test_build_remote_execution_note_starts_with_newline() -> None:
    """Test that note starts with newline for proper appending."""
    result = build_remote_execution_note(
        workflow_run_id="123",
        workflow_run_url="https://example.com/123",
    )

    assert result.startswith("\n")
