"""Plan summary generation via LLM inference.

This module provides AI-generated summaries for plan PRs using a fast LLM call
to distill plan content into 2-3 sentence descriptions.

Follows the BranchSlugGenerator pattern from src/erk/core/branch_slug_generator.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from erk_shared.core.prompt_executor import PromptExecutor

_MAX_SUMMARY_LENGTH = 500

PLAN_SUMMARY_SYSTEM_PROMPT = """\
You are a plan summarizer. Given a plan in markdown, return ONLY a 2-3 sentence \
summary. Focus on WHAT the plan does and WHY. Plain text, no markdown formatting. \
No bullet points. Keep it under 500 characters."""


@dataclass(frozen=True)
class PlanSummaryResult:
    """Result of plan summary generation.

    Attributes:
        success: Whether generation succeeded
        summary: The generated summary if successful
        error_message: Error description if generation failed
    """

    success: bool
    summary: str
    error_message: str


class PlanSummaryGenerator:
    """Generates plan summaries via LLM inference.

    This is a concrete class (not ABC) that uses PromptExecutor for
    testability. In tests, inject FakePromptExecutor with simulated prompt output.
    """

    def __init__(self, executor: PromptExecutor) -> None:
        self._executor = executor

    def generate(self, plan_content: str) -> PlanSummaryResult:
        """Generate a summary from plan content.

        Sends the plan content to an LLM with the summary system prompt,
        then validates and post-processes the output.

        Args:
            plan_content: Plan markdown content to summarize

        Returns:
            PlanSummaryResult with success status and summary or error
        """
        result = self._executor.execute_prompt(
            plan_content,
            model="haiku",
            tools=None,
            cwd=None,
            system_prompt=PLAN_SUMMARY_SYSTEM_PROMPT,
            dangerous=False,
        )

        if not result.success:
            return PlanSummaryResult(
                success=False,
                summary="",
                error_message=result.error or "LLM execution failed",
            )

        summary = _postprocess_summary(result.output)
        if not summary:
            return PlanSummaryResult(
                success=False,
                summary="",
                error_message=f"Invalid LLM output: {result.output!r}",
            )

        return PlanSummaryResult(
            success=True,
            summary=summary,
            error_message="",
        )


def _postprocess_summary(raw_output: str) -> str:
    """Clean and validate LLM summary output.

    Post-processing steps:
    1. Strip whitespace
    2. Validate non-empty
    3. Cap at max length

    Args:
        raw_output: Raw LLM output string

    Returns:
        Validated summary string, or empty string if invalid
    """
    stripped = raw_output.strip()

    if not stripped:
        return ""

    if len(stripped) > _MAX_SUMMARY_LENGTH:
        stripped = stripped[:_MAX_SUMMARY_LENGTH].rsplit(" ", 1)[0] + "..."

    return stripped


def generate_summary(executor: PromptExecutor, plan_content: str) -> str:
    """Generate a summary from plan content, returning empty string on failure.

    Convenience function that returns the LLM summary on success,
    or empty string on failure (graceful degradation, never blocks plan creation).

    Args:
        executor: PromptExecutor for LLM inference
        plan_content: Plan markdown content

    Returns:
        LLM-generated summary on success, empty string on failure
    """
    generator = PlanSummaryGenerator(executor)
    result = generator.generate(plan_content)
    if result.success:
        return result.summary
    return ""
