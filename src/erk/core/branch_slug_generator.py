"""Branch slug generation via LLM inference.

This module provides branch name slug generation using a fast LLM call
to distill plan/issue titles into meaningful 2-4 word slugs before they
enter the branch naming pipeline.

Follows the CommitMessageGenerator pattern from src/erk/core/commit_message_generator.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.naming import sanitize_worktree_name

BRANCH_SLUG_SYSTEM_PROMPT = """\
You are a branch name slug generator. Given a title, return ONLY a concise
2-4 word slug using lowercase letters and hyphens. No explanation.

Rules:
- Use 2-4 hyphenated words (e.g., "fix-auth-session", "add-plan-validation")
- Capture the distinctive essence, not generic words
- Drop filler words: "the", "a", "for", "and", "implementation", "plan"
- Prefer verbs: add, fix, refactor, update, consolidate, extract, migrate
- Never exceed 30 characters total
- Output ONLY the slug, nothing else"""


@dataclass(frozen=True)
class BranchSlugResult:
    """Result of branch slug generation.

    Attributes:
        success: Whether generation succeeded
        slug: The generated slug if successful
        error_message: Error description if generation failed
    """

    success: bool
    slug: str | None
    error_message: str | None


class BranchSlugGenerator:
    """Generates branch name slugs via LLM inference.

    This is a concrete class (not ABC) that uses PromptExecutor for
    testability. In tests, inject FakePromptExecutor with simulated prompt output.
    """

    def __init__(self, executor: PromptExecutor) -> None:
        self._executor = executor

    def generate(self, title: str) -> BranchSlugResult:
        """Generate a branch slug from a title.

        Sends the title to an LLM with the branch slug system prompt,
        then validates the output meets slug requirements.

        Args:
            title: Plan or issue title to distill into a slug

        Returns:
            BranchSlugResult with success status and slug or error
        """
        result = self._executor.execute_prompt(
            title,
            model="haiku",
            tools=None,
            cwd=None,
            system_prompt=BRANCH_SLUG_SYSTEM_PROMPT,
            dangerous=False,
        )

        if not result.success:
            return BranchSlugResult(
                success=False,
                slug=None,
                error_message=result.error or "LLM execution failed",
            )

        slug = _postprocess_slug(result.output)
        if slug is None:
            return BranchSlugResult(
                success=False,
                slug=None,
                error_message=f"Invalid LLM output: {result.output!r}",
            )

        return BranchSlugResult(
            success=True,
            slug=slug,
            error_message=None,
        )


def _postprocess_slug(raw_output: str) -> str | None:
    """Clean and validate LLM slug output.

    Post-processing steps:
    1. Strip whitespace
    2. Strip surrounding quotes and backticks
    3. Run through sanitize_worktree_name as safety net
    4. Validate: must have 2+ hyphenated words
    5. Validate: max 30 characters

    Args:
        raw_output: Raw LLM output string

    Returns:
        Validated slug string, or None if invalid
    """
    stripped = raw_output.strip()

    # Strip surrounding quotes and backticks
    stripped = stripped.strip("\"'`")

    # Run through sanitize_worktree_name as safety net
    sanitized = sanitize_worktree_name(stripped)

    # Validate: must have 2+ hyphenated words
    words = sanitized.split("-")
    if len(words) < 2:
        return None

    # Validate: max 30 characters
    if len(sanitized) > 30:
        return None

    return sanitized


def generate_slug_or_fallback(executor: PromptExecutor, title: str) -> str:
    """Generate a slug from title, falling back to raw title on failure.

    Convenience function that returns the LLM slug on success,
    or the raw title on failure (so sanitize_worktree_name handles it downstream).

    Args:
        executor: PromptExecutor for LLM inference
        title: Plan or issue title

    Returns:
        LLM-generated slug on success, raw title on failure
    """
    generator = BranchSlugGenerator(executor)
    result = generator.generate(title)
    if result.success and result.slug is not None:
        return result.slug
    return title
