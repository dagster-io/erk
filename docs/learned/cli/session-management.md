---
title: Session ID Availability and Propagation
last_audited: "2026-02-16 04:53 PT"
audit_result: clean
read_when:
  - "adding session ID to a new exec script or hook"
  - "debugging 'session ID required' errors"
  - "deciding whether a command should require or optionally accept session ID"
  - "understanding how session ID flows from Claude Code to erk"
tripwires:
  - action: "using os.environ to read CLAUDE_SESSION_ID"
    warning: "CLAUDE_SESSION_ID is NOT an environment variable. It's a Claude Code string substitution in commands/skills, and arrives via stdin JSON in hooks."
  - action: "using ls -t or mtime to find the current session"
    warning: "Use the ClaudeInstallation gateway or the session-id-injector-hook's scratch file instead. Mtime-based discovery is racy in parallel sessions."
  - action: "making session_id a required parameter for a new command"
    warning: "Check the fail-hard vs degrade decision table below. Most commands should accept session_id as optional."
---

# Session ID Availability and Propagation

Session IDs originate in Claude Code and must traverse multiple boundaries to reach erk code. The propagation mechanism differs by context, and getting it wrong produces confusing "session ID required" errors that only appear in certain execution environments.

## Why This Is Cross-Cutting

Session ID handling touches three distinct systems that must agree on the protocol:

1. **Claude Code** performs string substitution on `${CLAUDE_SESSION_ID}` in commands/skills
2. **Hook framework** receives session ID via stdin JSON and injects it into `HookContext`
3. **Exec scripts** accept `--session-id` as a CLI option, passed explicitly by the agent

Each system uses a different mechanism, and code that assumes the wrong one silently fails.

## Propagation Paths

| Origin → Destination              | Mechanism                                                              | Key Detail                                                                    |
| --------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Claude Code → Slash command/skill | `${CLAUDE_SESSION_ID}` string substitution                             | Not a shell env var — substituted before shell sees it                        |
| Claude Code → Hook                | stdin JSON `{"session_id": "..."}`                                     | `@hook_command` decorator extracts automatically via `HookContext`            |
| Hook → Scratch file               | `session_id_injector_hook` writes to `.erk/scratch/current-session-id` | Worktree-scoped persistence for CLI tools that run outside hook context       |
| Agent → Exec script               | Explicit `--session-id` CLI option                                     | Agent reads session ID from hook reminders (`📌 session: <id>`) and passes it |
| CI → Exec script                  | `capture-session-info` discovery                                       | Uses `ClaudeInstallation` gateway to find latest session by mtime             |

## Fail-Hard vs Graceful Degradation

When designing a command that uses session ID, the critical decision is whether missing session ID should be fatal.

| Fail hard when...                                                         | Degrade gracefully when...                               |
| ------------------------------------------------------------------------- | -------------------------------------------------------- |
| Core functionality requires session context (e.g., `impl-signal started`) | Feature enhances but isn't required (markers, telemetry) |
| Data corruption risk without session scoping                              | Command can produce useful output without session        |
| User explicitly requested a session-dependent operation                   | Session ID is only used for scratch file scoping         |

<!-- Source: src/erk/cli/commands/exec/scripts/impl_signal.py, _signal_started -->

See `_signal_started()` in `impl_signal.py` for the fail-hard pattern — it validates session ID and outputs a structured error JSON before exiting.

The `|| true` bash pattern (`erk exec impl-signal started --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true`) is used in commands/skills where session tracking is best-effort. This ensures the command workflow continues even when session ID is unavailable.

## Session Discovery Without Explicit ID

Two mechanisms exist for finding sessions without an explicit `--session-id`:

1. **Scratch file** (`.erk/scratch/current-session-id`): Written by the session-id-injector hook on each prompt. Fast, worktree-scoped, but only reflects the _last_ session that ran in this worktree.

2. **ClaudeInstallation gateway**: Enumerates `~/.claude/projects/<encoded-path>/*.jsonl` and picks the most recent by mtime. Used by `capture-session-info` and `find-project-dir` exec scripts.

<!-- Source: src/erk/cli/commands/exec/scripts/session_id_injector_hook.py, session_id_injector_hook -->
<!-- Source: src/erk/cli/commands/exec/scripts/capture_session_info.py, capture_session -->

**Both are racy in parallel sessions.** When multiple Claude sessions target the same worktree, mtime-based discovery may return the wrong session. The explicit `--session-id` parameter is the only reliable mechanism.

## Testing Session-Dependent Code

Tests must never depend on `${CLAUDE_SESSION_ID}` substitution — it only works inside Claude Code. Always pass a literal session ID string (e.g., `--session-id=test-123`) when invoking session-dependent commands in tests.

<!-- Source: src/erk/hooks/decorators.py, HookContext -->

For hook tests, the `HookContext` dataclass accepts `session_id` directly, so fakes can inject any value without needing Claude's stdin JSON protocol.

## Related Documentation

- [Session ID Substitution](../commands/session-id-substitution.md) — Common mistakes when using `${CLAUDE_SESSION_ID}` in hooks vs commands
- [Scratch Storage](../planning/scratch-storage.md) — Session-scoped scratch directory layout
- [Session Preprocessing](../sessions/preprocessing.md) — Processing session JSONL files
