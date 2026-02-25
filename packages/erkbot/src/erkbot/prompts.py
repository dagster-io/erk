"""Erk-specific system prompts for erkbot agent."""

from pathlib import Path


def _load_prompt(filename: str) -> str:
    """Load prompt from resources directory."""
    prompt_path = Path(__file__).parent / "resources" / filename
    return prompt_path.read_text(encoding="utf-8")


ERK_SYSTEM_PROMPT = _load_prompt("erk_system_prompt.md")


def get_erk_system_prompt(*, repo_root: Path) -> str:
    """Get erk system prompt, checking .erk/prompt-hooks/ first.

    Args:
        repo_root: Repository root to check for custom prompt.

    Returns:
        Custom prompt if .erk/prompt-hooks/erk-system-prompt.md exists,
        otherwise the built-in default prompt.
    """
    custom_prompt_path = repo_root / ".erk" / "prompt-hooks" / "erk-system-prompt.md"
    if custom_prompt_path.exists():
        return custom_prompt_path.read_text(encoding="utf-8")
    return ERK_SYSTEM_PROMPT
