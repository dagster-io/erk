"""Registry of skills portable to Codex CLI.

Codex is a generic AI coding agent framework. Skills in CODEX_PORTABLE_SKILLS
work with any AI coding agent (not Claude-specific).

Skills in CLAUDE_ONLY_SKILLS reference Claude-specific features like hooks,
session logs, or Claude Code commands and cannot be ported to Codex.
"""

# Skills that work with any AI coding agent (not Claude-specific)
CODEX_PORTABLE_SKILLS: frozenset[str] = frozenset(
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

# Skills that reference Claude-specific features (hooks, session logs, commands)
CLAUDE_ONLY_SKILLS: frozenset[str] = frozenset(
    {
        "session-inspector",
        "ci-iteration",
        "command-creator",
        "cli-skill-creator",
    }
)
