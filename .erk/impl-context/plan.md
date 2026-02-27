# Plan: Resilient plan-header recovery in `erk pr submit` and `plan-implement`

## Context

When `/erk:plan-implement` runs, Claude sometimes goes rogue and executes `gh pr edit --body ...` directly, which overwrites the PR body and destroys the `plan-header` metadata block. This causes `erk pr submit` to fail with:

```
Warning: failed to update lifecycle stage: plan-header block not found in PR body
```

The plan-header block is the sole source of plan lifecycle metadata (lifecycle_stage, dispatch info, learn status, etc.). Once destroyed, it's unrecoverable because the plan IS the PR — there's no separate storage.

Two fixes:
1. **`erk pr submit` resilience**: Reconstruct a minimal plan-header when it's missing
2. **`plan-implement` skill guardrails**: Explicitly prohibit direct `gh` PR commands

## Phase 1: Add `recover_plan_header` helper to `shared.py`

**File**: `src/erk/cli/commands/pr/shared.py`

Add a new function that attempts to recover the plan-header metadata block:

```python
def recover_plan_header(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_id: str,
) -> MetadataBlock | None:
```

Logic:
1. Call `ctx.plan_backend.get_plan(repo_root, plan_id)` to fetch the Plan
2. If `PlanNotFound`, return None
3. If `plan.header_fields` is non-empty (plan-header still exists in PR body), return `MetadataBlock(key="plan-header", data=plan.header_fields)`
4. Otherwise, create a minimal plan-header from PR metadata:
   - `schema_version`: `"2"`
   - `created_at`: `plan.created_at` (ISO 8601 formatted)
   - `created_by`: `plan.metadata.get("author", "unknown")`

New imports needed:
- `from erk_shared.gateway.github.metadata.types import MetadataBlock`
- `from erk_shared.gateway.github.metadata.schemas import SCHEMA_VERSION, CREATED_AT, CREATED_BY`
- `from datetime import UTC`

## Phase 2: Wire recovery into `assemble_pr_body`

**File**: `src/erk/cli/commands/pr/shared.py`

Add optional `recovered_plan_header: MetadataBlock | None = None` parameter to `assemble_pr_body`. When `find_metadata_block(existing_pr_body, "plan-header")` returns None, fall back to `recovered_plan_header`.

This is backwards-compatible — existing callers pass nothing and get current behavior.

## Phase 3: Call recovery in `finalize_pr`

**File**: `src/erk/cli/commands/pr/submit_pipeline.py`

In `finalize_pr` (around line 700), before calling `assemble_pr_body`:

1. Check if `existing_pr_body` has a plan-header: `find_metadata_block(existing_pr_body, "plan-header")`
2. If missing AND `state.plan_context is not None`, call `recover_plan_header(ctx, repo_root=state.repo_root, plan_id=state.plan_context.plan_id)`
3. Pass result as `recovered_plan_header` to `assemble_pr_body`

This ensures the recovered plan-header is included in the PR body written to GitHub, so `maybe_advance_lifecycle_to_impl` will find it when it re-fetches.

New imports in `submit_pipeline.py`:
- Add `recover_plan_header` to the existing `from erk.cli.commands.pr.shared import (...)` block
- Add `find_metadata_block` to the existing `from erk_shared.gateway.github.metadata.core import (...)` block

## Phase 4: Add guardrails to `plan-implement` skill

**File**: `.claude/commands/erk/plan-implement.md`

Add a prominent warning section after the prerequisites, before Step 1:

```markdown
## CRITICAL: PR Operations

**NEVER** run direct GitHub CLI commands for PR operations during implementation:
- ❌ `gh pr edit` — destroys plan-header metadata block
- ❌ `gh pr ready` — bypasses lifecycle tracking
- ❌ `gh pr close` / `gh pr merge`

All PR operations are handled by `erk pr submit` in Step 12. It automatically:
- Generates the PR title and body
- Preserves the plan-header metadata block
- Marks draft PRs as ready for review
- Updates lifecycle stage
```

## Phase 5: Tests

**File**: `tests/unit/cli/commands/pr/test_shared.py` (or create if needed)

Test `recover_plan_header`:
1. Plan not found → returns None
2. Plan has header_fields → returns MetadataBlock with those fields
3. Plan has empty header_fields → returns minimal MetadataBlock with schema_version/created_at/created_by

Test `assemble_pr_body` with `recovered_plan_header`:
1. `existing_pr_body` has plan-header → recovery ignored, original used
2. `existing_pr_body` missing plan-header, recovery provided → recovery used in output
3. Both missing → no plan-header in output (current behavior)

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/pr/shared.py` | Add `recover_plan_header()`, update `assemble_pr_body` signature |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Wire recovery into `finalize_pr` |
| `.claude/commands/erk/plan-implement.md` | Add PR operations guardrail section |
| `tests/unit/cli/commands/pr/test_shared.py` | Tests for recovery logic |

## Verification

1. Run existing tests: `make fast-ci`
2. New unit tests cover recovery paths
3. Manual verification: run `erk pr submit` on a branch where the plan-header was destroyed — should reconstruct and succeed without the warning
