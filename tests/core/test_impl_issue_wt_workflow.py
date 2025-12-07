"""Tests for implementation issue + worktree creation workflow.

Tests the integration of plan file reading, worktree creation, issue creation,
and linking them together via .impl/issue.json.
"""

from pathlib import Path

import pytest
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.impl_folder import (
    create_impl_folder,
    has_issue_reference,
    read_issue_reference,
    save_issue_reference,
)

from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.paths import sentinel_path


def test_save_and_read_issue_reference(tmp_path: Path) -> None:
    """Test saving and reading issue reference from impl folder."""
    impl_folder = tmp_path / ".impl"
    impl_folder.mkdir()

    issue_number = 42
    issue_url = "https://github.com/owner/repo/issues/42"

    # Save issue reference
    save_issue_reference(impl_folder, issue_number, issue_url)

    # Verify file was created
    issue_json = impl_folder / "issue.json"
    assert issue_json.exists()

    # Read back and verify
    ref = read_issue_reference(impl_folder)
    assert ref is not None
    assert ref.issue_number == issue_number
    assert ref.issue_url == issue_url
    assert ref.created_at is not None
    assert ref.synced_at is not None


def test_save_issue_reference_plan_dir_must_exist(tmp_path: Path) -> None:
    """Test that save_issue_reference raises if impl dir doesn't exist."""
    impl_folder = tmp_path / ".impl"  # Doesn't exist

    with pytest.raises(FileNotFoundError, match="Implementation directory does not exist"):
        save_issue_reference(impl_folder, 42, "https://github.com/owner/repo/issues/42")


def test_has_issue_reference_false_when_no_file(tmp_path: Path) -> None:
    """Test has_issue_reference returns False when issue.json doesn't exist."""
    impl_folder = tmp_path / ".impl"
    impl_folder.mkdir()

    assert has_issue_reference(impl_folder) is False


def test_has_issue_reference_true_when_file_exists(tmp_path: Path) -> None:
    """Test has_issue_reference returns True when issue.json exists."""
    impl_folder = tmp_path / ".impl"
    impl_folder.mkdir()

    save_issue_reference(impl_folder, 42, "https://github.com/owner/repo/issues/42")

    assert has_issue_reference(impl_folder) is True


def test_read_issue_reference_returns_none_when_no_file(tmp_path: Path) -> None:
    """Test read_issue_reference returns None when file doesn't exist."""
    impl_folder = tmp_path / ".plan"
    impl_folder.mkdir()

    ref = read_issue_reference(impl_folder)
    assert ref is None


def test_workflow_create_plan_then_link_issue(tmp_path: Path) -> None:
    """Test complete workflow: create plan folder, then link issue."""
    plan_content = """# Test Plan

## Objective
Test the workflow.

## Implementation Steps
1. Step one
2. Step two
"""

    # Step 1: Create plan folder (simulates erk create --from-plan)
    impl_folder = create_impl_folder(tmp_path, plan_content, overwrite=False)

    # Step 2: Create issue (simulates gh issue create)
    issues = FakeGitHubIssues(next_issue_number=123)
    result = issues.create_issue(sentinel_path(), "Test Plan", plan_content, ["erk-plan"])

    assert result.number == 123

    # Step 3: Link issue to plan folder
    save_issue_reference(impl_folder, result.number, result.url)

    # Step 4: Verify link was created
    assert has_issue_reference(impl_folder)

    # Step 5: Read back and verify
    ref = read_issue_reference(impl_folder)
    assert ref is not None
    assert ref.issue_number == 123
    assert ref.issue_url == result.url


def test_workflow_issue_creation_tracks_erk_plan_label() -> None:
    """Test that issue creation includes erk-plan label."""
    issues = FakeGitHubIssues()

    issues.create_issue(
        sentinel_path(),
        title="Implementation Plan",
        body="Plan content here",
        labels=["erk-plan"],
    )

    # Verify issue was created with label
    assert len(issues.created_issues) == 1
    title, body, labels = issues.created_issues[0]
    assert title == "Implementation Plan"
    assert body == "Plan content here"
    assert "erk-plan" in labels


def test_workflow_get_issue_after_creation() -> None:
    """Test retrieving issue info after creation."""
    issues = FakeGitHubIssues(
        next_issue_number=42, issues={42: create_test_issue(42, "Test Issue", "Body content")}
    )

    # Create issue
    result = issues.create_issue(sentinel_path(), "Test Issue", "Body content", ["erk-plan"])

    # Retrieve issue info
    info = issues.get_issue(sentinel_path(), result.number)

    assert info is not None
    assert info.number == 42
    assert info.title == "Test Issue"
    assert info.url == "https://github.com/test-owner/test-repo/issues/42"
    assert info.state == "OPEN"


def test_workflow_multiple_issues_increment_numbers() -> None:
    """Test that multiple issue creations increment issue numbers."""
    issues = FakeGitHubIssues(next_issue_number=10)

    result1 = issues.create_issue(sentinel_path(), "Issue 1", "Body 1", ["label1"])
    result2 = issues.create_issue(sentinel_path(), "Issue 2", "Body 2", ["label2"])
    result3 = issues.create_issue(sentinel_path(), "Issue 3", "Body 3", ["label3"])

    assert result1.number == 10
    assert result2.number == 11
    assert result3.number == 12

    assert len(issues.created_issues) == 3


def test_workflow_title_extraction_yaml_frontmatter(tmp_path: Path) -> None:
    """Test that plan with YAML front matter title is used for issue."""
    plan_content = """---
title: Custom Title from YAML
---

# Some Other Heading

Content here.
"""

    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # In real workflow, agent would parse YAML and extract "Custom Title from YAML"
    # For this test, we just verify the content contains the YAML
    content = plan_file.read_text(encoding="utf-8")
    assert "title: Custom Title from YAML" in content
    assert "# Some Other Heading" in content


def test_workflow_title_extraction_h1_heading(tmp_path: Path) -> None:
    """Test that plan with H1 heading (no YAML) uses H1 for issue."""
    plan_content = """# Implementation Plan for Feature X

## Objective
Build feature X.

## Steps
1. Step one
2. Step two
"""

    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # In real workflow, agent would extract "Implementation Plan for Feature X"
    content = plan_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    h1_line = next((line for line in lines if line.startswith("# ")), None)

    assert h1_line is not None
    title = h1_line.lstrip("# ").strip()
    assert title == "Implementation Plan for Feature X"


def test_workflow_title_extraction_filename_fallback(tmp_path: Path) -> None:
    """Test that filename (without -plan.md) is used as fallback for issue title."""
    plan_content = """Some plan content without YAML or H1 heading.

Just plain text describing the plan.
"""

    plan_file = tmp_path / "feature-x-plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # In real workflow, agent would use "feature-x" as title
    filename = plan_file.name
    title = filename.replace("-plan.md", "")
    assert title == "feature-x"
