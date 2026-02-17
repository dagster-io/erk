# Change pr-feedback-classifier to use haiku

## Context

The `pr-feedback-classifier` skill classifies PR review comments by actionability and complexity. It's a structured data extraction task (reading comments, categorizing them, outputting JSON) that doesn't require the full reasoning power of the default model. Switching it to haiku reduces cost and latency.

The classifier is invoked through two paths:
1. **Direct skill invocation** (`/pr-feedback-classifier`) — used by `pr-preview-address`
2. **Task tool delegation** — used by `pr-address` (Phase 1 classification and Phase 4 verification)

Both paths must be updated to use haiku.

## Changes

### 1. `.claude/skills/pr-feedback-classifier/SKILL.md` — Add model frontmatter

Add `model: haiku` to the YAML frontmatter. This controls the model when the skill is invoked directly (e.g., by `pr-preview-address`).

**Current frontmatter:**
```yaml
---
name: pr-feedback-classifier
description: >
  Fetches and classifies PR review feedback with context isolation.
  Returns structured JSON with thread IDs for deterministic resolution.
  Use when analyzing PR comments before addressing them.
argument-hint: "[--pr <number>] [--include-resolved]"
context: fork
agent: general-purpose
---
```

**New frontmatter:**
```yaml
---
name: pr-feedback-classifier
description: >
  Fetches and classifies PR review feedback with context isolation.
  Returns structured JSON with thread IDs for deterministic resolution.
  Use when analyzing PR comments before addressing them.
argument-hint: "[--pr <number>] [--include-resolved]"
context: fork
agent: general-purpose
model: haiku
---
```

### 2. `.claude/commands/erk/pr-address.md` — Add model to Task calls

There are two Task tool invocations in `pr-address.md` that call the classifier. Both need `model: "haiku"` added.

**Phase 1 (line ~57)** — Change:
```
Task(
  subagent_type: "general-purpose",
  description: "Classify PR feedback",
  prompt: "Load and follow the skill instructions in .claude/skills/pr-feedback-classifier/SKILL.md
           Arguments: [pass through --pr <number> if specified] [--include-resolved if --all was specified]
           Return the complete JSON output as your final message."
)
```

To:
```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Classify PR feedback",
  prompt: "Load and follow the skill instructions in .claude/skills/pr-feedback-classifier/SKILL.md
           Arguments: [pass through --pr <number> if specified] [--include-resolved if --all was specified]
           Return the complete JSON output as your final message."
)
```

**Phase 4 (line ~236)** — Change:
```
Task(
  subagent_type: "general-purpose",
  description: "Verify PR feedback resolved",
  prompt: "Load and follow the skill instructions in .claude/skills/pr-feedback-classifier/SKILL.md
           Arguments: [pass through --pr <number> if originally specified]
           Return the complete JSON output as your final message."
)
```

To:
```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Verify PR feedback resolved",
  prompt: "Load and follow the skill instructions in .claude/skills/pr-feedback-classifier/SKILL.md
           Arguments: [pass through --pr <number> if originally specified]
           Return the complete JSON output as your final message."
)
```

### 3. `.claude/commands/erk/pr-address.md` — Plan Review Phase 2 Task call

The Plan Review Phase 2 (line ~332) references "Same as standard Phase 1" so it implicitly uses the same Task pattern. Confirm it doesn't have its own Task block to update. (It doesn't — it references the Phase 1 pattern by prose, so the updated Phase 1 pattern automatically applies.)

## Files NOT Changing

- `.claude/commands/erk/pr-preview-address.md` — Invokes the skill directly via `/pr-feedback-classifier`. The `model: haiku` frontmatter in `SKILL.md` handles this path.
- `.claude/commands/erk/pr-address-remote.md` — Triggers `erk launch pr-address` (remote workflow), doesn't directly invoke the classifier.
- `src/erk/capabilities/skills/bundled.py` — Just a name/description registry, no model configuration.
- `src/erk/core/capabilities/codex_portable.py` — Portability classification, no model configuration.
- `docs/learned/` — No docs need updating for this change (the model choice is an implementation detail, not a pattern change).

## Verification

1. Open `.claude/skills/pr-feedback-classifier/SKILL.md` and confirm `model: haiku` is in the frontmatter
2. Open `.claude/commands/erk/pr-address.md` and confirm both Task blocks include `model: "haiku"`
3. Run `ruff check` and `prettier --check` on any modified files to ensure formatting is correct
4. Optionally test by running `/erk:pr-preview-address` on a PR with review comments to confirm the classifier still produces valid JSON output