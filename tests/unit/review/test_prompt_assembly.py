"""Tests for review prompt assembly."""

from erk.review.models import ParsedReview, ReviewFrontmatter
from erk.review.prompt_assembly import assemble_review_prompt


class TestAssembleReviewPrompt:
    """Tests for prompt assembly."""

    def test_basic_prompt_assembly(self) -> None:
        """Assemble a basic review prompt with all boilerplate."""
        review = ParsedReview(
            frontmatter=ReviewFrontmatter(
                name="Test Review",
                paths=("**/*.py",),
                marker="<!-- test-review -->",
                model="claude-sonnet-4-5",
                timeout_minutes=30,
                allowed_tools="Read(*)",
                enabled=True,
            ),
            body="Check for bugs in the code.",
            filename="test.md",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="owner/repo",
            pr_number=123,
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
        review = ParsedReview(
            frontmatter=ReviewFrontmatter(
                name="Dignified Python",
                paths=("**/*.py",),
                marker="<!-- dignified-python -->",
                model="claude-sonnet-4-5",
                timeout_minutes=30,
                allowed_tools="Read(*)",
                enabled=True,
            ),
            body="Review body.",
            filename="dignified-python.md",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=456,
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
        review = ParsedReview(
            frontmatter=ReviewFrontmatter(
                name="Multi-Step Review",
                paths=("**/*.py",),
                marker="<!-- multi-step -->",
                model="claude-sonnet-4-5",
                timeout_minutes=30,
                allowed_tools="Read(*)",
                enabled=True,
            ),
            body=body,
            filename="multi-step.md",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=789,
        )

        # All body content should be preserved
        assert "## Step 1: Load Rules" in prompt
        assert "## Step 2: Analyze" in prompt
        assert "## Step 3: Report" in prompt
        assert "Read the rules file." in prompt

    def test_prompt_uses_correct_pr_number(self) -> None:
        """Prompt uses the correct PR number throughout."""
        review = ParsedReview(
            frontmatter=ReviewFrontmatter(
                name="Test",
                paths=("**/*.py",),
                marker="<!-- test -->",
                model="claude-sonnet-4-5",
                timeout_minutes=30,
                allowed_tools="Read(*)",
                enabled=True,
            ),
            body="Body.",
            filename="test.md",
        )

        prompt = assemble_review_prompt(
            review=review,
            repository="test/repo",
            pr_number=999,
        )

        # PR number should appear in multiple places
        assert "PR NUMBER: 999" in prompt
        assert "gh pr diff 999" in prompt
        assert "--pr-number 999" in prompt
