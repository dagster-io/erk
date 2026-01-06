"""Shared prompts for gt kit CLI commands."""

from pathlib import Path


def _load_prompt(filename: str) -> str:
    """Load prompt from file in the same directory as this module."""
    prompt_path = Path(__file__).parent / filename
    return prompt_path.read_text()


COMMIT_MESSAGE_SYSTEM_PROMPT = _load_prompt("commit_message_prompt.md")

MAX_DIFF_CHARS = 1_000_000  # ~300K tokens - supports very large PRs


def get_commit_message_prompt(repo_root: Path) -> str:
    """Get commit message prompt, checking .erk/prompt-hooks/ first.

    Args:
        repo_root: Repository root to check for custom prompt

    Returns:
        Custom prompt if .erk/prompt-hooks/commit-message-prompt.md exists,
        otherwise the built-in default prompt.
    """
    custom_prompt_path = repo_root / ".erk" / "prompt-hooks" / "commit-message-prompt.md"
    if custom_prompt_path.exists():
        return custom_prompt_path.read_text(encoding="utf-8")
    return COMMIT_MESSAGE_SYSTEM_PROMPT


def truncate_diff(diff: str, max_chars: int = MAX_DIFF_CHARS) -> tuple[str, bool]:
    """Truncate diff if too large. Returns (diff, was_truncated)."""
    if len(diff) <= max_chars:
        return diff, False

    keep = max_chars - 200
    start = int(keep * 0.7)
    end = keep - start

    msg = f"\n\n[... TRUNCATED {len(diff) - keep:,} chars ...]\n\n"
    return diff[:start] + msg + diff[-end:], True
