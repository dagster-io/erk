"""Tests for review prompt assembly."""

import pytest

from erk.review.models import ParsedReview, ReviewFrontmatter
from erk.review.prompt_assembly import assemble_review_prompt


def _make_review(
    *,
    name: str,
    marker: str,
    body: str,
) -> ParsedReview:
    """Create a test review with common defaults."""
    return ParsedReview(
        frontmatter=ReviewFrontmatter(
            name=name,
            paths=("**/*.py",),
            marker=marker,
            provider="claude",
            model="claude-sonnet-4-5",
            timeout_minutes=30,
            allowed_tools="Read(*)",
            enabled=True,
        ),
        body=body,
        filename=f"{name.lower().replace(' ', '-')}.md",
    )


class TestAssemblePrPrompt:
    """Tests for PR mode prompt assembly."""

    def test_basic_prompt_assembly(self) -> None:
        """Assemble a basic review prompt with all boilerplate."""
        review = _make_review(
            name="Test Review",
            marker="<!-- test-review -->",
            body="Check for bugs in the code.",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="owner/repo",
            pr_number=123,
            base_branch=None,
        )

        # Check that key elements are present
        assert "REPO: owner/repo" in prompt
        assert "PR NUMBER: 123" in prompt
        assert "Test Review: Review code changes." in prompt
        assert "Check for bugs in the code." in prompt
        assert "<!-- test-review -->" in prompt
        assert "gh pr diff 123" in prompt
        assert "post-pr-inline-comment" in prompt
        assert "post-or-update-pr-summary" in prompt
        assert "Activity Log" in prompt

    def test_prompt_includes_review_name_in_inline_comment_format(self) -> None:
        """Prompt includes review name in inline comment format."""
        review = _make_review(
            name="Dignified Python",
            marker="<!-- dignified-python -->",
            body="Review body.",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=456,
            base_branch=None,
        )

        # The inline comment format should include the review name
        assert "**Dignified Python**" in prompt

    def test_prompt_preserves_body_content(self) -> None:
        """Prompt preserves the full review body content."""
        body = """\
## Step 1: Load Rules

Read the rules file.

## Step 2: Analyze

Check each file against the rules.

## Step 3: Report

Post findings.
"""
        review = _make_review(
            name="Multi-Step Review",
            marker="<!-- multi-step -->",
            body=body,
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=789,
            base_branch=None,
        )

        # All body content should be preserved
        assert "## Step 1: Load Rules" in prompt
        assert "## Step 2: Analyze" in prompt
        assert "## Step 3: Report" in prompt
        assert "Read the rules file." in prompt

    def test_prompt_uses_correct_pr_number(self) -> None:
        """Prompt uses the correct PR number throughout."""
        review = _make_review(
            name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=999,
            base_branch=None,
        )

        # PR number should appear in multiple places
        assert "PR NUMBER: 999" in prompt
        assert "gh pr diff 999" in prompt
        assert "--pr-number 999" in prompt


class TestAssembleLocalPrompt:
    """Tests for local mode prompt assembly."""

    def test_local_prompt_assembly(self) -> None:
        """Assemble a local review prompt with git diff commands."""
        review = _make_review(
            name="Test Review",
            marker="<!-- test-review -->",
            body="Check for bugs.",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="owner/repo",
            pr_number=None,
            base_branch="main",
        )

        # Should contain local mode elements
        assert "REPO: owner/repo" in prompt
        assert "BASE BRANCH: main" in prompt
        assert "Test Review: Review local code changes" in prompt
        assert "Check for bugs." in prompt
        assert "git diff --name-only $(git merge-base main HEAD)...HEAD" in prompt
        assert "git diff $(git merge-base main HEAD)...HEAD" in prompt

        # Should NOT contain PR mode elements
        assert "PR NUMBER:" not in prompt
        assert "gh pr diff" not in prompt
        assert "post-or-update-pr-summary" not in prompt

    def test_local_prompt_uses_base_branch(self) -> None:
        """Local prompt uses the specified base branch."""
        review = _make_review(
            name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=None,
            base_branch="develop",
        )

        assert "BASE BRANCH: develop" in prompt
        assert "git merge-base develop HEAD" in prompt

    def test_local_prompt_outputs_to_stdout(self) -> None:
        """Local prompt instructs to output violations to stdout."""
        review = _make_review(
            name="Test Review",
            marker="<!-- test -->",
            body="Body.",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=None,
            base_branch="main",
        )

        # Should have stdout-based output instructions
        assert "Output Violations" in prompt
        assert "**Test Review Violation**" in prompt
        assert "Summary" in prompt


class TestAssembleValidation:
    """Tests for parameter validation."""

    def test_raises_if_both_pr_and_base_provided(self) -> None:
        """Raises ValueError if both pr_number and base_branch provided."""
        review = _make_review(
            name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        with pytest.raises(ValueError, match="Cannot specify both"):
            assemble_review_prompt(
                review=review,
                repository="test/repo",
                pr_number=123,
                base_branch="main",
            )

    def test_raises_if_neither_pr_nor_base_provided(self) -> None:
        """Raises ValueError if neither pr_number nor base_branch provided."""
        review = _make_review(
            name="Test",
            marker="<!-- test -->",
            body="Body.",
        )

        with pytest.raises(ValueError, match="Must specify either"):
            assemble_review_prompt(
                review=review,
                repository="test/repo",
                pr_number=None,
                base_branch=None,
            )
