# Plan: Add Model Downgrades to Slash Commands

## Context

Many slash commands perform purely mechanical work (running a single CLI command, formatting output) but inherit the session model (usually opus). By adding `model: haiku` or `model: sonnet` with `context: fork` to their frontmatter, these commands run on cheaper/faster models without affecting quality.

The codebase already uses this pattern successfully (`pr-feedback-classifier`, `devrun`, `audit-scan`). This plan extends it to more commands.

## Changes

### Group 1: Add `model: haiku` + `context: fork` to Frontmatter (5 files)

Each file gets `context: fork`, `agent: general-purpose`, and `model: haiku` added to its YAML frontmatter.

| Command | File |
|---------|------|
| `/local:sessions-list` | `.claude/commands/local/sessions-list.md` |
| `/local:statusline-refresh` | `.claude/commands/local/statusline-refresh.md` |
| `/local:quick-submit` | `.claude/commands/local/quick-submit.md` |
| `/erk:objective-list` | `.claude/commands/erk/objective-list.md` |
| `/local:code-stats` | `.claude/commands/local/code-stats.md` |

**Pattern** (for files that already have frontmatter):
```yaml
---
description: <existing>
context: fork
agent: general-purpose
model: haiku
---
```

### Group 2: Downgrade Task `model` Parameters (3 files)

| Command | File | Change |
|---------|------|--------|
| `/erk:objective-plan` | `.claude/commands/erk/objective-plan.md` | Line 97: `model: "sonnet"` → `model: "haiku"` |
| `/erk:system:objective-plan-node` | `.claude/commands/erk/system/objective-plan-node.md` | Line 38: `model: "sonnet"` → `model: "haiku"` |
| `/local:objective-view` | `.claude/commands/local/objective-view.md` | Lines 90-138: Wrap Step 6 roadmap analysis in explicit `Task(model: "haiku")` call instead of prose-only "Prompt to haiku" |

### Excluded

- `/local:tasks-clear` — Uses `TaskList`/`TaskUpdate` which are session-scoped; `context: fork` would break it
- `/erk:pr-dispatch`, `/erk:pr-address-remote` — Need conversation context to find issue/PR numbers
- `/local:plan-update` — Needs session plan context

## Verification

1. Run each modified command to confirm it still works
2. For `context: fork` commands, verify the forked subagent spinner appears
3. For Task parameter changes, verify data fetch steps produce correct output with haiku
4. For Task parameter changes, verify data fetch steps produce correct output with haiku
