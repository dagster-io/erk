"""Tests for PlanFileCollector.

These tests verify that the impl collector correctly gathers implementation folder information
including issue references for status display.
"""

from pathlib import Path

from erk_shared.git.fake import FakeGit
from erk_shared.impl_folder import create_impl_folder, save_issue_reference

from erk.core.context import ErkContext
from erk.status.collectors.impl import PlanFileCollector


def test_plan_collector_no_plan_folder(tmp_path: Path) -> None:
    """Test collector returns None when no .impl/ folder exists."""
    git = FakeGit()
    ctx = ErkContext.minimal(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is False
    assert result.issue_number is None
    assert result.issue_url is None


def test_plan_collector_with_plan_no_issue(tmp_path: Path) -> None:
    """Test collector returns plan status without issue when no issue.json exists."""
    # Create plan folder without issue reference
    plan_content = "# Test Plan\n\n1. Step one\n2. Step two"
    create_impl_folder(tmp_path, plan_content)

    git = FakeGit()
    ctx = ErkContext.minimal(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is True
    assert result.issue_number is None
    assert result.issue_url is None


def test_plan_collector_with_issue_reference(tmp_path: Path) -> None:
    """Test collector includes issue reference in PlanStatus."""
    # Create plan folder
    plan_content = "# Test Plan\n\n1. Step one"
    plan_folder = create_impl_folder(tmp_path, plan_content)

    # Save issue reference
    save_issue_reference(plan_folder, 42, "https://github.com/owner/repo/issues/42")

    git = FakeGit()
    ctx = ErkContext.minimal(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is True
    assert result.issue_number == 42
    assert result.issue_url == "https://github.com/owner/repo/issues/42"


def test_plan_collector_issue_reference_with_progress(tmp_path: Path) -> None:
    """Test collector includes both progress and issue information."""
    import frontmatter

    # Create plan folder
    plan_content = "# Test Plan\n\n1. Step one\n2. Step two\n3. Step three"
    plan_folder = create_impl_folder(tmp_path, plan_content)

    # Save issue reference
    save_issue_reference(plan_folder, 123, "https://github.com/test/repo/issues/123")

    # Mark one step complete using frontmatter library
    progress_file = plan_folder / "progress.md"
    content = progress_file.read_text(encoding="utf-8")

    # Parse frontmatter
    post = frontmatter.loads(content)

    # Update the steps array
    post.metadata["steps"][0]["completed"] = True
    post.metadata["completed_steps"] = 1

    # Regenerate checkboxes in body
    body_lines = ["# Progress Tracking\n"]
    for step in post.metadata["steps"]:
        checkbox = "[x]" if step["completed"] else "[ ]"
        body_lines.append(f"- {checkbox} {step['text']}")
    body_lines.append("")
    post.content = "\n".join(body_lines)

    # Write back
    updated_content = frontmatter.dumps(post)
    progress_file.write_text(updated_content, encoding="utf-8")

    git = FakeGit()
    ctx = ErkContext.minimal(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    assert result is not None
    assert result.exists is True
    assert result.progress_summary == "1/3 steps completed"
    assert result.completion_percentage == 33  # 1/3 = 33%
    assert result.issue_number == 123
    assert result.issue_url == "https://github.com/test/repo/issues/123"


def test_plan_collector_invalid_issue_reference(tmp_path: Path) -> None:
    """Test collector handles invalid issue.json gracefully."""
    # Create plan folder
    plan_content = "# Test Plan\n\n1. Step"
    plan_folder = create_impl_folder(tmp_path, plan_content)

    # Create invalid issue.json
    issue_file = plan_folder / "issue.json"
    issue_file.write_text("not valid json", encoding="utf-8")

    git = FakeGit()
    ctx = ErkContext.minimal(git, tmp_path)
    collector = PlanFileCollector()

    result = collector.collect(ctx, tmp_path, tmp_path)

    # Should still work but without issue info
    assert result is not None
    assert result.exists is True
    assert result.issue_number is None
    assert result.issue_url is None
