"""Tests for PlanFileCollector.

These tests verify that the impl collector correctly gathers implementation folder information
including issue references for status display.
"""

from pathlib import Path

from erk.core.context import minimal_context
from erk.status.collectors.impl import PlanFileCollector
from erk_shared.git.fake import FakeGit
from erk_shared.impl_folder import create_impl_folder, save_issue_reference


def test_plan_collector_no_plan_folder(tmp_path: Path) -> None:
    """Test collector returns None when no .impl/ folder exists."""
    git = FakeGit()
    ctx = minimal_context(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is False
    assert result.issue_number is None
    assert result.issue_url is None


def test_plan_collector_with_plan_no_issue(tmp_path: Path) -> None:
    """Test collector returns plan status without issue when no issue.json exists."""
    # Create plan folder without issue reference (uses ## Step N: format)
    plan_content = "# Test Plan\n\n## Step 1: Step one\n## Step 2: Step two\n"
    create_impl_folder(tmp_path, plan_content, overwrite=False)

    git = FakeGit()
    ctx = minimal_context(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is True
    assert result.issue_number is None
    assert result.issue_url is None


def test_plan_collector_with_issue_reference(tmp_path: Path) -> None:
    """Test collector includes issue reference in PlanStatus."""
    # Create plan folder (uses ## Step N: format)
    plan_content = "# Test Plan\n\n## Step 1: Step one\n"
    plan_folder = create_impl_folder(tmp_path, plan_content, overwrite=False)

    # Save issue reference
    save_issue_reference(plan_folder, 42, "https://github.com/owner/repo/issues/42")

    git = FakeGit()
    ctx = minimal_context(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is True
    assert result.issue_number == 42
    assert result.issue_url == "https://github.com/owner/repo/issues/42"


def test_plan_collector_invalid_issue_reference(tmp_path: Path) -> None:
    """Test collector handles invalid issue.json gracefully."""
    # Create plan folder (uses ## Step N: format)
    plan_content = "# Test Plan\n\n## Step 1: Step\n"
    plan_folder = create_impl_folder(tmp_path, plan_content, overwrite=False)

    # Create invalid issue.json
    issue_file = plan_folder / "issue.json"
    issue_file.write_text("not valid json", encoding="utf-8")

    git = FakeGit()
    ctx = minimal_context(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    # Should still work but without issue info
    assert result is not None
    assert result.exists is True
    assert result.issue_number is None
    assert result.issue_url is None
