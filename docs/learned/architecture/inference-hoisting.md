---
title: Inference Hoisting Pattern
last_audited: "2026-02-23 00:00 PT"
audit_result: clean
read_when:
  - adding LLM calls to an exec script
  - calling PromptExecutor from a CLI command or exec script
  - working with BranchSlugGenerator or generate_branch_slug
  - adding --branch-slug or similar pre-computed value flags to exec commands
  - understanding why exec scripts must be deterministic
  - refactoring nested LLM calls out of exec scripts
  - working with plan summary generation or --summary flags
tripwires:
  - action: "calling PromptExecutor, generate_branch_slug, or BranchSlugGenerator from an exec script"
    warning: "Exec scripts must be deterministic. LLM calls belong in the skill layer (.claude/commands/*.md). Hoist: generate the value in the skill, pass it via --flag to the exec script. Read inference-hoisting.md."
    pattern: "PromptExecutor|generate_branch_slug|BranchSlugGenerator"
    score: 9
  - action: "adding LLM-dependent logic inside a Click @command function in exec/scripts/"
    warning: "Inference hoisting violation: exec scripts run as subprocesses; they cannot nest LLM calls within a Claude Code session. Move reasoning to the calling skill."
---

# Inference Hoisting Pattern

## Why This Pattern Exists

Exec scripts are Python subprocesses that run to completion without Claude Code context. They cannot invoke the Claude CLI via `PromptExecutor.execute_prompt()` — attempting to do so inside a Claude Code session creates a nested LLM call that deadlocks or fails.

The skill layer (`.claude/commands/*.md`) is the orchestration boundary. Skills run inside Claude Code with full reasoning capability. They can generate values through LLM inference before invoking exec scripts.

**The original bug**: `plan_save.py` and `setup_impl_from_pr.py` called `generate_branch_slug(executor, title)`, which invoked `PromptExecutor.execute_prompt()` to ask Claude for a branch slug. When these scripts ran inside a Claude Code session (via `/erk:plan-save`), the nested Claude subprocess locked up. The fix moved slug generation into the skill layer, passing the pre-generated slug via `--branch-slug`.

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

Two scripts were updated to follow this pattern:

- `plan_save.py` — `--branch-slug` for draft PR branch naming
- `setup_impl_from_pr.py` — `--branch-slug` for implementation branch naming

## Before/After Example

### Before (broken): LLM call inside exec script

```python
# BROKEN: generate_branch_slug calls PromptExecutor.execute_prompt()
# This creates a nested LLM call when run inside Claude Code — deadlocks.
slug = generate_branch_slug(executor, title)
branch_name = generate_planned_pr_branch_name(slug, now)
```

The `generate_branch_slug` function accepted a `PromptExecutor` and invoked it to ask Claude for a short, descriptive slug. This worked when running `erk exec plan-save` from a terminal, but locked up when called from a skill inside Claude Code.

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
- `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py`

**Skills with generation steps:**

- `.claude/commands/erk/plan-save.md` — Step 1.5 generates `BRANCH_SLUG` before calling `erk exec plan-save`
- `.claude/commands/erk/plan-implement.md` — Generates `BRANCH_SLUG` before calling `erk exec setup-impl` and `erk exec plan-save`

**Pre-existing correct implementation:**

The `objective-create` skill already followed this pattern before the hoisting PR — it generated values through LLM reasoning in skill steps and passed them as flags to exec scripts, providing the precedent this refactor followed.

## Example: Plan Summary Hoisting

The branch slug was the first inference hoisting case. Plan summary generation followed the same pattern when `PlanSummaryGenerator` was removed.

### Old Approach: Nested LLM Call

`PlanSummaryGenerator` was a class that called `PromptExecutor` to generate a one-line plan summary inside `pr_create`. When called from a skill running inside Claude Code, this created a nested LLM invocation that would deadlock.

### New Approach: `--summary` Flag

The `--summary` Click option was added to exec scripts that need a plan summary:

- `plan_save.py` — `--summary` Click option
- `plan_update.py` — `--summary` Click option
- `create-pr-from-session` — summary passed from skill layer

The calling skills generate the summary through LLM reasoning and pass it via the flag:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --summary="${PLAN_SUMMARY}" --branch-slug="${BRANCH_SLUG}"
```

### Deterministic Exception: `land_learn.py`

Not all summary generation requires LLM inference. `land_learn.py` builds its learn plan summary from a template using structured data (PR title, session counts, plan number). Since no reasoning is needed, it constructs the summary string directly — no `--summary` flag required.

This is the correct boundary: hoist when the value requires LLM reasoning; compute directly when a deterministic template suffices.

### Callers Updated

- `plan-save` skill (`.claude/commands/erk/plan-save.md`) — generates summary in skill, passes via `--summary`
- `plan-update` command (`.claude/commands/local/plan-update.md`, Step 1.5) — generates summary before exec call
- `create-pr-from-session` — summary generated in skill layer
- `pr create` — no longer calls `PlanSummaryGenerator` internally

## LlmCaller: Direct SDK Calls in Dispatch Layer

<!-- Source: packages/erk-shared/src/erk_shared/core/llm_caller.py -->
<!-- Source: src/erk/core/fast_llm.py -->

While `PromptExecutor` runs full reasoning through the Claude CLI (and must be hoisted to the skill layer), `LlmCaller` provides lightweight, direct Anthropic SDK calls that **can** run inside exec scripts and CLI commands. This is a separate pattern from inference hoisting.

### LlmCaller ABC

<!-- Source: packages/erk-shared/src/erk_shared/core/llm_caller.py, LlmCaller.call -->

`LlmCaller` at `packages/erk-shared/src/erk_shared/core/llm_caller.py` defines a single abstract method `call()`. See `LlmCaller.call()` in `packages/erk-shared/src/erk_shared/core/llm_caller.py` for the full signature.

Returns a discriminated union of three frozen dataclasses:

- `LlmResponse(text: str)` — successful response
- `NoApiKey(message: str)` — no `ANTHROPIC_API_KEY` environment variable
- `LlmCallFailed(message: str)` — API error during the call

### AnthropicLlmCaller

`AnthropicLlmCaller` at `src/erk/core/fast_llm.py` implements the ABC using the Anthropic Python SDK. It uses `claude-haiku-4-5-20251001` with `max_tokens=50` for fast, cheap inference.

**Performance:** ~200ms with an API key vs ~5s for a `PromptExecutor` subprocess call (25x improvement).

### When to Use Which

| Pattern          | Mechanism             | Use When                                                                      |
| ---------------- | --------------------- | ----------------------------------------------------------------------------- |
| `PromptExecutor` | Claude CLI subprocess | Full reasoning in skill layer; must be hoisted out of exec scripts            |
| `LlmCaller`      | Direct Anthropic SDK  | Lightweight inference (slug generation, classification) in dispatch/CLI layer |

### Context Integration

`AnthropicLlmCaller` is instantiated during context creation in `create_context()` at `src/erk/core/context.py` and stored as `ctx.llm_caller`. The branch slug generator and other dispatch-layer callers access it through the context.

## Related Documentation

- [Parameter Threading Pattern](parameter-threading-pattern.md) — Step-by-step guide for threading parameters through skill → command → exec layers
- [Prompt Executor Gateway](prompt-executor-gateway.md) — What `PromptExecutor` is and how it works; explains why nested calls deadlock
