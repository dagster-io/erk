"""Commit-history relevance check for plans via LLM inference.

This module checks whether a plan's work has already been implemented
by comparing plan content against recent commits merged to the trunk
branch. This is a separate concern from duplicate detection (plan-vs-plan)
so it has its own class, system prompt, and result type.

Mirrors the PlanDuplicateChecker pattern: concrete class, PromptExecutor
injection, model="haiku", frozen result dataclass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from erk_shared.core.prompt_executor import PromptExecutor

RELEVANCE_CHECK_SYSTEM_PROMPT = """\
You are a commit-history relevance checker. Given a PLAN and a list of \
RECENT COMMITS from the trunk branch, determine whether the plan's work \
has already been implemented by those commits.

Compare the plan's intent and goals against what the commits accomplished. \
A plan is "already implemented" only if the commits fully address the \
plan's primary objective. Partial overlap is NOT sufficient.

Respond with ONLY valid JSON in this exact format:
{
  "already_implemented": true,
  "relevant_commits": [{"sha": "abc1234", "explanation": "why"}]
}

If no relevant commits, respond: {"already_implemented": false, "relevant_commits": []}

Rules:
- Only flag as already_implemented if commits fully cover the plan's goal
- Commits that touch similar files for different purposes are NOT relevant
- A commit that partially addresses the plan is NOT sufficient
- Be conservative: when in doubt, say NOT already implemented"""

_MAX_PLAN_CHARS = 2000
_MAX_COMMITS = 20


@dataclass(frozen=True)
class RelevantCommit:
    """A commit relevant to the plan's work."""

    sha: str
    message: str
    explanation: str


@dataclass(frozen=True)
class RelevanceCheckResult:
    """Result of a commit-history relevance check.

    Attributes:
        already_implemented: Whether the plan's work is already implemented
        relevant_commits: Commits relevant to the plan
        error: Error description if the check failed (graceful degradation)
    """

    already_implemented: bool
    relevant_commits: list[RelevantCommit]
    error: str | None


class PlanRelevanceChecker:
    """Checks whether a plan's work has already been implemented via recent commits.

    This is a concrete class (not ABC) that uses PromptExecutor for
    testability. In tests, inject FakePromptExecutor with simulated prompt output.
    """

    def __init__(self, executor: PromptExecutor) -> None:
        self._executor = executor

    def check(
        self,
        plan_content: str,
        recent_commits: list[dict[str, str]],
    ) -> RelevanceCheckResult:
        """Check if a plan's work has already been implemented.

        Args:
            plan_content: Full markdown content of the plan.
            recent_commits: List of commit info dicts with keys: sha, message, author, date.

        Returns:
            RelevanceCheckResult with relevant commits or graceful degradation on error.
        """
        if not recent_commits:
            return RelevanceCheckResult(
                already_implemented=False, relevant_commits=[], error=None
            )

        prompt = _build_prompt(plan_content, recent_commits)

        result = self._executor.execute_prompt(
            prompt,
            model="haiku",
            tools=None,
            cwd=None,
            system_prompt=RELEVANCE_CHECK_SYSTEM_PROMPT,
            dangerous=False,
        )

        if not result.success:
            return RelevanceCheckResult(
                already_implemented=False,
                relevant_commits=[],
                error=f"LLM call failed: {result.error}",
            )

        return _parse_response(result.output, recent_commits)


def _build_prompt(
    plan_content: str,
    recent_commits: list[dict[str, str]],
) -> str:
    """Build the prompt sent to the LLM for relevance checking."""
    truncated_plan = plan_content[:_MAX_PLAN_CHARS]

    lines = [
        "## PLAN",
        "",
        truncated_plan,
        "",
        "## RECENT TRUNK COMMITS",
        "",
    ]

    for commit in recent_commits[:_MAX_COMMITS]:
        lines.append(f"- {commit['sha']}: {commit['message']}")

    return "\n".join(lines)


def _parse_response(
    output: str,
    recent_commits: list[dict[str, str]],
) -> RelevanceCheckResult:
    """Parse the LLM JSON response into a RelevanceCheckResult."""
    commit_map = {commit["sha"]: commit for commit in recent_commits}

    # Strip markdown code fences if present
    stripped = output.strip()
    if stripped.startswith("```"):
        fence_lines = stripped.splitlines()
        stripped = "\n".join(fence_lines[1:-1]).strip()

    parsed = _safe_json_parse(stripped)
    if parsed is None:
        return RelevanceCheckResult(
            already_implemented=False,
            relevant_commits=[],
            error=f"Malformed LLM response: {output[:200]}",
        )

    already_implemented = parsed.get("already_implemented")
    if not isinstance(already_implemented, bool):
        return RelevanceCheckResult(
            already_implemented=False,
            relevant_commits=[],
            error="LLM response missing 'already_implemented' boolean",
        )

    raw_commits = parsed.get("relevant_commits")
    if not isinstance(raw_commits, list):
        return RelevanceCheckResult(
            already_implemented=False,
            relevant_commits=[],
            error="LLM response missing 'relevant_commits' list",
        )

    relevant: list[RelevantCommit] = []
    for entry in raw_commits:
        if not isinstance(entry, dict):
            continue
        sha = entry.get("sha")
        if not isinstance(sha, str):
            continue
        explanation = entry.get("explanation", "")
        if not isinstance(explanation, str):
            explanation = str(explanation)
        # Only include commits that reference actual input commits
        if sha in commit_map:
            relevant.append(
                RelevantCommit(
                    sha=sha,
                    message=commit_map[sha]["message"],
                    explanation=explanation,
                )
            )

    return RelevanceCheckResult(
        already_implemented=already_implemented and bool(relevant),
        relevant_commits=relevant,
        error=None,
    )


def _safe_json_parse(text: str) -> dict | None:
    """Parse JSON without raising exceptions.

    This is an error boundary: json.loads can fail on malformed LLM output,
    so catching ValueError here is appropriate (third-party API compatibility).
    """
    if not text:
        return None
    if not text.startswith("{"):
        return None
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed
