---
title: CI Environment Detection for Learn Workflow
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "running /erk:learn in CI"
  - "understanding CI vs interactive mode differences"
  - "debugging learn workflow in GitHub Actions"
---

# CI Environment Detection for Learn Workflow

## The Cross-Cutting Pattern

Erk uses **two different CI detection mechanisms** depending on the execution context:

1. **Python code**: Uses `in_github_actions()` from `packages/erk-shared/src/erk_shared/env.py`
2. **Bash commands/skills**: Uses shell environment variable checks in command text

This bifurcation exists because:

- **Python commands** execute in a Python interpreter with access to imported functions
- **Slash commands** (like `/erk:learn`) generate bash command strings that Claude executes — they cannot import Python functions

## Why Learn Uses Bash-Based Detection

<!-- Source: .claude/commands/erk/learn.md, CI Detection sections -->

The `/erk:learn` command instructs Claude to run this bash check:

```bash
([ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]) && echo "CI_MODE" || echo "INTERACTIVE"
```

**Why not use `in_github_actions()`?** Slash commands emit bash that Claude executes. They cannot call Python functions directly. The detection logic must be expressed as shell conditionals in the command text.

**Why check both `CI` and `GITHUB_ACTIONS`?** The bash-based check is more permissive than the Python version:

- `CI` is set by most CI systems (Travis, CircleCI, GitHub Actions, etc.)
- `GITHUB_ACTIONS` is GitHub-specific but more reliable for GitHub Actions detection
- The OR logic provides broader CI detection for future-proofing

Compare to the Python version in `packages/erk-shared/src/erk_shared/env.py`, which only checks `GITHUB_ACTIONS == "true"`. This narrower check is sufficient for Python CLI commands because they always run in GitHub Actions when running in CI (not other CI systems).

## Behavioral Differences

| Behavior           | Interactive Mode | CI Mode                 |
| ------------------ | ---------------- | ----------------------- |
| User confirmations | Prompted         | Skipped (auto-proceed)  |
| Plan save          | User confirms    | Auto-saves              |
| Blocking prompts   | Shown            | Skipped (would hang CI) |

**Why auto-proceed in CI?** GitHub Actions has no interactive terminal. Commands that prompt for input (`click.confirm()`, `input()`, etc.) will hang indefinitely waiting for stdin that never arrives.

**Why skip confirmations entirely?** The learn workflow was designed to be safe to run automatically — it creates a plan issue but doesn't merge code or modify production state. Auto-proceeding in CI reduces friction without introducing risk.

## Session ID Availability in CI

`CLAUDE_SESSION_ID` is available as an environment variable **only in CI environments**. Local Claude Code sessions do not export this variable to shell commands.

**For slash commands** (which generate bash), use the `${CLAUDE_SESSION_ID}` string substitution pattern:

```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" ...
```

Claude Code's skill processor replaces this string with the actual session ID before execution. This works in both local and CI contexts.

**For Python commands**, session IDs are passed as explicit parameters or retrieved from Claude Code's context injection (not environment variables).

See [Session ID Substitution](../commands/session-id-substitution.md) for the complete pattern across different contexts.

## When This Pattern Fails

If you see `/erk:learn` hanging in CI:

1. **Check the workflow logs** for "INTERACTIVE" instead of "CI_MODE" — indicates environment variables aren't set
2. **Verify `GITHUB_ACTIONS` is set** in the workflow file (GitHub Actions sets this automatically, but custom containers might not inherit it)
3. **Look for blocking prompts** that bypassed the CI check (e.g., `click.confirm()` without `in_github_actions()` guard)

## Related Documentation

- [CI-Aware Commands](../cli/ci-aware-commands.md) — General pattern for Python commands with `in_github_actions()`
- [Learn Workflow](../planning/learn-workflow.md) — Full learn workflow with CI behavior details
- [Session ID Substitution](../commands/session-id-substitution.md) — How `${CLAUDE_SESSION_ID}` works across contexts
