"""Registry of skills portable to Codex CLI.

Codex is a generic AI coding agent framework. Skills in codex_portable_skills()
work with any AI coding agent (not Claude-specific).

Skills in claude_only_skills() reference Claude-specific features like hooks,
session logs, or Claude Code commands and cannot be ported to Codex.
"""

from functools import cache


@cache
def codex_portable_skills() -> frozenset[str]:
    """Skills that work with any AI coding agent (not Claude-specific)."""
    # Skills migrated to npx distribution don't need codex-portable tracking;
    # npx handles distribution directly. Remove skills from here as they migrate.
    return frozenset(
        {
            "fake-driven-testing",
            "erk-diff-analysis",
            "erk-exec",
            "objective",
            "gh",
            "gt",
            "dignified-code-simplifier",
            "pr-operations",
            "pr-feedback-classifier",
            # Tombstone: distributed to all repos to overwrite stale copies
            "erk-planning",
        }
    )


@cache
def claude_only_skills() -> frozenset[str]:
    """Skills that reference Claude-specific features (hooks, session logs, commands)."""
    return frozenset()
