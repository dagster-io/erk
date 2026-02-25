# Fix: Stale `erk plan check` reference in one-shot workflow

## Context

The one-shot workflow (`one-shot.yml`) fails at the "Validate plan format" step because it calls `erk plan check`, which was renamed to `erk pr check` in PR #8110 ("Unify PR and plan CLI commands under `erk pr` group"). The workflow was not updated during that rename.

This is the sole cause of the one-shot failure (run 22391925318).

## Change

**File:** `.github/workflows/one-shot.yml` (line 190)

```diff
-          erk plan check ${{ steps.read_result.outputs.plan_id }}
+          erk pr check ${{ steps.read_result.outputs.plan_id }}
```

No other stale `erk plan check/submit/co` references exist in `.github/`.

## Verification

- Re-run the failed one-shot workflow (run 22391925318) or dispatch a new one-shot to confirm the "Validate plan format" step passes.
