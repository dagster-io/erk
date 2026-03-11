# Plan: Make objective mutation commands discoverable

## Context

In a previous session, an agent tried `erk objective add-node` (which doesn't exist) instead of `erk exec add-objective-node`. This caused 4 wasted tool calls (1 failure + 2 cascade cancellations + discovery sequence). The objective skill already documents the correct commands, but the critical architectural insight — `erk objective` is read-only, mutations live under `erk exec` — isn't prominent enough to prevent this mistake.

## Changes

### 1. Add CLI architecture callout to objective skill SKILL.md

**File:** `.claude/skills/objective/SKILL.md`

Add a prominent callout section right after the "Key Design Principles" list (after line 48, before "Quick Reference"), something like:

```markdown
## CLI Architecture: Read vs Write

> **`erk objective` = read-only** (check, view, list, plan, close)
> **`erk exec` = mutations** (add-objective-node, update-objective-node, objective-render-roadmap, etc.)
>
> Never try `erk objective add-node` or `erk objective update-node` — these don't exist.
> All roadmap mutations go through `erk exec` commands.
```

### 2. Add tripwire to objectives tripwires

**File:** `docs/learned/objectives/tripwires.md`

Add a new tripwire entry:

```
**trying to mutate an objective via `erk objective` subcommands (add-node, update-node, etc.)** → Read [SKILL.md](../../../.claude/skills/objective/SKILL.md) first. `erk objective` is read-only (check, view, list, plan, close). All roadmap mutations use `erk exec` commands: `erk exec add-objective-node`, `erk exec update-objective-node`. The `--phase` flag auto-assigns sequential node IDs within a phase (no `--id` flag exists).
```

## Verification

- Read the modified SKILL.md and tripwires.md to confirm clarity
- `erk objective check 9109` still passes (no functional changes)
