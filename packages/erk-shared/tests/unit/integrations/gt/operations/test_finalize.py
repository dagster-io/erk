"""Unit tests for build_pr_metadata_section function.

Tests the PR metadata footer generation for PR bodies.
"""

from erk_shared.integrations.gt.operations.finalize import build_pr_metadata_section


def test_build_pr_metadata_section_without_issue_number() -> None:
    """Test metadata section without issue number."""
    result = build_pr_metadata_section(pr_number=1895)

    assert "---" in result
    assert "erk pr checkout 1895" in result
    assert "Closes #" not in result


def test_build_pr_metadata_section_with_issue_number() -> None:
    """Test metadata section includes Closes #N when issue_number is provided."""
    result = build_pr_metadata_section(pr_number=1895, issue_number=123)

    assert "---" in result
    assert "Closes #123" in result
    assert "erk pr checkout 1895" in result


def test_build_pr_metadata_section_issue_number_before_checkout() -> None:
    """Test that Closes #N appears before the checkout command."""
    result = build_pr_metadata_section(pr_number=456, issue_number=789)

    closes_pos = result.find("Closes #789")
    checkout_pos = result.find("erk pr checkout 456")

    assert closes_pos != -1
    assert checkout_pos != -1
    assert closes_pos < checkout_pos
