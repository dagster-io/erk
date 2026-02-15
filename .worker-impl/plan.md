# Plan: Add `--no-interactive` documentation to gt skill and AGENTS.md

## Context

`--interactive` / `--no-interactive` is a **global flag** inherited by every single gt command — it is not per-command. When enabled (the default), gt may open prompts, pagers, and editors that hang indefinitely in non-interactive contexts like Claude Code sessions. The codebase already has documentation in `docs/learned/architecture/git-graphite-quirks.md` and a tripwire in the architecture tripwires, but the **gt skill itself** (the primary reference agents load when working with gt) has zero mention of `--no-interactive`. AGENTS.md also lacks an explicit CRITICAL rule for this.

## Changes

### 1. Add CRITICAL rule to AGENTS.md (line ~22)

Add alongside the other CRITICAL rules in the "Before Writing Any Code" section:

```markdown
**CRITICAL: NEVER invoke `gt` commands without `--no-interactive`.** The `--interactive` flag is a global option on ALL gt commands (enabled by default). Without `--no-interactive`, gt may prompt for input and hang indefinitely. Note: `--force` does NOT disable prompts — you must pass `--no-interactive` separately.
```

**File:** `AGENTS.md` (after line 22, with the other CRITICAL rules)

### 2. Add prominent warning section to gt skill

Add a new section right after the "Overview" paragraph (before "Core Mental Model") with the `--no-interactive` rule:

```markdown
## CRITICAL: Always Use `--no-interactive`

**NEVER invoke any `gt` command without `--no-interactive`.** This is a global flag inherited by every gt command — not a per-command option.

Without `--no-interactive`, gt may open prompts, pagers, or editors that hang indefinitely in agent/CI contexts. The `--force` flag does NOT prevent prompts — you must use `--no-interactive` separately.

```bash
# WRONG - may hang waiting for user input
gt sync
gt submit --force
gt track --parent main

# CORRECT - always pass --no-interactive
gt sync --no-interactive
gt submit --no-interactive
gt track --parent main --no-interactive
gt restack --no-interactive
gt create my-branch -m "message" --no-interactive
```

**What `--interactive` controls (all disabled by `--no-interactive`):**
- Prompts (confirmation dialogs in sync, delete, submit, etc.)
- Pagers (output paging in log)
- Editors (commit message editing in create/modify, PR metadata in submit)
- Interactive selectors (branch selection in checkout, move, track)

**Note:** `gt modify --interactive-rebase` is a separate, unrelated flag that starts a git interactive rebase. It is NOT the same as the global `--interactive`.
```

**File:** `.claude/skills/gt/SKILL.md` (after line 14, before "Core Mental Model")

### 3. Update workflow examples in gt skill

Update the command examples in the "Workflow Patterns" section to include `--no-interactive` where gt commands appear. Key locations:

- Pattern 4 (Syncing After Merges): `gt sync` → `gt sync --no-interactive`
- Essential Commands table: add note that all commands should use `--no-interactive`

**File:** `.claude/skills/gt/SKILL.md`

## Files to modify

1. `AGENTS.md` — Add CRITICAL rule
2. `.claude/skills/gt/SKILL.md` — Add warning section + update examples

## Verification

1. Read both modified files to confirm the documentation is clear and emphatic
2. Grep for any bare `gt sync`, `gt submit`, `gt track` examples in the skill that lack `--no-interactive`