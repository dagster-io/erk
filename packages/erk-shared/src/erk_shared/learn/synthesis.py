"""Synthesize documentation gaps from session XML using LLM."""

from erk_shared.learn.prompts import LEARN_SYNTHESIS_PROMPT
from erk_shared.prompt_executor.abc import PromptExecutor


def synthesize_session(
    session_xml: str,
    branch_name: str,
    pr_number: int,
    prompt_executor: PromptExecutor,
) -> str | None:
    """Synthesize documentation gaps from session XML.

    Uses Claude to analyze the session content and extract actionable
    documentation improvements.

    Args:
        session_xml: XML-formatted session content from session_to_xml()
        branch_name: Git branch name for context
        pr_number: PR number for context
        prompt_executor: Executor for LLM calls

    Returns:
        Synthesized documentation gaps as markdown, or None if synthesis fails
    """
    prompt = LEARN_SYNTHESIS_PROMPT.format(
        session_xml=session_xml,
        branch_name=branch_name,
        pr_number=pr_number,
    )

    result = prompt_executor.execute_prompt(prompt, model="haiku")

    if not result.success:
        return None

    output = result.output.strip()
    if not output:
        return None

    return output
