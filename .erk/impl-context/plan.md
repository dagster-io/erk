# Plan: Fix lifecycle_stage update coverage in PR Submit Pipeline

> **Replans:** #7997

## Context

When a PR is submitted via `erk pr submit`, the linked plan's `lifecycle_stage` should advance to `"impl"`. The helper function `maybe_advance_lifecycle_to_impl()` already exists and correctly implements this logic. However, it's only called when `state.plan_context is not None` — which means ad-hoc submissions (no AI description, `--skip-description`, or description generation failures) skip the lifecycle update even when the PR IS linked to a plan.

## What Changed Since Original Plan

The original plan (#7997) proposed adding lifecycle update logic to `finalize_pr`. Since then:
- `maybe_advance_lifecycle_to_impl()` already exists at `src/erk/cli/commands/pr/shared.py:144-176`
- It's already called from `finalize_pr` at `submit_pipeline.py:773-780`
- The function uses the correct `"impl"` stage value (not `"implementing"` as the original plan stated)

The real gap is narrower than originally planned: the **call condition** is too restrictive, not the logic itself.

## Investigation Findings

### Corrections to Original Plan
1. **Stage value**: Uses `"impl"` not `"implementing"` — all schema, tests, and code use `"impl"`
2. **Function already exists**: `maybe_advance_lifecycle_to_impl()` implements all required logic
3. **Already called**: finalize_pr already calls it, just gated too narrowly on `plan_context`

### The Actual Gap
- `finalize_pr` line 774: `if state.plan_context is not None:` — only triggers when AI description was generated
- `state.issue_number` (set by `prepare()` from `.impl/plan-ref.json` or branch name) carries the plan_id regardless of plan_context
- For draft-PR backend: `issue_number` is set to `None` locally (line 706) to prevent self-closing, but `state.issue_number` still holds the original value at the top of `finalize_pr`

## Implementation Steps

### Step 1: Widen the lifecycle update condition in `finalize_pr`

**File:** `src/erk/cli/commands/pr/submit_pipeline.py` (lines 773-780)

**Current code:**
```python
# Update lifecycle stage for linked plan
if state.plan_context is not None:
    maybe_advance_lifecycle_to_impl(
        ctx,
        repo_root=state.repo_root,
        plan_id=state.plan_context.plan_id,
        quiet=state.quiet,
    )
```

**New code:**
```python
# Update lifecycle stage for linked plan
plan_id_for_lifecycle: str | None = None
if state.plan_context is not None:
    plan_id_for_lifecycle = state.plan_context.plan_id
elif state.issue_number is not None:
    plan_id_for_lifecycle = str(state.issue_number)
elif ctx.plan_backend.get_provider_name() == "github-draft-pr" and state.pr_number is not None:
    plan_id_for_lifecycle = str(state.pr_number)

if plan_id_for_lifecycle is not None:
    maybe_advance_lifecycle_to_impl(
        ctx,
        repo_root=state.repo_root,
        plan_id=plan_id_for_lifecycle,
        quiet=state.quiet,
    )
```

**Rationale:**
- Prefer `plan_context.plan_id` when available (existing behavior)
- Fall back to `state.issue_number` (from prepare's plan linkage discovery)
- Final fallback: draft-PR backend where the plan IS the PR

### Step 2: Add test for issue_number fallback path

**File:** `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`

Add a test that verifies lifecycle update occurs when `plan_context is None` but `issue_number` is set:

```python
def test_updates_lifecycle_stage_without_plan_context(tmp_path: Path) -> None:
    """finalize_pr updates lifecycle even when plan_context is None but issue_number is set."""
    # Create plan issue with "planned" lifecycle
    # Set state with issue_number=321 but plan_context=None
    # Call finalize_pr
    # Assert lifecycle_stage updated to "impl" in the plan issue
```

Follow the existing test pattern at line 490-532 — use `FakeGitHubIssues`, `format_plan_header_body_for_test`, and assert on `fake_issues.updated_bodies`.

### Step 3: Add test for draft-PR backend fallback

**File:** `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`

Add a test for the draft-PR backend path where neither plan_context nor issue_number is set but pr_number is available:

```python
def test_updates_lifecycle_stage_for_draft_pr_backend(tmp_path: Path) -> None:
    """finalize_pr updates lifecycle for draft-PR backend where plan IS the PR."""
    # Set up plan backend as "github-draft-pr"
    # Set state with plan_context=None, issue_number=None, pr_number=42
    # Call finalize_pr
    # Assert lifecycle_stage updated to "impl"
```

## Verification

1. Run existing test: `pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py::test_updates_lifecycle_stage_for_linked_plan` — should still pass (unchanged path)
2. Run new tests for the two fallback paths
3. Run full test file: `pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`
4. Run type checker on modified files
