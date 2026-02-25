# Fix Plan-Header Metadata Loss During PR Submit

## Context

Plan-header metadata stored in PR bodies is silently destroyed during `erk pr submit`. The warning "Plan #8128 has incomplete plan-header (missing created_at, created_by, schema_version)" keeps recurring.

### Root cause

The submit pipeline has a timing bug:

1. `PlannedPRBackend.create_plan()` creates draft PR with plan-header metadata block in body
2. User implements, runs `erk pr submit`
3. `_graphite_first_flow()` calls `ctx.graphite.submit_stack()` → **`gt submit` overwrites the entire PR body with the commit message**
4. `finalize_pr()` reads the now-overwritten PR body → `extract_metadata_prefix()` returns `""` → metadata permanently lost
5. With `metadata_prefix=""`, `assemble_pr_body()` falls through to the issue-based format path (line 242) instead of the planned-PR path (line 239), producing "Implementation Plan (Issue #N)" sections instead of "original-plan" sections
6. Each subsequent submit cycle appends another duplicate plan section + footer (explaining the 4 footers / 6 plan sections in PR #8128)

The metadata block is the lynchpin — once it's destroyed, the body assembly takes the wrong code path on every subsequent rewrite.

### Evidence from PR #8128

- 0 `erk:metadata-block` remnants (metadata gone)
- 4 duplicate checkout footers (accumulated across submits)
- 6 "Implementation Plan" sections (wrong format used repeatedly)
- Branch `plnd/simplify-roadmap-tables-02-24-1824` + `erk-plan` label confirm it IS a planned PR

## Fix: Capture metadata prefix BEFORE `gt submit`

**File:** `src/erk/cli/commands/pr/submit_pipeline.py`

### a) Add `metadata_prefix: str` to `SubmitState`

Add field to the frozen dataclass (after line 93):
```python
metadata_prefix: str
```

### b) Create new pipeline step `capture_metadata_prefix`

```python
def capture_metadata_prefix(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    """Extract plan-header metadata prefix from existing PR body before gt submit overwrites it."""
    pr_result = ctx.github.get_pr_for_branch(state.repo_root, state.branch_name)
    if isinstance(pr_result, PRNotFound):
        return state
    prefix = extract_metadata_prefix(pr_result.body)
    return dataclasses.replace(state, metadata_prefix=prefix)
```

Import `extract_metadata_prefix` from `erk_shared.plan_store.planned_pr_lifecycle` (already imported in this file at line 42).

### c) Insert into pipeline tuples BEFORE `push_and_create_pr`

`_submit_pipeline()` (line 830):
```python
return (
    prepare_state,
    commit_wip,
    capture_metadata_prefix,  # NEW
    push_and_create_pr,
    extract_diff,
    fetch_plan_context,
    generate_description,
    enhance_with_graphite,
    finalize_pr,
)
```

`_push_and_create_pipeline()` (line 802):
```python
return (
    prepare_state,
    commit_wip,
    capture_metadata_prefix,  # NEW
    push_and_create_pr,
)
```

### d) Modify `finalize_pr()` to use pre-captured prefix

Replace lines 690-695:
```python
# BEFORE (reads body AFTER gt submit destroyed it):
metadata_prefix = ""
if state.pr_number is not None:
    existing_pr = ctx.github.get_pr(state.repo_root, state.pr_number)
    if not isinstance(existing_pr, PRNotFound):
        metadata_prefix = extract_metadata_prefix(existing_pr.body)

# AFTER (uses prefix captured BEFORE gt submit):
metadata_prefix = state.metadata_prefix
```

### e) Update `make_initial_state()` (line 877)

Add `metadata_prefix=""` to the `SubmitState` constructor.

## Critical Files

| File | Change |
|------|--------|
| `src/erk/cli/commands/pr/submit_pipeline.py` | Add `metadata_prefix` to `SubmitState`, new `capture_metadata_prefix` step, update `finalize_pr`, update pipeline tuples and `make_initial_state` |

## Existing Utilities to Reuse

- `extract_metadata_prefix()` from `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py:174-192` — already imported in submit_pipeline.py at line 42
- `PRNotFound` from `erk_shared.gateway.github.types` — already imported

## Tests

1. **`capture_metadata_prefix` step:** Test with existing PR body containing metadata → prefix captured in state. Test with no PR → state unchanged.
2. **`finalize_pr` metadata survival:** Test that metadata survives through the pipeline when `state.metadata_prefix` is pre-populated (simulating gt submit overwriting the body mid-pipeline).
3. **Regression:** Existing submit pipeline tests should continue to pass.

## Verification

1. Run existing submit pipeline tests
2. Full CI: `make all-ci`
