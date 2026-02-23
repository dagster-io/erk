---
title: Inference Hoisting Pattern
last_audited: "2026-02-23 00:00 PT"
audit_result: clean
read_when:
  - adding LLM calls to an exec script
  - calling PromptExecutor from a CLI command or exec script
  - working with BranchSlugGenerator or generate_slug_or_fallback
  - adding --branch-slug or similar pre-computed value flags to exec commands
  - understanding why exec scripts must be deterministic
  - refactoring nested LLM calls out of exec scripts
tripwires:
  - action: "calling PromptExecutor, generate_slug_or_fallback, or BranchSlugGenerator from an exec script"
    warning: "Exec scripts must be deterministic. LLM calls belong in the skill layer (.claude/commands/*.md). Hoist: generate the value in the skill, pass it via --flag to the exec script. Read inference-hoisting.md."
    pattern: "PromptExecutor|generate_slug_or_fallback|BranchSlugGenerator"
    score: 9
  - action: "adding LLM-dependent logic inside a Click @command function in exec/scripts/"
    warning: "Inference hoisting violation: exec scripts run as subprocesses; they cannot nest LLM calls within a Claude Code session. Move reasoning to the calling skill."
---

# Inference Hoisting Pattern

## Why This Pattern Exists

Exec scripts are Python subprocesses that run to completion without Claude Code context. They cannot invoke the Claude CLI via `PromptExecutor.execute_prompt()` — attempting to do so inside a Claude Code session creates a nested LLM call that deadlocks or fails.

The skill layer (`.claude/commands/*.md`) is the orchestration boundary. Skills run inside Claude Code with full reasoning capability. They can generate values through LLM inference before invoking exec scripts.

**The original bug**: `plan_save.py`, `setup_impl_from_issue.py`, and `plan_migrate_to_draft_pr.py` called `generate_slug_or_fallback(executor, title)`, which invoked `PromptExecutor.execute_prompt()` to ask Claude for a branch slug. When these scripts ran inside a Claude Code session (via `/erk:plan-save`), the nested Claude subprocess locked up. The fix moved slug generation into the skill layer, passing the pre-generated slug via `--branch-slug`.

## The Rule

**All LLM inference happens in the skill layer. Exec scripts receive pre-computed values as CLI flags.**

## The Pattern

```
Skill (.claude/commands/*.md)
  1. LLM generates the value (e.g., branch slug from plan title)
  2. Stores it as VARIABLE
  3. Passes it as: erk exec <script> --flag "${VARIABLE}"

Exec script (src/erk/cli/commands/exec/scripts/*.py)
  4. Accepts --flag as optional Click option
  5. Uses the pre-computed value, or falls back deterministically
```

Three scripts were updated to follow this pattern:

- `plan_save.py` — `--branch-slug` for draft PR branch naming
- `setup_impl_from_issue.py` — `--branch-slug` for implementation branch naming
- `plan_migrate_to_draft_pr.py` — `--branch-slug` for migration branch naming

## Before/After Example

### Before (broken): LLM call inside exec script

```python
# BROKEN: generate_slug_or_fallback calls PromptExecutor.execute_prompt()
# This creates a nested LLM call when run inside Claude Code — deadlocks.
slug = generate_slug_or_fallback(executor, title)
branch_name = generate_draft_pr_branch_name(slug, now)
```

The `generate_slug_or_fallback` function accepted a `PromptExecutor` and invoked it to ask Claude for a short, descriptive slug. This worked when running `erk exec plan-save` from a terminal, but locked up when called from a skill inside Claude Code.

### After (fixed): Pre-computed value via --flag

```python
# FIXED: Use pre-generated slug or deterministic fallback (no LLM call)
# branch_slug is None when invoked directly outside a skill context.
slug = branch_slug if branch_slug else sanitize_worktree_name(title)
branch_name = generate_draft_pr_branch_name(slug, now)
```

The `--branch-slug` Click option:

```python
@click.option(
    "--branch-slug",
    default=None,
    help="Pre-generated branch slug (skips LLM call when provided)",
)
```

### The skill step that generates BRANCH_SLUG

From `.claude/commands/erk/plan-save.md`, Step 1.5:

```
Generate a branch slug from the title:
- 2-4 hyphenated lowercase words, max 30 characters
- Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
- Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"

Store the result as BRANCH_SLUG.
```

Then Step 2 passes it:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}" ${OBJECTIVE_FLAG} ${PLAN_TYPE_FLAG}
```

Claude generates the slug using its reasoning about the plan title. The exec script receives it as a plain string — no Claude invocation needed.

## Deterministic Fallbacks

When `--branch-slug` is not provided (e.g., direct CLI invocation outside a skill context), exec scripts fall back to `sanitize_worktree_name()` from `erk_shared.naming`:

```python
slug = branch_slug if branch_slug else sanitize_worktree_name(title)
```

`sanitize_worktree_name()` is a pure function — no I/O, no LLM, always produces a valid result. It strips special characters and normalizes whitespace into a filesystem-safe slug.

This is intentional: exec scripts remain safe to invoke directly from the terminal without an LLM present. The `--branch-slug` flag is optional by design.

## How to Refactor a Nested LLM Call

If you find an LLM call inside an exec script, follow these steps:

1. **Identify the LLM call** — find the `PromptExecutor` invocation and what value it produces
2. **Understand the value** — what information does it compute? (e.g., a descriptive string, a classification, a title)
3. **Add a `--flag` to the exec script** — make it optional with `default=None` in Click; add a deterministic fallback for the `None` case
4. **Add a generation step to the calling skill** — add a step (e.g., "Step 1.5") that instructs Claude to reason about the input and produce the value, storing it as `VARIABLE`
5. **Thread the flag through parameter layers** — update the skill's `erk exec` invocation to pass `--flag="${VARIABLE}"`; see [parameter-threading-pattern.md](parameter-threading-pattern.md) for the full checklist
6. **Remove the LLM call and its imports** from the exec script — the script should now have zero `PromptExecutor` references

## Existing Examples

**Scripts updated in the inference hoisting PR:**

- `src/erk/cli/commands/exec/scripts/plan_save.py` — line: `slug = branch_slug if branch_slug else sanitize_worktree_name(title)`
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` — line: `slug = branch_slug if branch_slug else sanitize_worktree_name(plan.title)`
- `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py` — line: `slug = branch_slug if branch_slug else sanitize_worktree_name(plan.title)`

**Skills with generation steps:**

- `.claude/commands/erk/plan-save.md` — Step 1.5 generates `BRANCH_SLUG` before calling `erk exec plan-save`

**Pre-existing correct implementation:**

The `objective-create` skill already followed this pattern before the hoisting PR — it generated values through LLM reasoning in skill steps and passed them as flags to exec scripts, providing the precedent this refactor followed.

## Related Documentation

- [Parameter Threading Pattern](parameter-threading-pattern.md) — Step-by-step guide for threading parameters through skill → command → exec layers
- [Prompt Executor Gateway](prompt-executor-gateway.md) — What `PromptExecutor` is and how it works; explains why nested calls deadlock
