# Generalize PR Body Preservation in Submit Pipeline

## Context

The submit pipeline captures a specific extracted blob (`plan_header_block`) before `gt submit` destroys the PR body. This is brittle — the capture step must know what metadata exists, and adding new metadata types would require new fields on `SubmitState`. The fix: capture the full PR body and let consumers extract what they need at point of use.

## Change Summary

Replace `plan_header_block: str` (pre-extracted metadata) with `existing_pr_body: str` (full preserved body) on `SubmitState` and the `assemble_pr_body` parameter. Move extraction logic into `assemble_pr_body` where it's consumed.

## Files to Modify

### 1. `src/erk/cli/commands/pr/submit_pipeline.py`

**SubmitState dataclass (line 94):**
- Rename `plan_header_block: str` → `existing_pr_body: str`

**`capture_plan_header_block` → `capture_existing_pr_body` (lines 185-193):**
- Store `pr_result.body` directly instead of extracting the block
- No more call to `extract_plan_header_block` here
- Remove import of `extract_plan_header_block`

**`finalize_pr` (line 703):**
- Pass `state.existing_pr_body` to `assemble_pr_body` instead of `state.plan_header_block`

**Pipeline tuples (lines 814, 843):**
- Rename step reference from `capture_plan_header_block` → `capture_existing_pr_body`

**`make_initial_state` (line 909):**
- Rename `plan_header_block=""` → `existing_pr_body=""`

### 2. `src/erk/cli/commands/pr/shared.py`

**`assemble_pr_body` (lines 209-261):**
- Rename parameter `plan_header_block: str` → `existing_pr_body: str`
- Move extraction inside: `plan_header_block = extract_plan_header_block(existing_pr_body)` at top of function
- Add import of `extract_plan_header_block` from `erk_shared.plan_store.planned_pr_lifecycle`
- Internal logic stays the same (uses local `plan_header_block` variable)

### 3. Callers of `assemble_pr_body` — simplify by passing full body

These files currently do `extract_plan_header_block(body)` then pass the result. Now they just pass the body directly.

**`src/erk/cli/commands/pr/rewrite_cmd.py` (lines 158-169):**
- Remove `plan_header_block = extract_plan_header_block(pr_info.body)`
- Pass `existing_pr_body=pr_info.body` to `assemble_pr_body`
- Remove import of `extract_plan_header_block`

**`src/erk/cli/commands/exec/scripts/update_pr_description.py` (lines 145-154):**
- Remove `plan_header_block = extract_plan_header_block(existing_body)`
- Pass `existing_pr_body=existing_body` to `assemble_pr_body`
- Remove import of `extract_plan_header_block`

**`src/erk/cli/commands/exec/scripts/set_pr_description.py` (lines 82-91):**
- Remove `plan_header_block = extract_plan_header_block(existing_body)`
- Pass `existing_pr_body=existing_body` to `assemble_pr_body`
- Remove import of `extract_plan_header_block`

### 4. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` (lines 277-284)

This file does its own manual extraction and assembly (doesn't use `assemble_pr_body`). No change needed — it calls `extract_plan_header_block` directly for its own logic.

### 5. Test files

**`tests/unit/cli/commands/pr/submit_pipeline/test_capture_metadata_prefix.py`:**
- Rename file to `test_capture_existing_pr_body.py`
- Update to test `capture_existing_pr_body` — asserts `result.existing_pr_body == pr.body` (full body, not extracted block)

**All `_make_state` helpers across 10 test files in `tests/unit/cli/commands/pr/submit_pipeline/`:**
- Rename `plan_header_block` param/field → `existing_pr_body`

**`tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`:**
- The two tests that pass `plan_header_block=extract_plan_header_block(pr_body)` now pass `existing_pr_body=pr_body` directly (simpler!)

### 6. Unchanged

- `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py` — `extract_plan_header_block` function definition stays as-is
- `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` — uses `extract_plan_header_block` for its own logic, not via `assemble_pr_body`
- `tests/unit/plan_store/test_planned_pr_lifecycle.py` — tests the extraction function directly, unchanged
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` — has its own assembly logic
- `docs/learned/` — auto-generated, not manually edited

## Verification

1. `make lint format ty` — no import sorting or type errors
2. `uv run pytest tests/unit/cli/commands/pr/submit_pipeline/ -v` — all pipeline tests pass
3. `make test-unit-erk test-erk-dev` — full test suite passes
