# Delete `erk-planning` skill

## Context

The `erk-planning` skill documents plan PR structure and workflows, but its content is significantly out of date — it describes the legacy issue-based plan format, not the current planned-PR backend. Rather than update it, we're removing it since the slash commands (`/erk:plan-save`, `/local:plan-update`, `/erk:replan`) and AGENTS.md already carry sufficient context.

## Changes

### 1. Delete skill files
- Delete `.claude/skills/erk-planning/SKILL.md`
- Delete `.claude/skills/erk-planning/references/workflow.md`
- Delete `.claude/skills/erk-planning/` directory

### 2. Remove from bundled skill registry
- **File:** `src/erk/capabilities/skills/bundled.py:53`
- Remove `"erk-planning": "Plan management",` from `bundled_skills()` dict

### 3. Remove from Codex portable list
- **File:** `src/erk/core/capabilities/codex_portable.py:22`
- Remove `"erk-planning",` from `codex_portable_skills()` frozenset

### 4. Remove from pyproject.toml
- **File:** `pyproject.toml:73`
- Remove `".claude/skills/erk-planning" = "erk/data/claude/skills/erk-planning"` symlink entry

### 5. Remove references from AGENTS.md
- **Line 88:** Remove "Load the `erk-planning` skill for detailed guidance." — keep the command list that follows
- **Line 110:** Remove "Load the `erk-planning` skill (`$erk-planning`) for detailed workflow guidance."

### 6. Remove reference from `/local:plan-update`
- **File:** `.claude/commands/local/plan-update.md:62`
- Remove `- \`erk-planning\` skill - Complete plan management documentation` from Related section

### Not touching (different meaning of "erk-planning")
- `.devcontainer/devcontainer.json:2` — `"name": "erk-planning"` is the devcontainer name, not a skill reference
- `docs/user/planner-setup.md:56` — same, example devcontainer name

## Verification

1. Run `ruff check` (via devrun) to confirm no import errors
2. Run `ty check` (via devrun) for type checking
3. Grep for any remaining `erk-planning` references to confirm clean removal
4. Run capability-related tests if any exist
