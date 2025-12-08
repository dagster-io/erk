"""Turn execution logic for objectives.

A turn evaluates the current codebase against an objective's desired state
and generates a bounded plan if a gap is found.

Note: The actual LLM call happens in the CLI layer, not here. This module
builds the prompt and handles post-turn operations.
"""

from dataclasses import dataclass

from erk_shared.objectives.types import (
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)


@dataclass(frozen=True)
class TurnPrompt:
    """Structured prompt for running a turn.

    Contains all the information needed for Claude to evaluate the objective
    and generate a plan.
    """

    objective_name: str
    objective_type: ObjectiveType
    system_prompt: str
    user_prompt: str


def build_turn_prompt(
    definition: ObjectiveDefinition,
    notes: ObjectiveNotes,
) -> TurnPrompt:
    """Build the evaluation prompt for a turn.

    Combines the objective definition, accumulated notes, and plan sizing
    guidance into a structured prompt for Claude.

    Args:
        definition: The objective definition
        notes: Accumulated knowledge from previous turns

    Returns:
        TurnPrompt ready for Claude evaluation
    """
    # Build system prompt
    system_parts = [
        "You are evaluating the current codebase against an objective.",
        "",
        f"**Objective:** {definition.name}",
        f"**Type:** {definition.objective_type.value}",
        "",
        "## Desired State",
        definition.desired_state,
        "",
        "## Rationale",
        definition.rationale,
    ]

    # Add scope if defined
    if definition.scope_includes or definition.scope_excludes:
        system_parts.append("")
        system_parts.append("## Scope")
        if definition.scope_includes:
            system_parts.append("### In Scope")
            for item in definition.scope_includes:
                system_parts.append(f"- {item}")
        if definition.scope_excludes:
            system_parts.append("### Out of Scope")
            for item in definition.scope_excludes:
                system_parts.append(f"- {item}")

    # Add examples if present
    if definition.examples:
        system_parts.append("")
        system_parts.append("## Examples")
        for example in definition.examples:
            system_parts.append(example)

    # Add accumulated notes
    if notes.entries:
        system_parts.append("")
        system_parts.append("## Accumulated Knowledge from Previous Turns")
        for entry in notes.entries:
            system_parts.append(f"### {entry.timestamp}")
            system_parts.append(entry.content)
            if entry.source_turn:
                system_parts.append(f"*Source: {entry.source_turn}*")

    system_prompt = "\n".join(system_parts)

    # Build user prompt (evaluation + plan sizing)
    user_parts = [
        "## Evaluation Task",
        "",
        definition.evaluation_prompt,
        "",
        "## Plan Sizing Guidelines",
        "",
        definition.plan_sizing_prompt,
        "",
        "## Instructions",
        "",
        "1. Evaluate the current codebase against the desired state.",
        "2. Identify specific gaps that need to be addressed.",
        "3. Generate a bounded, achievable plan that makes progress.",
        "",
        "If the objective is complete (no gaps found), respond with:",
        "```",
        "STATUS: COMPLETE",
        "No remaining gaps identified.",
        "```",
        "",
        "If gaps exist, respond with:",
        "```",
        "STATUS: GAPS_FOUND",
        "",
        "## Gap Analysis",
        "<describe the gaps>",
        "",
        "## Proposed Plan",
        "<the implementation plan>",
        "```",
    ]

    user_prompt = "\n".join(user_parts)

    return TurnPrompt(
        objective_name=definition.name,
        objective_type=definition.objective_type,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


def format_turn_output(prompt: TurnPrompt) -> str:
    """Format the turn prompt for display.

    Args:
        prompt: The turn prompt to format

    Returns:
        Human-readable formatted output
    """
    lines = [
        f"# Turn: {prompt.objective_name}",
        f"Type: {prompt.objective_type.value}",
        "",
        "---",
        "",
        "## System Prompt",
        "",
        prompt.system_prompt,
        "",
        "---",
        "",
        "## User Prompt",
        "",
        prompt.user_prompt,
    ]
    return "\n".join(lines)


def build_claude_prompt(prompt: TurnPrompt) -> str:
    """Build a single prompt string for Claude CLI from a TurnPrompt.

    Combines system prompt context with user evaluation task into
    a format suitable for passing directly to Claude CLI.

    Args:
        prompt: The turn prompt containing system and user components

    Returns:
        Combined prompt string for Claude CLI
    """
    parts = [
        prompt.system_prompt,
        "",
        "---",
        "",
        prompt.user_prompt,
    ]
    return "\n".join(parts)
