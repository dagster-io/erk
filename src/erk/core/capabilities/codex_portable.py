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
    return frozenset(
        {
            "dignified-python",
            "fake-driven-testing",
            "erk-diff-analysis",
            "erk-exec",
            "erk-planning",
            "objective",
            "gh",
            "gt",
            "learned-docs",
            "dignified-code-simplifier",
            "pr-operations",
            "pr-feedback-classifier",
        }
    )


@cache
def claude_only_skills() -> frozenset[str]:
    """Skills that reference Claude-specific features (hooks, session logs, commands)."""
    return frozenset(
        {
            "session-inspector",
            "ci-iteration",
            "command-creator",
            "cli-skill-creator",
            "learn",
        }
    )
