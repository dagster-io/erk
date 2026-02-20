"""Instruction enrichment via lightweight inference.

Extracts clean titles and summaries from raw one-shot instructions,
which may contain noisy input like pasted PR review feedback, GitHub
UI artifacts, timestamps, and usernames.

Uses Haiku for fast, cheap inference with a fallback path for when
inference fails or output is unparseable.
"""

from __future__ import annotations

from dataclasses import dataclass

from erk_shared.core.prompt_executor import PromptExecutor, PromptResult

# Short instructions that don't need enrichment
_SHORT_CIRCUIT_MAX_LEN = 60

_SYSTEM_PROMPT = """\
You are a task title extractor. Given a raw instruction that may contain noise \
(GitHub UI artifacts, timestamps, usernames, formatting), extract the core \
actionable task.

Output exactly two lines:
TITLE: <imperative-mood title, max 60 chars>
SUMMARY: <1-3 sentence summary of the task>

Rules:
- Title must be imperative mood (e.g. "Fix", "Add", "Update")
- Title must be max 60 characters
- Strip all noise: timestamps, usernames, GitHub UI text, markdown artifacts
- Focus on the actionable engineering task
- If the input is already clean, preserve it as-is"""


@dataclass(frozen=True)
class EnrichmentRequest:
    """Request to enrich a raw instruction."""

    raw_instruction: str


@dataclass(frozen=True)
class EnrichedInstruction:
    """Result of instruction enrichment.

    Attributes:
        title: Clean short title, max 60 chars (for issue/PR/branch)
        summary: 1-3 sentence summary (for issue/PR bodies)
        raw_instruction: Original input, preserved verbatim
    """

    title: str
    summary: str
    raw_instruction: str


class InstructionEnricher:
    """Enriches raw instructions into clean titles and summaries.

    Uses lightweight inference (Haiku) to extract actionable task
    descriptions from potentially noisy input. Falls back to simple
    truncation when inference fails or is unnecessary.
    """

    def __init__(self, executor: PromptExecutor) -> None:
        self._executor = executor

    def enrich(self, request: EnrichmentRequest) -> EnrichedInstruction:
        """Enrich a raw instruction into a clean title and summary.

        Short-circuits for already-clean single-line instructions (<=60 chars).
        Falls back to truncation if inference fails or output is unparseable.
        """
        raw = request.raw_instruction

        # Short-circuit: clean single-line input doesn't need inference
        if len(raw) <= _SHORT_CIRCUIT_MAX_LEN and "\n" not in raw:
            return EnrichedInstruction(
                title=raw,
                summary=raw,
                raw_instruction=raw,
            )

        # Attempt inference
        result = self._call_inference(raw)
        if result is not None:
            return result

        # Fallback: first line truncated
        return self._fallback(raw)

    def _call_inference(self, raw: str) -> EnrichedInstruction | None:
        """Call Haiku to extract title and summary. Returns None on failure."""
        result: PromptResult = self._executor.execute_prompt(
            raw,
            model="haiku",
            tools=None,
            cwd=None,
            system_prompt=_SYSTEM_PROMPT,
            dangerous=False,
        )

        if not result.success:
            return None

        return self._parse_output(result.output, raw)

    def _parse_output(self, output: str, raw: str) -> EnrichedInstruction | None:
        """Parse TITLE:/SUMMARY: format from model output.

        Returns None if the output doesn't contain the expected markers.
        """
        title: str | None = None
        summary: str | None = None

        for line in output.strip().splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("TITLE:"):
                title = stripped[len("TITLE:") :].strip()
            elif stripped.upper().startswith("SUMMARY:"):
                summary = stripped[len("SUMMARY:") :].strip()

        if title is None or summary is None:
            return None

        # Enforce max length on title
        if len(title) > _SHORT_CIRCUIT_MAX_LEN:
            title = title[:57] + "..."

        return EnrichedInstruction(
            title=title,
            summary=summary,
            raw_instruction=raw,
        )

    def _fallback(self, raw: str) -> EnrichedInstruction:
        """Fallback enrichment using simple truncation."""
        return fallback_enrichment(raw)


def fallback_enrichment(raw: str) -> EnrichedInstruction:
    """Fallback enrichment using simple truncation.

    Usable standalone (e.g., in dry-run mode) without requiring
    an InstructionEnricher instance or PromptExecutor.
    """
    first_line = raw.split("\n", maxsplit=1)[0].strip()
    if len(first_line) > _SHORT_CIRCUIT_MAX_LEN:
        title = first_line[:57] + "..."
    else:
        title = first_line

    summary = raw[:200].strip()
    if len(raw) > 200:
        summary += "..."

    return EnrichedInstruction(
        title=title,
        summary=summary,
        raw_instruction=raw,
    )
