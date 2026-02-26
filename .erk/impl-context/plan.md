# Plan: Rename issue_number to plan_number in pr/* CLI files

Part of Objective #7724, Node 6.1

## Context

This is Phase 6 of the `issue_number` → `plan_number` terminology migration across erk. Phases 1-5 renamed exec scripts and their tests. Phase 6 targets the `pr/` CLI command files. Only 3 of the 6 listed files have `issue_number` references; the other 3 are already clean.

## Scope

### Files requiring changes

1. **`src/erk/cli/commands/pr/dispatch_cmd.py`** — Most changes
2. **`src/erk/cli/commands/pr/metadata_helpers.py`** — Moderate changes
3. **`src/erk/cli/commands/pr/create_cmd.py`** — Minimal changes (output strings only)

### Files with NO `issue_number` references (no changes needed)

- `src/erk/cli/commands/pr/submit_pipeline.py` — already uses `plan_id`/`pr_number`
- `src/erk/cli/commands/pr/shared.py` — already uses `plan_id`/`pr_number`
- `src/erk/cli/commands/pr/rewrite_cmd.py` — already uses `pr_number`

## Cross-boundary rules

- **`metadata_helpers.py` IS in scope** → rename its `issue_number` parameter to `plan_number`
- **`create_submission_queued_block()` is in erk_shared (Phase 9)** → keep keyword `issue_number=` at call site
- **`CreatePlanIssueResult.issue_number/.issue_url` is in erk_shared (Phase 9)** → keep field access as-is in create_cmd.py

## Implementation

### Step 1: `dispatch_cmd.py`

**Dataclass rename:**
- `DispatchResult.issue_number` → `plan_number`
- `DispatchResult.issue_title` → `plan_title`
- `DispatchResult.issue_url` → `plan_url`

**Click argument rename:**
- `@click.argument("issue_numbers", ...)` → `@click.argument("plan_numbers", ...)`
- Function signature: `pr_dispatch(ctx, issue_numbers, ...)` → `pr_dispatch(ctx, plan_numbers, ...)`

**Local variable renames** (throughout function body):
- `issue_numbers` → `plan_numbers` (tuple parameter and all references)
- `issue_number` → `plan_number` (local variable in the validation loop, lines 541-578)

**Call site updates:**
- `write_dispatch_metadata(..., issue_number=plan_number, ...)` → `plan_number=plan_number` (metadata_helpers is in-scope)
- `create_submission_queued_block(issue_number=plan_number, ...)` → **KEEP AS-IS** (erk_shared Phase 9)

**User-facing output strings:**
- `r.issue_number` → `r.plan_number`
- `r.issue_url` → `r.plan_url`
- `r.issue_title` → `r.plan_title`
- `"issue"` → `"plan"` in user-facing messages (e.g. "No issue numbers provided" → "No plan numbers provided")

**Docstring updates:**
- `ISSUE_NUMBERS` → `PLAN_NUMBERS` in Click help text
- "issue numbers" → "plan numbers" in docstrings and comments

### Step 2: `metadata_helpers.py`

**Function parameter rename:**
- `write_dispatch_metadata(issue_number: int, ...)` → `plan_number: int`
- Internal: `plan_id = str(issue_number)` → `plan_id = str(plan_number)`
- Error msg: `f"Plan #{issue_number} not found"` → `f"Plan #{plan_number} not found"`

**Docstring/comment updates:**
- `P{issue_number}` → appropriate update in docstring (line 71)
- "Branch doesn't match P{issue_number} pattern" → update

### Step 3: `create_cmd.py`

**Output strings only** (field accesses stay as-is per cross-boundary rule):
- `f"Issue #{result.issue_number} created but incomplete."` → `f"Plan #{result.issue_number} created but incomplete."`
- `f"Created plan #{result.issue_number}"` — already says "plan", no change
- `f"  View:       erk get {result.issue_number}"` — no change (it's a number)
- Keep all `result.issue_number` and `result.issue_url` field accesses unchanged (Phase 9)

### Step 4: Verify

- Run `ruff check` on modified files
- Run `ty check` on modified files
- Run unit tests for dispatch, metadata_helpers, and create commands
- Grep for any remaining `issue_number` in the 6 pr/ files to confirm completeness

## Test impact

Tests for these files (`tests/commands/pr/test_dispatch.py`, `tests/commands/pr/test_create.py`, `tests/unit/cli/commands/pr/test_metadata_helpers.py`) already have zero `issue_number` references — no test changes needed in this node. Node 6.2 covers any test updates that may arise.
