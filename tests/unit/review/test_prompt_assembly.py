"""Tests for review prompt assembly."""

import pytest

from erk.review.models import ParsedReview, ReviewFrontmatter
from erk.review.prompt_assembly import assemble_review_prompt


def _make_review(
    *,
    name: str,
    body: str,
    marker: str,
) -> ParsedReview:
    """Create a test review with sensible defaults."""
    return ParsedReview(
        frontmatter=ReviewFrontmatter(
            name=name,
            paths=("**/*.py",),
            marker=marker,
            model="claude-sonnet-4-5",
            timeout_minutes=30,
            allowed_tools="Read(*)",
            enabled=True,
        ),
        body=body,
        filename="test.md",
    )


class TestAssembleReviewPromptPRMode:
    """Tests for PR mode prompt assembly."""

    def test_basic_prompt_assembly(self) -> None:
        """Assemble a basic review prompt with all boilerplate."""
        review = _make_review(
            name="Test Review",
            body="Check for bugs in the code.",
            marker="<!-- test-review -->",
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
            body="Review body.",
            marker="<!-- dignified-python -->",
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
            body=body,
            marker="<!-- multi-step -->",
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
            body="Body.",
            marker="<!-- test -->",
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


class TestAssembleReviewPromptLocalMode:
    """Tests for local mode prompt assembly."""

    def test_local_prompt_uses_git_diff(self) -> None:
        """Local mode uses git diff commands instead of gh pr diff."""
        review = _make_review(
            name="Test Review",
            body="Check for issues.",
            marker="<!-- test -->",
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
        assert "Test Review: Review code changes." in prompt
        assert "Check for issues." in prompt
        assert "git diff --name-only" in prompt
        assert "git merge-base main HEAD" in prompt

        # Should NOT contain PR mode elements
        assert "PR NUMBER:" not in prompt
        assert "gh pr diff" not in prompt
        assert "post-pr-inline-comment" not in prompt
        assert "post-or-update-pr-summary" not in prompt

    def test_local_prompt_uses_specified_base_branch(self) -> None:
        """Local mode uses the specified base branch in git commands."""
        review = _make_review(
            name="Test",
            body="Body.",
            marker="<!-- test -->",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=None,
            base_branch="develop",
        )

        assert "BASE BRANCH: develop" in prompt
        assert "git merge-base develop HEAD" in prompt

    def test_local_prompt_outputs_violations_to_stdout(self) -> None:
        """Local mode outputs violations to stdout rather than PR comments."""
        review = _make_review(
            name="Test Review",
            body="Body.",
            marker="<!-- test -->",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=None,
            base_branch="main",
        )

        # Should have stdout violation format
        assert "--- VIOLATION ---" in prompt
        assert "--- END VIOLATION ---" in prompt
        assert "--- SUMMARY ---" in prompt
        assert "--- END SUMMARY ---" in prompt


class TestAssembleReviewPromptValidation:
    """Tests for parameter validation."""

    def test_raises_when_both_pr_and_base_specified(self) -> None:
        """Raises ValueError when both pr_number and base_branch are provided."""
        review = _make_review(
            name="Test",
            body="Body.",
            marker="<!-- test -->",
        )

        with pytest.raises(ValueError, match="Cannot specify both pr_number and base_branch"):
            assemble_review_prompt(
                review=review,
                repository="test/repo",
                pr_number=123,
                base_branch="main",
            )

    def test_raises_when_neither_pr_nor_base_specified(self) -> None:
        """Raises ValueError when neither pr_number nor base_branch is provided."""
        review = _make_review(
            name="Test",
            body="Body.",
            marker="<!-- test -->",
        )

        with pytest.raises(ValueError, match="Must specify either pr_number or base_branch"):
            assemble_review_prompt(
                review=review,
                repository="test/repo",
                pr_number=None,
                base_branch=None,
            )
