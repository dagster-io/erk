"""Local plan extraction from ~/.claude/plans/.

This module provides the core plan extraction logic for ClaudeCodeSessionStore.
It extracts plans from the Claude plans directory, supporting both mtime-based
selection and session-scoped lookup via slugs.
"""

from pathlib import Path


def get_plans_dir() -> Path:
    """Return the Claude plans directory path.

    Returns:
        Path to ~/.claude/plans/
    """
    return Path.home() / ".claude" / "plans"


def get_latest_plan_content(session_id: str | None = None) -> str | None:
    """Get plan content from ~/.claude/plans/, optionally session-scoped.

    For MVP, uses mtime-based selection. Session-scoped slug extraction
    is more complex and handled separately in session_plan_extractor.py.

    Args:
        session_id: Optional session ID (reserved for future session-scoped lookup)

    Returns:
        Plan content as markdown string, or None if no plan found
    """
    # Note: session_id param is reserved for future slug-based lookup
    # For now, we use simple mtime-based selection
    _ = session_id

    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        return None

    plan_files = sorted(
        [f for f in plans_dir.glob("*.md") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not plan_files:
        return None

    return plan_files[0].read_text(encoding="utf-8")
