---
title: CI Environment Detection for Learn Workflow
read_when:
  - "running /erk:learn in CI"
  - "understanding CI vs interactive mode differences"
  - "debugging learn workflow in GitHub Actions"
---

# CI Environment Detection for Learn Workflow

The `/erk:learn` workflow behaves differently in CI (GitHub Actions) versus interactive (local terminal) environments.

## Detection Mechanism

CI mode is detected by checking environment variables:

- `CI` — set by most CI systems
- `GITHUB_ACTIONS` — set specifically by GitHub Actions

If either is set and non-empty, the workflow runs in CI mode.

## Behavioral Differences

| Behavior            | Interactive Mode | CI Mode                 |
| ------------------- | ---------------- | ----------------------- |
| User confirmations  | Prompted         | Skipped (auto-proceed)  |
| Plan save           | User confirms    | Auto-saves              |
| Blocking prompts    | Shown            | Skipped (would hang CI) |
| `CLAUDE_SESSION_ID` | Not available    | Available (CI-injected) |

## Session ID Availability

`CLAUDE_SESSION_ID` is a CI-only environment variable. Local sessions do not have this variable set. Commands that depend on session ID should use graceful fallback:

```bash
erk exec some-command --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

For local sessions, use `${CLAUDE_SESSION_ID}` string substitution in skills (supported since Claude Code 2.1.9), which resolves from the running Claude session context.

## Related Topics

- [Learn Workflow](../planning/learn-workflow.md) — Full learn workflow documentation (CI Environment Behavior section)
- [CI Workflow Patterns](workflow-gating-patterns.md) — CI gating and workflow patterns
