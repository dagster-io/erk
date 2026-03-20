---
title: Skill Deletion Patterns
read_when:
  - "deleting a skill from erk"
  - "understanding tombstone pattern for skills"
  - "working with erk-planning tombstone"
  - "removing a skill from bundled_skills registry"
tripwires:
  - action: "completely removing a skill's SKILL.md without leaving a tombstone"
    warning: "When erk syncs skills to external repos, it only installs — never removes. A stale skill from a previous installation will remain active in external repos unless a tombstone SKILL.md overwrites it. Always leave a tombstone."
---

# Skill Deletion Patterns

When a skill is deleted from erk, it must be replaced with a tombstone to ensure external repos that previously installed the skill receive the deletion on next sync.

## Why Tombstones?

Erk syncs skills to external repos via `erk capability install`. This is an additive operation — it copies skills but never deletes them. If you completely remove a skill's files, external repos that previously installed it will continue using the stale version indefinitely.

A tombstone overwrites the stale installation: on next sync, external repos receive the tombstone SKILL.md which displays the deletion message and points users to the replacement.

## Tombstone Pattern

Replace the skill's `SKILL.md` with a minimal tombstone:

```markdown
---
name: skill-name
description: "[REMOVED] This skill has been deleted. <Replacement instructions>"
---

This skill has been removed. Use the following instead:

- `replacement-command` — brief description
- `AGENTS.md` — where the documentation moved
```

**Example**: `.claude/skills/erk-planning/SKILL.md` (12 lines):

```markdown
---
name: erk-planning
description: "[REMOVED] This skill has been deleted. Plan management is now handled by slash commands and AGENTS.md."
---

This skill has been removed. Use the following instead:

- `/erk:plan-save` — save plan as draft PR
- `/local:plan-update` — update an existing plan
- `/erk:replan` — replan against current codebase
- `AGENTS.md` — ambient planning workflow documentation
```

## Complete Deletion Checklist

When deleting a skill, modify these locations:

1. **`.claude/skills/<name>/SKILL.md`** → Replace with tombstone (keep the file, change content)

2. **`bundled_skills()` dict** in `src/erk/capabilities/skills/bundled.py` → Add tombstone entry:

   ```python
   "skill-name": "[REMOVED] Plan management now in slash commands",
   ```

3. **`codex_portable_skills()`** → Keep the tombstone entry so it distributes to Codex users

4. **`pyproject.toml` force-include** → Remove the force-include entry (tombstone is minimal, no assets to bundle)

5. **`AGENTS.md`** → Remove any `@.claude/skills/skill-name` references or loading instructions

6. **Related commands** → Remove `Skill tool` invocations for the deleted skill from slash commands

## When to Use Tombstone vs. Complete Removal

| Situation                                          | Action                             |
| -------------------------------------------------- | ---------------------------------- |
| Skill was previously distributed to external repos | Tombstone (required)               |
| Skill was only used internally (never synced out)  | Can completely remove              |
| Skill is being replaced by another approach        | Tombstone pointing to replacement  |
| Skill is being renamed                             | Tombstone for old name + new skill |

In practice: **always use tombstone**. It's hard to track which external repos have installed a skill, so the safe default is to always leave a tombstone.

## Two-Phase Pattern

Complex skill deletions often happen in two phases:

1. **Phase 1 (deletion)**: Remove skill functionality, update all internal references, add tombstone SKILL.md
2. **Phase 2 (tombstone dist)**: Ensure tombstone is in `bundled_skills()` so it distributes on next sync

**Example**: `erk-planning` deletion:

- PR #9223 (phase 1): Deleted planning logic, replaced with slash commands
- PR #9228 (phase 2): Added tombstone to ensure external repos get the deletion

## Related Documentation

- [NPX Skill Management](npx-skill-management.md) — How skills are installed and managed
- [AGENTS.md](../../AGENTS.md) — Skill loading patterns
