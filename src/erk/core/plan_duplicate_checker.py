"""Duplicate plan detection via LLM inference.

This module checks new plans against existing open plans using a fast
LLM call to detect semantic duplicates — plans that aim to accomplish
the same functional change, even if worded differently.

Concrete class with PromptExecutor injection, model="haiku", frozen result dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass

from erk.core.llm_json import extract_json_dict
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.plan_store.types import Plan

DUPLICATE_CHECK_SYSTEM_PROMPT = """\
You are a duplicate plan detector. Given a NEW plan and a list of EXISTING \
open plans, identify any existing plans that are semantic duplicates of the \
new plan.

A duplicate means the plans aim to accomplish the same functional change. \
Plans touching the same files for different purposes are NOT duplicates. \
Focus on intent and outcome, not surface-level word overlap.

Respond with ONLY valid JSON in this exact format:
{"duplicates": [{"plan_id": "ID", "explanation": "one sentence why"}]}

If no duplicates, respond: {"duplicates": []}

Rules:
- Only flag true semantic duplicates, not vaguely related plans
- A plan that extends or builds upon another is NOT a duplicate
- Two plans that refactor different aspects of the same module are NOT duplicates
- Be conservative: when in doubt, do NOT flag as duplicate"""

_MAX_EXISTING_PLANS = 20
_MAX_NEW_PLAN_CHARS = 2000
_MAX_EXISTING_PLAN_BODY_CHARS = 500


@dataclass(frozen=True)
class DuplicateMatch:
    """A single duplicate match between new and existing plan."""

    plan_id: str
    title: str
    url: str
    explanation: str


@dataclass(frozen=True)
class DuplicateCheckResult:
    """Result of a duplicate plan check.

    Attributes:
        has_duplicates: Whether any duplicates were found
        matches: List of matching existing plans
        error: Error description if the check failed (graceful degradation)
    """

    has_duplicates: bool
    matches: list[DuplicateMatch]
    error: str | None


class PlanDuplicateChecker:
    """Checks new plans for duplicates against existing open plans.

    This is a concrete class (not ABC) that uses PromptExecutor for
    testability. In tests, inject FakePromptExecutor with simulated prompt output.
    """

    def __init__(self, executor: PromptExecutor) -> None:
        self._executor = executor

    def check(
        self,
        new_plan_content: str,
        existing_plans: list[Plan],
    ) -> DuplicateCheckResult:
        """Check if a new plan duplicates any existing open plans.

        Args:
            new_plan_content: Full markdown content of the new plan.
            existing_plans: List of existing open plans (already filtered
                by caller — no erk-learn plans should be included).

        Returns:
            DuplicateCheckResult with matches or graceful degradation on error.
        """
        if not existing_plans:
            return DuplicateCheckResult(has_duplicates=False, matches=[], error=None)

        prompt = _build_prompt(new_plan_content, existing_plans)

        result = self._executor.execute_prompt(
            prompt,
            model="haiku",
            tools=None,
            cwd=None,
            system_prompt=DUPLICATE_CHECK_SYSTEM_PROMPT,
            dangerous=False,
        )

        if not result.success:
            return DuplicateCheckResult(
                has_duplicates=False,
                matches=[],
                error=f"LLM call failed: {result.error}",
            )

        return _parse_response(result.output, existing_plans)


def _build_prompt(
    new_plan_content: str,
    existing_plans: list[Plan],
) -> str:
    """Build the prompt sent to the LLM for duplicate detection."""
    truncated_new = new_plan_content[:_MAX_NEW_PLAN_CHARS]

    lines = [
        "## NEW PLAN",
        "",
        truncated_new,
        "",
        "## EXISTING OPEN PLANS",
        "",
    ]

    for plan in existing_plans[:_MAX_EXISTING_PLANS]:
        body_preview = (plan.body or "")[:_MAX_EXISTING_PLAN_BODY_CHARS]
        lines.append(f"### #{plan.pr_identifier}: {plan.title}")
        lines.append(body_preview)
        lines.append("")

    return "\n".join(lines)


def _parse_response(
    output: str,
    existing_plans: list[Plan],
) -> DuplicateCheckResult:
    """Parse the LLM JSON response into a DuplicateCheckResult."""
    plan_map = {plan.pr_identifier: plan for plan in existing_plans}

    parsed = extract_json_dict(output)
    if parsed is None:
        return DuplicateCheckResult(
            has_duplicates=False,
            matches=[],
            error=f"Malformed LLM response: {output[:200]}",
        )

    raw_duplicates = parsed.get("duplicates")
    if not isinstance(raw_duplicates, list):
        return DuplicateCheckResult(
            has_duplicates=False,
            matches=[],
            error="LLM response missing 'duplicates' list",
        )

    matches: list[DuplicateMatch] = []
    for entry in raw_duplicates:
        if not isinstance(entry, dict):
            continue
        plan_id = entry.get("plan_id")
        if not isinstance(plan_id, str):
            continue
        explanation = entry.get("explanation", "")
        if not isinstance(explanation, str):
            explanation = str(explanation)
        # Only include matches that reference actual existing plans
        if plan_id in plan_map:
            plan = plan_map[plan_id]
            matches.append(
                DuplicateMatch(
                    plan_id=plan_id,
                    title=plan.title,
                    url=plan.url,
                    explanation=explanation,
                )
            )

    return DuplicateCheckResult(
        has_duplicates=bool(matches),
        matches=matches,
        error=None,
    )
