"""Node slug generation via LLM inference.

This module provides node slug generation using a fast LLM call
to distill objective node descriptions into meaningful slugs.

Mirrors the BranchSlugGenerator pattern from src/erk/core/branch_slug_generator.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.naming import (
    InvalidNodeSlug,
    make_unique_slug,
    slugify_node_description,
    validate_node_slug,
)

NODE_SLUG_SYSTEM_PROMPT = """\
You are a node slug generator for a project roadmap. Given a list of step \
descriptions (one per line), return ONLY a concise slug for each (one per line). \
No explanation, no numbering, no extra text.

Rules:
- Use 2-4 hyphenated lowercase words per slug (e.g., "add-user-model", "wire-cli")
- Capture the distinctive essence, not generic words
- Drop filler words: "the", "a", "for", "and", "implementation"
- Prefer verbs: add, fix, refactor, update, wire, create, extract, migrate
- Never exceed 30 characters per slug
- Output ONLY the slugs, one per line, matching the input order"""


@dataclass(frozen=True)
class NodeSlugResult:
    """Result of node slug generation.

    Attributes:
        success: Whether generation succeeded
        slugs: The generated slugs if successful
        error_message: Error description if generation failed
    """

    success: bool
    slugs: list[str]
    error_message: str | None


class NodeSlugGenerator:
    """Generates node slugs via LLM inference with deterministic fallback.

    This is a concrete class (not ABC) that uses PromptExecutor for
    testability. In tests, inject FakePromptExecutor with simulated prompt output.
    """

    def __init__(self, executor: PromptExecutor) -> None:
        self._executor = executor

    def generate(self, descriptions: list[str]) -> NodeSlugResult:
        """Generate slugs for a batch of node descriptions.

        Sends all descriptions as a newline-separated list to an LLM,
        then validates and deduplicates the output.

        Args:
            descriptions: List of node descriptions to generate slugs for.

        Returns:
            NodeSlugResult with success status and slugs or error.
        """
        if not descriptions:
            return NodeSlugResult(success=True, slugs=[], error_message=None)

        prompt = "\n".join(descriptions)
        result = self._executor.execute_prompt(
            prompt,
            model="haiku",
            tools=None,
            cwd=None,
            system_prompt=NODE_SLUG_SYSTEM_PROMPT,
            dangerous=False,
        )

        if not result.success:
            return self._fallback(descriptions)

        raw_slugs = [line.strip() for line in result.output.strip().splitlines() if line.strip()]

        # If LLM returned wrong number of slugs, fall back
        if len(raw_slugs) != len(descriptions):
            return self._fallback(descriptions)

        # Validate and deduplicate
        slugs: list[str] = []
        seen: set[str] = set()
        for i, raw_slug in enumerate(raw_slugs):
            slug = _postprocess_node_slug(raw_slug)
            if slug is None:
                # Individual slug failed validation, use deterministic fallback
                slug = slugify_node_description(descriptions[i])
            slug = make_unique_slug(slug, seen)
            seen.add(slug)
            slugs.append(slug)

        return NodeSlugResult(success=True, slugs=slugs, error_message=None)

    def _fallback(self, descriptions: list[str]) -> NodeSlugResult:
        """Generate slugs deterministically when LLM fails."""
        slugs: list[str] = []
        seen: set[str] = set()
        for desc in descriptions:
            slug = slugify_node_description(desc)
            slug = make_unique_slug(slug, seen)
            seen.add(slug)
            slugs.append(slug)
        return NodeSlugResult(success=True, slugs=slugs, error_message=None)


def _postprocess_node_slug(raw_output: str) -> str | None:
    """Clean and validate LLM node slug output.

    Post-processing steps:
    1. Strip whitespace
    2. Strip surrounding quotes and backticks
    3. Lowercase
    4. Replace unsafe chars with hyphens
    5. Validate against node slug pattern

    Args:
        raw_output: Raw LLM output string for a single slug.

    Returns:
        Validated slug string, or None if invalid.
    """
    stripped = raw_output.strip()
    # Strip surrounding quotes and backticks
    stripped = stripped.strip("\"'`")
    # Lowercase
    stripped = stripped.lower()
    # Remove any numbering prefix like "1. " or "1) "
    if stripped and stripped[0].isdigit():
        stripped = re.sub(r"^\d+[.)]\s*", "", stripped)
    # Replace non-alphanumeric (except hyphens) with hyphens
    stripped = re.sub(r"[^a-z0-9-]+", "-", stripped)
    stripped = re.sub(r"-+", "-", stripped)
    stripped = stripped.strip("-")

    validation = validate_node_slug(stripped)
    if isinstance(validation, InvalidNodeSlug):
        return None
    return validation.slug
