---
title: Raw Extraction Plan Command
read_when:
  - "using /erk:create-raw-extraction-plan command"
  - "working with erk pr land --extract"
  - "storing raw session data"
---

# Raw Extraction Plan Command

## Purpose

`/erk:create-raw-extraction-plan` captures preprocessed session data in a GitHub issue WITHOUT analysis. Used by `erk pr land --extract` for raw context storage.

## When to Use

**Use raw extraction when:**

- Landing PRs with `--extract` flag (automated)
- Want to defer analysis to later
- Building context corpus for training/research

**Use analyzed extraction when:**

- Actively identifying documentation gaps
- Want specific recommendations with draft content
- Doing post-session retrospective

## Command: `/erk:create-raw-extraction-plan`

Auto-selects sessions using same logic as `/erk:create-extraction-plan`:

- If on trunk: current session only
- If current session trivial (<1KB): auto-select substantial sessions
- No user prompts (fully automated)

## Output

Creates GitHub issue with `erk-extraction` label containing:

- Raw preprocessed XML from session(s)
- Wrapped in code fences for GitHub rendering
- Truncated if exceeds 65KB limit

## Related

- Analyzed Extraction: `.claude/commands/erk/create-extraction-plan.md`
- GitHub Issue Limits: `docs/agent/github/issue-limits.md`
- Session Preprocessing: `packages/dot-agent-kit/.../preprocess_session.py`
