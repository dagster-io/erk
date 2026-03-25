"""Tests for file_utils.extract_pr_title."""

import pytest

from erk.core.file_utils import extract_pr_title

PLAN_CASES = [
    pytest.param(
        "frontmatter_followed_by_heading",
        "plan.md",
        """---
title: Metadata
---

# Actual Title

Content here.
""",
        "Actual Title",
        id="frontmatter_followed_by_heading",
    ),
    pytest.param(
        "heading_on_first_line",
        "plan.md",
        "# First Heading\n\nContent.",
        "First Heading",
        id="heading_on_first_line",
    ),
    pytest.param(
        "deep_heading",
        "plan.md",
        "### Deep Heading\n\nContent.",
        "Deep Heading",
        id="deep_heading",
    ),
    pytest.param(
        "only_frontmatter",
        "plan.md",
        """---
title: Metadata
---
""",
        None,
        id="only_frontmatter",
    ),
    pytest.param(
        "no_heading",
        "plan.md",
        "Just some text without headings.",
        None,
        id="no_heading",
    ),
    pytest.param(
        "empty_file",
        "plan.md",
        "",
        None,
        id="empty_file",
    ),
    pytest.param(
        "empty_heading",
        "plan.md",
        "#\n\nContent.",
        None,
        id="empty_heading",
    ),
    pytest.param(
        "heading_with_whitespace",
        "plan.md",
        "#   Title With Spaces   \n\nContent.",
        "Title With Spaces",
        id="heading_with_whitespace",
    ),
    pytest.param(
        "second_heading_ignored",
        "plan.md",
        """# First Heading

Some content.

## Second Heading

More content.
""",
        "First Heading",
        id="second_heading_ignored",
    ),
    pytest.param(
        "missing_file",
        "nonexistent.md",
        None,
        None,
        id="missing_file",
    ),
    pytest.param(
        "implementation_plan_prefix_colon",
        "plan.md",
        "# Implementation Plan: Change Erk LS to Display PR and Plan Info\n\nContent.",
        "Change Erk LS to Display PR and Plan Info",
        id="implementation_plan_prefix_colon",
    ),
    pytest.param(
        "implementation_plan_prefix_hyphen",
        "plan.md",
        "# Implementation Plan - Migrate Test Suite to SimulatedWorkstackEnv Pattern\n\nContent.",
        "Migrate Test Suite to SimulatedWorkstackEnv Pattern",
        id="implementation_plan_prefix_hyphen",
    ),
    pytest.param(
        "implementation_plan_case_insensitive",
        "plan.md",
        "# IMPLEMENTATION PLAN: Add Real-Time Progress Output\n\nContent.",
        "Add Real-Time Progress Output",
        id="implementation_plan_case_insensitive",
    ),
    pytest.param(
        "implementation_plan_mixed_case",
        "plan.md",
        "# Implementation Plan: Convert Subprocess CLI Tests to CliRunner\n\nContent.",
        "Convert Subprocess CLI Tests to CliRunner",
        id="implementation_plan_mixed_case",
    ),
    pytest.param(
        "plan_prefix",
        "plan.md",
        "# Plan: Add User Authentication Feature\n\nContent.",
        "Add User Authentication Feature",
        id="plan_prefix",
    ),
    pytest.param(
        "plan_prefix_case_insensitive",
        "plan.md",
        "# PLAN: Add Retry Logic\n\nContent.",
        "Add Retry Logic",
        id="plan_prefix_case_insensitive",
    ),
]


@pytest.mark.parametrize(
    ("description", "filename", "contents", "expected"),
    PLAN_CASES,
)
def test_extract_pr_title_cases(tmp_path, description, filename, contents, expected):
    """Exercise extract_pr_title across the supported input variations."""
    plan = tmp_path / filename

    if contents is not None:
        plan.write_text(contents, encoding="utf-8")

    assert extract_pr_title(plan) == expected
