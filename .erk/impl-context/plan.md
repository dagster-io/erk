# Parallelize extract_diff and fetch_plan_context in PR Submit Pipeline

## Context

`erk pr submit` runs an 11-step sequential pipeline. Steps 6 (`extract_diff`) and 7 (`fetch_plan_context`) are completely independent — they read disjoint parts of `SubmitState` and write disjoint fields. Running them sequentially wastes 500-2500ms of wall time. This plan parallelizes them using `ThreadPoolExecutor`.

## Key Files

- `src/erk/cli/commands/pr/submit_pipeline.py` — pipeline definition, `SubmitState`, step functions
- `tests/unit/cli/commands/pr/submit_pipeline/` — unit tests for pipeline steps

## Data Flow Analysis

| Step | Reads | Writes |
|------|-------|--------|
| `extract_diff` (Step 6) | `skip_description`, `base_branch`, `cwd`, `debug`, `session_id`, `repo_root` | `diff_file` |
| `fetch_plan_context` (Step 7) | `skip_description`, `repo_root`, `branch_name` | `plan_context` |

No overlap. Both guard on `skip_description` and return early. `generate_description` (Step 8) is the first to consume both outputs.

## Implementation Plan

### 1. Create a combined `extract_diff_and_fetch_plan_context` step

Add a new function in `submit_pipeline.py` that runs both steps in parallel using `ThreadPoolExecutor(max_workers=2)`:

```python
def extract_diff_and_fetch_plan_context(
    ctx: ErkContext, state: SubmitState
) -> SubmitState | SubmitError:
    """Run extract_diff and fetch_plan_context concurrently."""
    if state.skip_description:
        return state

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        diff_future = executor.submit(extract_diff, ctx, state)
        plan_future = executor.submit(fetch_plan_context, ctx, state)
        diff_result = diff_future.result()
        plan_result = plan_future.result()

    if isinstance(diff_result, SubmitError):
        return diff_result
    if isinstance(plan_result, SubmitError):
        return plan_result

    return dataclasses.replace(
        state,
        diff_file=diff_result.diff_file,
        plan_context=plan_result.plan_context,
    )
```

The `skip_description` early return at the top avoids spinning up threads for the fast path.

**Output interleaving**: `extract_diff` and `fetch_plan_context` both call `click.echo`. Since both threads write to stdout concurrently, lines could interleave. The simplest fix: add `import threading` and a module-level `_echo_lock = threading.Lock()`, then wrap `click.echo` calls in both functions with the lock. Alternatively, suppress the per-step echo calls and have the combined step print a single "Phase 2+3: Getting diff and plan context" line before launching threads.

Preferred approach: single combined echo before the thread launch ("Phase 2: Getting diff and plan context"), remove the individual `click.echo(click.style("Phase 2:...", bold=True))` and `click.echo(click.style("Phase 3:...", bold=True))` lines from the individual functions, keep the debug echo lines (rare path, acceptable interleave in debug mode).

### 2. Update `_submit_pipeline()` to use the combined step

```python
def _submit_pipeline() -> tuple[SubmitStep, ...]:
    return (
        prepare_state,
        cleanup_impl_for_submit,
        commit_wip,
        capture_existing_pr_body,
        push_and_create_pr,
        extract_diff_and_fetch_plan_context,  # replaces extract_diff + fetch_plan_context
        generate_description,
        enhance_with_graphite,
        finalize_pr,
        link_pr_to_objective_nodes,
    )
```

### 3. Keep individual functions intact

`extract_diff` and `fetch_plan_context` remain as standalone functions for direct testability. The combined step delegates to them. No existing tests need to change for the individual step tests.

### 4. Add import

Add `import concurrent.futures` at the top of `submit_pipeline.py`.

### 5. Add test for the combined step

In `tests/unit/cli/commands/pr/submit_pipeline/`, add a test that:
- Verifies both `diff_file` and `plan_context` are set on the returned state
- Verifies `skip_description=True` short-circuits (no thread creation)
- Verifies that a `SubmitError` from `extract_diff` is propagated
- Verifies that a `SubmitError` from `fetch_plan_context` is propagated

Follow existing fake-driven test patterns in the same directory.

## Verification

1. Run existing submit pipeline tests: `pytest tests/unit/cli/commands/pr/submit_pipeline/ -x`
2. Run `erk pr submit` on a branch with changes — verify PR is created/updated, description is generated
3. Time before/after with `time erk pr submit` to confirm improvement
