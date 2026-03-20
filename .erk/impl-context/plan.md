# Plan: Delete `get-pr-for-plan` exec command (Objective #9109, Node 8.1)

## Context

`get-pr-for-plan` is a redundant exec command — since the plan number IS the PR number, it's just a thin wrapper around `github.get_pr()`. The richer `get-plan-info` command already exists but is missing `head_ref_name`/`base_ref_name` fields that some callers need. This plan migrates callers to `get-plan-info` and deletes the redundant command.

## Current State

**`get-pr-for-plan`** (`src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`):
- Returns: `{success, pr: {number, title, state, url, head_ref_name, base_ref_name}}`
- Uses GitHub gateway directly

**`get-plan-info`** (`src/erk/cli/commands/exec/scripts/get_plan_info.py`):
- Returns: `{success, pr_number, title, state, labels, url, objective_id, backend}`
- Missing: `head_ref_name`, `base_ref_name`
- Uses plan backend (backend-agnostic)

**Callers of `get-pr-for-plan`:**
- `.claude/commands/erk/learn.md` (line 140) — uses `head_ref_name`, `base_ref_name`
- `.claude/skills/erk-exec/reference.md` — documentation
- ~8 `docs/learned/` files — documentation references

## Implementation

### Phase 1: Add branch fields to `get-plan-info`

1. **Add `head_ref_name` to conversion metadata** (`packages/erk-shared/src/erk_shared/plan_store/conversion.py:109`)
   - Add `"head_ref_name": pr.head_ref_name` to the metadata dict (alongside existing `base_ref_name`)

2. **Expose branch fields in `get-plan-info` output** (`src/erk/cli/commands/exec/scripts/get_plan_info.py`)
   - Add `head_ref_name` and `base_ref_name` to the result dict, reading from `plan.metadata`

3. **Update `get-plan-info` tests** (`tests/unit/cli/commands/exec/scripts/test_get_plan_info.py`)
   - Add assertions for `head_ref_name` and `base_ref_name` in success responses

### Phase 2: Migrate callers and delete

4. **Update `learn.md`** (`.claude/commands/erk/learn.md:140`)
   - Replace `erk exec get-pr-for-plan <pr-number>` with `erk exec get-plan-info <pr-number>`
   - Update field references (output structure differs: fields are top-level, not nested under `pr`)

5. **Delete `get-pr-for-plan` script** (`src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`)

6. **Delete tests** (`tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py`)

7. **Remove registration** (`src/erk/cli/commands/exec/group.py`)
   - Remove import (line 66) and `add_command` call (line 218)

8. **Update documentation references** — all `docs/learned/` files and `.claude/skills/erk-exec/reference.md` that reference `get-pr-for-plan`:
   - `docs/learned/cli/pr-operations.md`
   - `docs/learned/architecture/subprocess-wrappers.md`
   - `docs/learned/architecture/fail-open-patterns.md`
   - `docs/learned/planning/branch-name-inference.md`
   - `docs/learned/planning/learn-without-pr-context.md`
   - `docs/learned/planning/pr-discovery.md`
   - `docs/learned/planning/planned-pr-learn-pipeline.md`
   - `docs/learned/planning/lifecycle.md`
   - `docs/learned/planning/tripwires.md`
   - `docs/learned/planning/index.md`
   - `.claude/skills/erk-exec/reference.md`

## Verification

1. Run unit tests for `get-plan-info` to verify new fields
2. Run `ty` type checker
3. Run `ruff` linter
4. Grep for any remaining references to `get-pr-for-plan`
5. Run full test suite to catch any breakage
