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
  4. Accepts --flag as a Click option
  5. Uses the pre-computed value; errors with remediation instructions if missing
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

Each script accepts a `--branch-slug` Click option. When provided, it uses the pre-generated slug directly. When missing, the script exits with a clear error message and remediation instructions directing the caller to generate a slug in the skill layer.

See `src/erk/cli/commands/exec/scripts/plan_save.py` for the canonical implementation of this pattern.

### The skill step that generates BRANCH_SLUG

The calling skill (`.claude/commands/erk/plan-save.md`, Step 1.5) instructs Claude to generate a short hyphenated slug from the plan title — 2-4 lowercase words, max 30 characters, using action verbs. The result is stored as `BRANCH_SLUG`.

Then Step 2 passes it:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}" ${OBJECTIVE_FLAG} ${PLAN_TYPE_FLAG}
```

Claude generates the slug using its reasoning about the plan title. The exec script receives it as a plain string — no Claude invocation needed.

## Error Handling

When `--branch-slug` is not provided, exec scripts exit with a clear error message and remediation instructions. They do **not** silently fall back to a sanitized title. This follows the [agent backpressure gates](agent-backpressure-gates.md) philosophy: silent transformation masks mistakes and prevents the agent from learning.

The error message directs callers to generate a slug in the skill layer (e.g., plan-save.md Step 1.5) and pass it via `--branch-slug`. For direct CLI invocation, pass `--branch-slug` explicitly.

## How to Refactor a Nested LLM Call

If you find an LLM call inside an exec script, follow these steps:

1. **Identify the LLM call** — find the `PromptExecutor` invocation and what value it produces
2. **Understand the value** — what information does it compute? (e.g., a descriptive string, a classification, a title)
3. **Add a `--flag` to the exec script** — add it as a Click option; if missing, emit a clear error message with remediation instructions explaining how to generate the value
4. **Add a generation step to the calling skill** — add a step (e.g., "Step 1.5") that instructs Claude to reason about the input and produce the value, storing it as `VARIABLE`
5. **Thread the flag through parameter layers** — update the skill's `erk exec` invocation to pass `--flag="${VARIABLE}"`; see [parameter-threading-pattern.md](parameter-threading-pattern.md) for the full checklist
6. **Remove the LLM call and its imports** from the exec script — the script should now have zero `PromptExecutor` references

## Existing Examples

**Scripts updated in the inference hoisting PR:**

- `src/erk/cli/commands/exec/scripts/plan_save.py`
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`
- `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`

**Skills with generation steps:**

- `.claude/commands/erk/plan-save.md` — Step 1.5 generates `BRANCH_SLUG` before calling `erk exec plan-save`
- `.claude/commands/erk/plan-implement.md` — Generates `BRANCH_SLUG` before calling `erk exec setup-impl` and `erk exec plan-save`
- `.claude/commands/erk/migrate-plan-to-draft-pr.md` — Step 2.5 generates `BRANCH_SLUG` before calling `erk exec plan-migrate-to-draft-pr`

**Pre-existing correct implementation:**

The `objective-create` skill already followed this pattern before the hoisting PR — it generated values through LLM reasoning in skill steps and passed them as flags to exec scripts, providing the precedent this refactor followed.

## Related Documentation

- [Parameter Threading Pattern](parameter-threading-pattern.md) — Step-by-step guide for threading parameters through skill → command → exec layers
- [Prompt Executor Gateway](prompt-executor-gateway.md) — What `PromptExecutor` is and how it works; explains why nested calls deadlock
