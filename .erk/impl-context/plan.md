# Plan: Fix changelog-commits output size for agent consumption

## Context

The `erk-dev changelog-commits --json-output` command exists solely to serve the commit-categorizer agent. When many commits accumulate (e.g., 56 since last release), the JSON output reaches ~480KB — far exceeding the agent's context window. This causes the agent to waste 6+ tool calls trying to read the output, then resort to writing ad hoc Python scripts to extract summaries from persisted files.

The root cause is that `get_commit_details()` fetches **full commit bodies** and **complete file lists** for every commit. For categorization, the agent needs file path patterns (to detect "tests-only" or "gateway ABC" commits) and commit subjects, but not exhaustive data.

## Changes

### 1. Trim output in `get_commit_details()` (command.py:90-119)

**File:** `packages/erk-dev/src/erk_dev/commands/changelog_commits/command.py`

In `get_commit_details()`:
- **Truncate `body`** to 300 characters (with `...` suffix if truncated)

The `files_changed` list is kept intact — the agent needs the full list for pattern detection (tests-only, gateway ABC, fake files, etc.). The body is the main size driver since commit bodies can be multi-paragraph. Truncating to 300 chars preserves enough context for categorization while dramatically reducing output size.

### 2. Update agent definition to document the trimming

**File:** `.claude/agents/changelog/commit-categorizer.md`

Update the JSON schema example to show that `body` may be truncated. Add a note that the data is intentionally compact for context window efficiency.

### 3. No changes to changelog-update command

The orchestrator command (`.claude/commands/local/changelog-update.md`) needs no changes — it just launches the agent.

## Verification

1. Run `erk-dev changelog-commits --json-output` and verify output is compact (< 50KB even with many commits)
2. Run `erk-dev changelog-commits` (human-readable mode) — should be unaffected
3. Run `/local:changelog-update` end-to-end to confirm the agent can consume the output without overflow
4. Run devrun with ruff/ty to verify no lint or type errors
