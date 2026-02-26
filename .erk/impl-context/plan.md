# Plan: Fix Inaccurate Documentation in learn-plan-land-flow.md

## Context

PR #8269 ("Delete get_branch_issue() dead code and simplify to plan-ref.json") has one unresolved review thread from the audit-pr-docs bot (thread `PRRT_kwDOPxC3hc5w8gz5`).

The bot flagged that `docs/learned/cli/learn-plan-land-flow.md` line 42 says:

> "Read `plan-ref.json` from `.impl/` to get plan ID"

But the actual implementation in `src/erk/cli/commands/land_pipeline.py:338` does:

```python
plan_id = ctx.plan_backend.resolve_plan_id_for_branch(state.main_repo_root, state.branch)
```

The concrete `PlannedPRBackend.resolve_plan_id_for_branch()` (in `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py:114`) calls `self._github.get_pr_for_branch(repo_root, branch_name)` — a **GitHub API call** to find a draft PR associated with the branch. It does **not** read `plan-ref.json`.

## Change Required

**File:** `docs/learned/cli/learn-plan-land-flow.md`

**Location:** Line 42 (the "Detection sequence" section, step 1)

**Current:**
```
1. Read `plan-ref.json` from `.impl/` to get plan ID
```

**Replace with:**
```
1. Call `ctx.plan_backend.resolve_plan_id_for_branch()` to get plan ID (queries GitHub API for a draft PR associated with the branch via `PlannedPRBackend`)
```

## Files to Modify

- `docs/learned/cli/learn-plan-land-flow.md` (line 42 only)

## After the Change

1. **Commit**: `git add docs/learned/cli/learn-plan-land-flow.md && git commit -m "Address PR review comments (batch 1/1)\n\n- Fix inaccurate claim: check_learn_status() calls resolve_plan_id_for_branch() via GitHub API, not plan-ref.json"`

2. **Resolve thread** using batch command:
   ```bash
   echo '[{"thread_id": "PRRT_kwDOPxC3hc5w8gz5", "comment": "Fixed - updated step 1 to accurately describe the GitHub API call via resolve_plan_id_for_branch()"}]' | erk exec resolve-review-threads
   ```

3. **Update PR description**:
   ```bash
   erk exec update-pr-description --session-id "384775a4-ce95-45d7-8f66-2f3145fc2c0f"
   ```

4. **Push** with Graphite: `gt submit --no-interactive`

## Verification

- Re-run the classifier to confirm zero unresolved threads remain.
- Verify the fix against `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py:114-130` (PlannedPRBackend implementation).
