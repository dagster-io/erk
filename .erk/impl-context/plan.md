# Move CI-only command to system folder + add documentation

## Context

`/erk:consolidate-learn-plans-plan` is a CI-only inner skill (used exclusively by the `consolidate-learn-plans` GitHub workflow). It currently lives at `.claude/commands/erk/consolidate-learn-plans-plan.md` alongside user-facing commands, but should be in `.claude/commands/erk/system/` following the same convention as `objective-update-with-landed-pr.md` and `objective-plan-node.md`.

Additionally, there's no documentation about when commands should go in `system/`. This guidance needs to be added.

## Changes

### 1. Move the command file

- **From:** `.claude/commands/erk/consolidate-learn-plans-plan.md`
- **To:** `.claude/commands/erk/system/consolidate-learn-plans-plan.md`

The invocation changes from `/erk:consolidate-learn-plans-plan` to `/erk:system:consolidate-learn-plans-plan`.

### 2. Update all references to the old invocation path

Three files reference `/erk:consolidate-learn-plans-plan`:

| File | Line | Change |
|------|------|--------|
| `.github/workflows/consolidate-learn-plans.yml` | L85 (printf prompt) | Update to `/erk:system:consolidate-learn-plans-plan` |
| `.github/workflows/consolidate-learn-plans.yml` | L104 (claude invocation) | Update to `/erk:system:consolidate-learn-plans-plan` |
| `src/erk/cli/commands/consolidate_learn_plans_dispatch.py` | L125 (prompt content) | Update to `/erk:system:consolidate-learn-plans-plan` |

### 3. Update the command's self-reference

Inside `consolidate-learn-plans-plan.md` itself, update the heading to reflect the new path: `# /erk:system:consolidate-learn-plans-plan` (if it has a self-reference heading like the other system commands do — it currently doesn't have one, so no change needed here).

### 4. Add documentation about the system folder convention

Add a new doc: `docs/learned/commands/system-folder-convention.md`

Content covers:
- **What `system/` is for:** CI-only commands and inner skills that are invoked programmatically (by workflows, other commands, or CLI code), not directly by users
- **When to use it:** Command is invoked by CI workflows, command is an inner skill called by another command, command description says "CI-only" or "inner skill"
- **Naming:** Commands in `system/` get the `/erk:system:` prefix automatically
- **Examples:** Reference the three existing system commands

Frontmatter:
- `read_when`: "placing a new command in .claude/commands/", "creating a CI-only or inner skill command"
- `tripwires`: action "creating a CI-only or workflow-only command outside .claude/commands/erk/system/" → warning "CI-only and inner skill commands belong in the system/ subfolder"

### 5. Run `erk docs sync` to regenerate index files

After creating the new doc, run `erk docs sync` to update `docs/learned/commands/index.md` and `docs/learned/commands/tripwires.md`.

## Verification

1. Grep for old path `/erk:consolidate-learn-plans-plan` (without `system:`) — should return zero results (excluding CHANGELOG)
2. Verify the new file exists at `.claude/commands/erk/system/consolidate-learn-plans-plan.md`
3. Verify the three system commands are all in the `system/` directory
4. Run `erk docs sync` successfully
5. Check that `docs/learned/commands/tripwires.md` includes the new tripwire
